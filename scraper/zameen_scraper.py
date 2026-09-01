"""
Zameen.com property listings scraper — Playwright edition.

Scrapes listing CARDS from Zameen's search-results pages (not individual
listing detail pages) because each card page load returns ~25 listings at
once, which is what makes hitting a 500+ row target realistic in a 7-day
hackathon window. Detail-page scraping would be ~25x slower for the same
row count.

Output columns (matches the team's agreed schema):
    url, type, purpose, area, bedroom, bath, added, price, location, location_city

Selector strategy
------------------
Zameen's CSS class names are build-hashed (e.g. `_5b98ebdf`) and change
between deploys, so this scraper does NOT rely on them. Instead it uses the
`aria-label` attributes Zameen puts on each card's fields (Price, Location,
Beds, Baths, Area, Title, "Listing creation date", "Listing link") — these
are accessibility hooks that are far more stable over time than hashed
classes. Verified live against https://www.zameen.com/Homes/Lahore-1-1.html
on 2026-09-01.

`type` (Apartment/House/Plot/etc.) and `purpose` (For Sale/For Rent) are not
separately labelled on the card, so they're parsed out of the listing title
text (e.g. "... 3 beds Apartment For Sale In DHA Phase 5") with a fallback
to the URL section (Homes = sale, Rentals = rent).

Politeness / ToS note
----------------------
Zameen's robots.txt disallows crawling on some city-listing path patterns.
This script is built for a small, one-off academic data pull (not a
production crawler): it runs single-threaded, waits between page loads,
identifies itself with a normal browser UA, and is meant to be run once (or
a few times) to build a ~500-1000 row dataset, not on a schedule. If your
institution or Zameen's terms require otherwise, prefer the Kaggle datasets
listed in the team's data-source-research doc instead.
"""

import argparse
import csv
import random
import re
import time
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE_URL = "https://www.zameen.com"

# purpose_path -> label written into the `purpose` column
PURPOSE_PATHS = {
    "Homes": "For Sale",
    "Rentals": "For Rent",
}

# Known property-type keywords, longest/most-specific first so e.g.
# "Farm House" matches before "House".
TYPE_KEYWORDS = [
    "Farm House", "Penthouse", "Upper Portion", "Lower Portion",
    "Room", "Flat", "Apartment", "House", "Villa",
    "Office", "Shop", "Warehouse", "Factory", "Building",
    "Residential Plot", "Commercial Plot", "Agricultural Land", "Plot", "Land",
]

FIELDS = ["url", "type", "purpose", "area", "bedroom", "bath", "added", "price", "location", "location_city"]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def guess_type(title: str) -> str:
    for kw in TYPE_KEYWORDS:
        if kw.lower() in title.lower():
            return kw
    return "Other"


def guess_purpose(title: str, purpose_path: str) -> str:
    t = title.lower()
    if "for rent" in t:
        return "For Rent"
    if "for sale" in t:
        return "For Sale"
    return PURPOSE_PATHS.get(purpose_path, "Unknown")


def extract_listing(card, purpose_path: str, city: str) -> dict | None:
    """Pull the 10 target fields out of one listing card element."""
    try:
        link_el = card.query_selector('[aria-label="Listing link"]')
        title_el = card.query_selector('[aria-label="Title"]')
        price_el = card.query_selector('[aria-label="Price"]')
        loc_el = card.query_selector('[aria-label="Location"]')
        beds_el = card.query_selector('[aria-label="Beds"]')
        baths_el = card.query_selector('[aria-label="Baths"]')
        area_el = card.query_selector('[aria-label="Area"]')
        date_el = card.query_selector('[aria-label="Listing creation date"]')

        if not link_el or not title_el:
            return None

        href = link_el.get_attribute("href") or ""
        url = urljoin(BASE_URL, href)
        title = title_el.inner_text().strip()

        # price row includes a currency span ("PKR") glued to the number;
        # take the parent's text so we get "PKR6.95 Crore" then normalize spacing.
        price = price_el.evaluate("el => el.parentElement.textContent").strip() if price_el else ""
        price = re.sub(r"^(PKR)", r"\1 ", price)

        added_raw = date_el.inner_text().strip() if date_el else ""
        added = re.sub(r"^Added:\s*", "", added_raw)

        return {
            "url": url,
            "type": guess_type(title),
            "purpose": guess_purpose(title, purpose_path),
            "area": area_el.inner_text().strip() if area_el else "",
            "bedroom": beds_el.inner_text().strip() if beds_el else "",
            "bath": baths_el.inner_text().strip() if baths_el else "",
            "added": added,
            "price": price,
            "location": loc_el.inner_text().strip() if loc_el else "",
            "location_city": city,
        }
    except Exception as e:
        print(f"  ! failed to parse a card: {e}")
        return None


def scrape(cities, purpose_paths, max_pages_per_combo, out_path, headless=True, delay_range=(2.0, 4.0)):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    seen_urls = set()
    total_written = 0

    write_header = not out_path.exists() or out_path.stat().st_size == 0
    csv_file = open(out_path, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
    if write_header:
        writer.writeheader()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1366, "height": 900})
        page = context.new_page()

        for purpose_path in purpose_paths:
            for city in cities:
                empty_pages_in_a_row = 0
                for page_num in range(1, max_pages_per_combo + 1):
                    url = f"{BASE_URL}/{purpose_path}/{city}-1-{page_num}.html"
                    print(f"[{purpose_path}/{city}] page {page_num}: {url}")
                    try:
                        page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        page.wait_for_selector('[aria-label="Listing"]', timeout=10000)
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
                        row = extract_listing(card, purpose_path, city)
                        if row and row["url"] not in seen_urls:
                            seen_urls.add(row["url"])
                            writer.writerow(row)
                            page_new += 1
                    csv_file.flush()
                    total_written += page_new
                    print(f"  +{page_new} new rows (total so far: {total_written})")

                    time.sleep(random.uniform(*delay_range))

    csv_file.close()
    print(f"\nDone. {total_written} unique rows written to {out_path}")
    return total_written


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Scrape Zameen.com listing cards into a CSV.")
    ap.add_argument("--cities", nargs="+", default=["Lahore", "Karachi", "Islamabad"],
                     help="City slugs as used in Zameen URLs (e.g. Lahore, Karachi, Islamabad, Rawalpindi, Faisalabad).")
    ap.add_argument("--purposes", nargs="+", default=["Homes", "Rentals"], choices=["Homes", "Rentals"],
                     help="Homes = for-sale listings, Rentals = for-rent listings.")
    ap.add_argument("--pages", type=int, default=10, help="Max pages to fetch per city/purpose combo (~25 listings/page).")
    ap.add_argument("--out", default="../data/raw/zameen_raw.csv", help="Output CSV path.")
    ap.add_argument("--no-headless", action="store_true", help="Run with a visible browser window (useful for debugging).")
    args = ap.parse_args()

    scrape(
        cities=args.cities,
        purpose_paths=args.purposes,
        max_pages_per_combo=args.pages,
        out_path=args.out,
        headless=not args.no_headless,
    )
