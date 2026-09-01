# Zameen.com Scraper

Scrapes property listings from Zameen.com into `../data/raw/zameen_raw.csv` with these columns:

`url, type, purpose, area, bedroom, bath, added, price, location, location_city`

## Why Playwright (not Selenium)

Both work, but Playwright is the better fit here: faster startup, built-in
auto-waiting (no manual `sleep`/`WebDriverWait` boilerplate), a single
`pip install` + `playwright install` gets the browser binary (no separate
driver-version matching like `chromedriver`), and it's noticeably more
stable against modern JS-heavy sites like Zameen. It's also just as easy to
run headless in GitHub Actions later if we want to automate re-scrapes.

## Setup

```bash
cd scraper
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r ../requirements.txt
playwright install chromium
```

## Run

```bash
# Default: Lahore, Karachi, Islamabad, both for-sale and for-rent, 10 pages each (~25 listings/page)
python zameen_scraper.py

# Custom: just Lahore for-sale, 25 pages (~625 listings)
python zameen_scraper.py --cities Lahore --purposes Homes --pages 25

# Watch it work (non-headless) while debugging
python zameen_scraper.py --cities Lahore --pages 1 --no-headless
```

Output is appended to `../data/raw/zameen_raw.csv` (created if missing),
with duplicate URLs skipped automatically — so it's safe to re-run to top
up the row count.

With the default settings (3 cities x 2 purposes x 10 pages x ~25
listings/page) you should comfortably clear the assignment's 500-row
minimum; increase `--pages` or `--cities` if you want more.

## How it finds the data

Zameen's CSS class names are build-hashed and change on every deploy, so
the scraper does **not** select on classes. It uses the `aria-label`
attributes Zameen puts on each listing card (`Price`, `Location`, `Beds`,
`Baths`, `Area`, `Title`, `Listing link`, `Listing creation date`) — these
are accessibility hooks and are much more stable. Verified live against
`https://www.zameen.com/Homes/Lahore-1-1.html`.

`type` (House/Apartment/Plot/etc.) and `purpose` (For Sale/For Rent) aren't
separately labelled on the card, so they're inferred from the listing
title text, with a fallback based on which URL section it came from
(`Homes` = sale, `Rentals` = rent).

## If Zameen changes its markup

If the scraper suddenly returns 0 rows, the `aria-label` values probably
changed. Open a listings page in a real browser, inspect a card, and check
what `aria-label`s are present now — `extract_listing()` in
`zameen_scraper.py` is the only place that needs updating.

## A note on scraping etiquette

Zameen's `robots.txt` disallows crawling on some city-listing path
patterns, so this is written for a one-off, small academic pull rather
than a production crawler: single-threaded, a random 2-4s delay between
page loads, a normal browser user-agent, and it's meant to be run a
handful of times to build the dataset — not scheduled or run in parallel.
If that's a concern for the assignment, the Kaggle datasets in
`docs/data-source-research.md` are a fully valid alternative data source
per the rubric (Kaggle OR scraper, not both required).

## Next steps for the team

- [ ] Run it and confirm we clear 500+ rows across the target cities
- [ ] Spot-check ~10 random rows against the live site for accuracy
- [ ] Hand `data/raw/zameen_raw.csv` off for the cleaning/EDA notebook
- [ ] (Optional) add a GitHub Action to re-run this weekly for fresher data
