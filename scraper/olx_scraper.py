"""
OLX Pakistan property listings scraper — Playwright edition.

Same idea as zameen_scraper.py: scrape listing CARDS from OLX's category
search-results pages (not individual item pages) so a page load returns
~24 listings at once.

Output columns (same schema as the Zameen scraper, plus `source`):
    url, type, purpose, area, bedroom, bath, added, price, location, location_city, source

Selector strategy
------------------
Like Zameen, OLX's CSS classes are build-hashed (e.g. `f114c800`) and
useless as long-term selectors. OLX also puts `aria-label` accessibility
hooks on each card: `Listing` (the card itself), `Price`, `Title`,
`Subtitle`, `Location`, `Beds`, `Bathrooms`, `Area`, `Creation date`.
Verified live against
https://www.olx.com.pk/lahore_g4060673/property-for-sale_c2 on 2026-09-01.

`type` isn't separately labelled, so — same as the Zameen scraper — it's
parsed out of the listing title with a fallback of "Other".

City IDs
--------
OLX URLs are /{city}_g{geoId}/{category}?page={n} — the geo id is an
internal OLX id per city, found by typing the city name into OLX's own
location search box and reading the suggestion link. Verified for the 6
cities below on 2026-09-01; add more the same way if needed.

Cross-run de-duplication and politeness notes are the same as
zameen_scraper.py — see that file's docstring.
"""

import argparse
import csv
import random
import re
import time
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE_URL = "https://www.olx.com.pk"
SOURCE_NAME = "OLX"

# City name -> OLX's internal geo location id. Verified live on 2026-09-01.
CITY_IDS = {
    "Lahore": 4060673,
    "Karachi": 4060695,
    "Islamabad": 4060615,
    "Rawalpindi": 4060681,
    "Faisalabad": 4060660,
    "Multan": 4060675,
    "Gujranwala": 4060662,
    "Sialkot": 4060686,
}

# category slug -> label written into the `purpose` column
PURPOSE_CATEGORIES = {
    "property-for-sale_c2": "For Sale",
    "property-for-rent_c3": "For Rent",
}

TYPE_KEYWORDS = [
    "Farm House", "Penthouse", "Upper Portion", "Lower Portion",
    "Room", "Flat", "Apartment", "House", "Villa",
    "Office", "Shop", "Warehouse", "Factory", "Building",
    "Residential Plot", "Commercial Plot", "Agricultural Land", "Plot", "Land", "File",
]

FIELDS = ["url", "type", "purpose", "area", "bedroom", "bath", "added", "price", "location", "location_city", "source"]


def guess_type(title: str) -> str:
    for kw in TYPE_KEYWORDS:
        if kw.lower() in title.lower():
            return kw
    return "Other"


def extract_listing(card, purpose_label: str, city: str) -> dict | None:
    """Pull the target fields out of one OLX listing card element."""
    try:
        link_el = card.query_selector('a[href*="-iid-"]')
        title_el = card.query_selector('[aria-label="Title"]')
        price_el = card.query_selector('[aria-label="Price"]')
        loc_el = card.query_selector('[aria-label="Location"]')
        beds_el = card.query_selector('[aria-label="Beds"]')
        baths_el = card.query_selector('[aria-label="Bathrooms"]')
        area_el = card.query_selector('[aria-label="Area"]')
        date_el = card.query_selector('[aria-label="Creation date"]')

        if not link_el or not title_el:
            return None

        href = link_el.get_attribute("href") or ""
        url = urljoin(BASE_URL, href)
        title = title_el.inner_text().strip()

        location_raw = loc_el.inner_text().strip() if loc_el else ""
        location = location_raw.rstrip("•").strip()  # OLX appends a "•" separator to the location text

        return {
            "url": url,
            "type": guess_type(title),
            "purpose": purpose_label,
            "area": area_el.inner_text().strip() if area_el else "",
            "bedroom": (beds_el.inner_text().strip() if beds_el else "").replace(" Beds", "").replace(" Bed", ""),
            "bath": (baths_el.inner_text().strip() if baths_el else "").replace(" Baths", "").replace(" Bath", ""),
            "added": date_el.inner_text().strip() if date_el else "",
            "price": price_el.inner_text().strip() if price_el else "",
            "location": location,
            "location_city": city,
            "source": SOURCE_NAME,
        }
    except Exception as e:
        print(f"  ! failed to parse a card: {e}")
        return None


