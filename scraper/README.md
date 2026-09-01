# Zameen.com Scraper

Scrapes property listings from Zameen.com into `../data/raw/zameen_raw.csv` with these columns:

`url, type, purpose, area, bedroom, bath, added, price, location, location_city`

## Why Playwright (not Selenium)

Both work, but Playwright is the better fit here: faster startup, built-in
auto-waiting (no manual `sleep`/`WebDriverWait` boilerplate), a single
`pip install` + `playwright install` gets the browser binary (no separate
driver-version matching like `chromedriver`), and it's noticeably more
stable against modern JS-heavy sites like Zameen.

## Setup

```bash
cd scraper
python3 -m venv venv && source venv/bin/activate
pip install -r ../requirements.txt
playwright install chromium
```

## Run

```bash
# Default: Lahore, Karachi, Islamabad, Rawalpindi, Faisalabad, Multan,
# both for-sale and for-rent, 15 pages each (~25 listings/page) -> ~4500
# raw rows, comfortably clears a 3000-row target after de-duplication.
python zameen_scraper.py

# Custom: just Lahore for-sale, 25 pages (~625 listings)
python zameen_scraper.py --cities Lahore --purposes Homes --pages 25

# Watch it work (non-headless) while debugging
python zameen_scraper.py --cities Lahore --pages 1 --no-headless
```

Known cities and their Zameen location IDs are hardcoded in `CITY_IDS` at
the top of `zameen_scraper.py` (Lahore, Karachi, Islamabad, Rawalpindi,
Faisalabad, Multan, Peshawar, Sialkot, Gujranwala, Quetta). Zameen's city
IDs are internal and not derivable from the name — if you want a city
that's not listed, open a Zameen search page for it in a browser and copy
the numeric id out of the URL (`/Homes/{City}-{id}-1.html`), then add it
to the dict.

### Re-running / topping up

The scraper loads the URLs already in the output CSV **before** it starts,
so re-running it — to add more cities, grab fresh listings, or recover
from an interrupted run — only appends genuinely new rows. It will not
re-save listings you already have. Safe to run as many times as you like:

```bash
python zameen_scraper.py --cities Peshawar Sialkot --pages 15
```

## Validating before it goes to the notebook

`data/raw/` is exactly what the scraper wrote — untouched. Before handing
the dataset to the cleaning/EDA notebook, run it through the validation
gate, which checks column shape, row count, duplicate URLs, and missing
rates on the critical fields, and only copies the file into
`data/processed/` if everything passes:

```bash
python validate_and_promote.py
# or with custom thresholds/paths:
python validate_and_promote.py --raw ../data/raw/zameen_raw.csv --min-rows 3000
```

It prints a pass/fail report for each check. If something fails (e.g. row
count too low, or a field is suspiciously empty on many rows — usually a
sign Zameen changed its markup or the scraper hit mostly dead pages),
nothing gets copied — go fix the underlying data first. `--force` copies
anyway if you need to unblock a teammate while you investigate.

This validation step is a data-quality gate, not the cleaning step — the
actual `fillna`/currency-stripping/EDA work for the rubric still happens
in the notebook, starting from the promoted `data/processed/` file.

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

If the scraper suddenly returns 0 rows for every city, the `aria-label`
values probably changed — check a live listings page. If it returns 0
rows for *some specific* cities only, first suspect a wrong id in
`CITY_IDS` (that's what happened the first time around: Karachi and
Islamabad were both scraped using Lahore's id and silently 404'd).

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

- [x] Fix the city-id bug so Karachi/Islamabad/etc. actually get scraped
- [ ] Run it and confirm we clear the target row count across all cities
- [ ] Run `validate_and_promote.py` and confirm it promotes cleanly
- [ ] Spot-check ~10 random rows against the live site for accuracy
- [ ] Hand `data/processed/zameen_validated.csv` off for the cleaning/EDA notebook

## OLX Pakistan scraper

`olx_scraper.py` scrapes the same 10 fields (plus a `source` column, see
below) from OLX Pakistan into `../data/raw/olx_raw.csv`. Same tooling, same
politeness approach, same cross-run de-duplication as the Zameen scraper.

```bash
python olx_scraper.py
# or scoped down, e.g.:
python olx_scraper.py --cities Lahore Karachi --categories property-for-sale_c2 --pages 15
```

OLX's DOM uses the same kind of stable `aria-label` hooks as Zameen
(`Listing`, `Price`, `Title`, `Subtitle`, `Location`, `Beds`, `Bathrooms`,
`Area`, `Creation date`), verified live against
`https://www.olx.com.pk/lahore_g4060673/property-for-sale_c2`. City ids are
OLX-internal (found via OLX's own location search box, not derivable from
the name) and are listed in `CITY_IDS` at the top of the file.

## Combining sources: `source` column + merging

Both scrapers write a `source` column (`Zameen` or `OLX`) so once you have
listings from multiple sites you can tell them apart and merge them into
one dataset:

```bash
# Merge two (or more) raw CSVs into one, de-duped by URL
python merge_sources.py ../data/raw/zameen_raw.csv ../data/raw/olx_raw.csv --out ../data/raw/combined_raw.csv

# If a file predates the `source` column (e.g. an old zameen_raw.csv
# scraped before this was added), tell merge_sources.py what to backfill,
# in the same order as the input files:
python merge_sources.py ../data/raw/zameen_raw.csv ../data/raw/olx_raw.csv --sources Zameen OLX
```

Then validate the combined file the same way as before:

```bash
python validate_and_promote.py --raw ../data/raw/combined_raw.csv
```

`validate_and_promote.py` now also requires `source` on every row and
prints a per-source row-count breakdown as part of its report, so you can
see the sale/rent and Zameen/OLX split at a glance before promoting to
`data/processed/`.