def load_existing_urls(out_path: Path) -> set:
    if not out_path.exists() or out_path.stat().st_size == 0:
        return set()
    seen = set()
    with open(out_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            u = row.get("url")
            if u:
                seen.add(u)
    return seen


def scrape(cities, categories, max_pages_per_combo, out_path, headless=True, delay_range=(2.0, 4.0)):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    unknown = [c for c in cities if c not in CITY_IDS]
    if unknown:
        raise SystemExit(
            f"Unknown city/cities (no location id on record): {unknown}. "
            f"Known cities: {sorted(CITY_IDS)}. Add missing ones to CITY_IDS in this file."
        )

    seen_urls = load_existing_urls(out_path)
    if seen_urls:
        print(f"Loaded {len(seen_urls)} existing URLs from {out_path} — those will be skipped this run.")
    total_written = 0

    write_header = not out_path.exists() or out_path.stat().st_size == 0
    csv_file = open(out_path, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
    if write_header:
        writer.writeheader()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1366, "height": 900})
        page = context.new_page()

        for category in categories:
            purpose_label = PURPOSE_CATEGORIES[category]
            for city in cities:
                location_id = CITY_IDS[city]
                empty_pages_in_a_row = 0
                for page_num in range(1, max_pages_per_combo + 1):
                    suffix = "" if page_num == 1 else f"?page={page_num}"
                    url = f"{BASE_URL}/{city.lower()}_g{location_id}/{category}{suffix}"
                    print(f"[{category}/{city}] page {page_num}: {url}")
                    try:
                        page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        page.wait_for_selector('[aria-label="Listing"]', timeout=10000)
                        # OLX renders cards progressively; give it a moment to settle.
                        page.wait_for_timeout(800)
                    except PWTimeout:
                        print("  no listings found (timeout) — assuming end of results for this combo")
                        empty_pages_in_a_row += 1
                        if empty_pages_in_a_row >= 2:
                            break
                        continue

                    cards = page.query_selector_all('[aria-label="Listing"]')
                    if not cards:
                        empty_pages_in_a_row += 1
                        if empty_pages_in_a_row >= 2:
                            break
                        continue
                    empty_pages_in_a_row = 0

                    page_new = 0
                    for card in cards:
                        row = extract_listing(card, purpose_label, city)
                        if row and row["url"] not in seen_urls:
                            seen_urls.add(row["url"])
                            writer.writerow(row)
                            page_new += 1
                    csv_file.flush()
                    total_written += page_new
                    print(f"  +{page_new} new rows (session total: {total_written}, file total: {len(seen_urls)})")

                    time.sleep(random.uniform(*delay_range))

    csv_file.close()
    print(f"\nDone. +{total_written} new rows this run. {out_path} now has {len(seen_urls)} unique rows total.")
    return total_written


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Scrape OLX Pakistan property listing cards into a CSV.")
    ap.add_argument("--cities", nargs="+",
                     default=["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad", "Multan"],
                     help=f"City names with a known location id. Known: {sorted(CITY_IDS)}")
    ap.add_argument("--categories", nargs="+", default=list(PURPOSE_CATEGORIES),
                     choices=list(PURPOSE_CATEGORIES),
                     help="property-for-sale_c2 = for-sale listings, property-for-rent_c3 = for-rent listings.")
    ap.add_argument("--pages", type=int, default=15,
                     help="Max pages to fetch per city/category combo (~24 listings/page).")
    ap.add_argument("--out", default="../data/raw/olx_raw.csv", help="Output CSV path.")
    ap.add_argument("--no-headless", action="store_true", help="Run with a visible browser window (useful for debugging).")
    args = ap.parse_args()

    scrape(
        cities=args.cities,
        categories=args.categories,
        max_pages_per_combo=args.pages,
        out_path=args.out,
        headless=not args.no_headless,
    )
