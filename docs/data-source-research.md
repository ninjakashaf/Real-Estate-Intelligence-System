# Hackathon Data Source Research — Week 03 Group Hackathon

Prepared for the domain-decision discussion. Rubric reminder: **Criterion 1 only requires data via Kaggle OR a BeautifulSoup/Selenium scraper (min 500 rows)** — you do not need both, so a good Kaggle dataset alone is a fully valid path if the timeline is tight.

## Track-by-track findings

### Track 1: FinTech & Digital Banking (EasyPaisa / JazzCash / FBR) — not recommended
- Only generic/global Kaggle datasets found: [Credit Risk Dataset](https://www.kaggle.com/datasets/laotse/credit-risk-dataset), [Microfinance Loan Dataset](https://www.kaggle.com/datasets/youngdaniel/loan-dataset), [Financial Risk for Loan Approval](https://www.kaggle.com/datasets/lorenzozoppelletto/financial-risk-for-loan-approval). None are Pakistan-specific.
- No public, scrapable source for actual EasyPaisa/JazzCash/FBR transaction data — that data isn't public, for good reason.
- Model: classification or regression (credit risk / anomalous filings), per the rubric.
- Verdict: usable, but the "Pakistan industry standards" framing would be a stretch — you'd be doing generic global credit scoring with a Pakistan narrative bolted on.

### Track 2: Real Estate Intelligence (Zameen.com / Graana) — strongest option
- Multiple ready, recent Kaggle datasets already scraped from Zameen (and one that merges Zameen + Graana), with exactly the columns the rubric's example features need (Area, Location, Rooms/Bedrooms, Baths, Price, City):
  - [Pakistan Real Estate Property Listings Dataset (Zameen + Graana)](https://www.kaggle.com/datasets/hassaanmustafavi/pakistan-real-estate-property-listings-dataset) — last updated Jan 2025
  - [Lahore House Listings from Zameen.com (2025)](https://www.kaggle.com/datasets/tahirmehmood0/lahore-house-listings-from-zameen-com-2025)
  - [Karachi Property Dataset Zameen.com](https://www.kaggle.com/datasets/muneebahmedabbasi/karachi-property-dataset-zameencom)
  - [ZAMEEN.COM: Real Estate Dataset Pakistan](https://www.kaggle.com/datasets/hassaanmustafavi/real-estate-dataset-pakistan)
  - [Pakistan property (zameen) dataset](https://www.kaggle.com/datasets/muhammadusmanfarooq/pakistan-property-zameen-dataset)
  - [Zameen.com Property Data Pakistan 2023](https://www.kaggle.com/datasets/muhammadzafeer/zameen-com-property-data-pakistan-2023)
- Feature engineering is nearly handed to you: `Price_per_SqFt` and `Area_per_Room` — literally the rubric's own example names — map directly onto the Area/Rooms/Price columns already in these sets.
- Model: clean regression problem (predict Price). Easy to evaluate with MAE/MSE, which the rubric asks for.
- Scraping caveat: I checked `zameen.com/robots.txt` — it disallows crawling on the city-listing pages (`/Karachi*`, `/Lahore*`, etc.), which are exactly the pages you'd need for a fresh scrape. Practical implication: **use one of the existing Kaggle datasets rather than scraping Zameen directly.** If the team wants a scraper for the bonus/learning value, Graana.com listings or a smaller neighborhood-level scrape would be a safer target — worth a quick robots.txt check on Graana before committing.
- Verdict: fastest path to a working, well-scoped project with the least data risk.

### Track 3: E-Commerce & Retail (Daraz.pk) — feasible but higher scraping risk
- No ready-made Pakistan-specific Kaggle dataset found — the team would be building the dataset from scratch via scraping.
- `daraz.pk/robots.txt` blocks `/cart/`, `/checkout/`, `/customer/`, and category catalog paths (`/catalog/`), but individual product/listing pages aren't broadly blocked — scraping is possible, but Daraz product listings are JS-rendered, so this realistically needs Selenium/Playwright rather than plain BeautifulSoup. There's meaningful risk of rate-limiting or layout changes eating into the 7-day window.
- Several third-party scraper services exist (Apify, ScrapingBee), which confirms it's a known-scrapable target, but those are paid APIs, not something to lean on for a student project.
- Model: classification (sentiment) or regression (discount rate) — both fine, but sentiment needs review text, which is the hardest part to scrape reliably.
- Verdict: doable, but the riskiest timeline-wise of the three tracks above; only pick this if someone on the team is confident with Selenium and has scraped Daraz before.

### Track 4: AgriTech & Food Security (Kissan Mandi Price Forecasting) — solid second option
- [Crop Prices Dataset of Pakistan](https://www.kaggle.com/datasets/humairarana/crop-prices-dataset-of-pakistan) — Pakistan-specific, 2007–2022 time series of crop prices (exact row/column count needs a manual check on the page, but it's a multi-year daily/periodic series, so 500+ rows is very likely).
- [Current Daily Prices of Commodities from Mandi](https://www.kaggle.com/datasets/brpuneet898/current-daily-prices-of-commodities-from-mandi) — same idea but India-focused, useful only as a schema reference, not for a "Pakistan industry standards" pitch.
- Live scrape targets if the team wants fresh data: [AMIS Punjab (Agriculture Marketing Information Service)](http://amis.pk/ViewPrices.aspx) publishes daily commodity prices by district — a government service, generally friendlier to scrape than e-commerce sites, though I couldn't verify its robots.txt (the site had a TLS error on fetch — needs a manual check before scraping). [Kissan Cares mandi rates](https://kissancares.com/mandi-rates) and [Ghalla Mandi](https://ghallamandi.pk/shop/) are other current-rate sources worth eyeballing.
- Model: regression (forecast price) — matches the rubric.
- Verdict: good if the team wants a genuinely Pakistan-flavored, scrape-your-own story; slightly more data-wrangling risk than real estate, since a time-series forecast setup takes a bit more work than a straightforward tabular regression.

### Track 5: Public Sector Identity (NADRA / Excise Service Centers) — not recommended
- No public dataset exists for this (understandably — it's government ID data), and there's no legitimate scrape target either.
- Would require simulating/synthesizing data to get anything at all, which is extra work and weaker for the "real-world data" spirit of the assignment.
- Verdict: not recommended given the 7-day window.

### Track 6: HealthTech Supply Chain (Pharmacy Stockout & Triage) — not recommended
- Decent generic options exist: [Healthcare Dataset](https://www.kaggle.com/datasets/prasad22/healthcare-dataset), [Hospital Triage and Patient History Data](https://www.kaggle.com/datasets/maalona/hospital-triage-and-patient-history-data), [Pharma Sales Data](https://www.kaggle.com/datasets/milanzdravkovic/pharma-sales-data).
- None are Pakistan-specific — same "generic data + local narrative" tradeoff as FinTech.
- Model: classification (triage level / stockout risk), per the rubric.
- Verdict: workable as a fallback, but no stronger a pitch than Track 1, and less scrapable.

## Recommendation for the team's "domain + why" round
1. **Real Estate (Track 2)** — pick this if the priority is finishing a clean, well-evaluated project with low data risk. A dataset is ready today, the example features are basically pre-named by the rubric, and it's a well-understood regression problem.
2. **AgriTech (Track 4)** — pick this if the team wants a more distinctly "Pakistan" story and doesn't mind slightly more setup work (and possibly a live scrape from AMIS Punjab for the bonus points).
3. **E-Commerce (Track 3)** — only pick this if someone is already comfortable with Selenium/Playwright scraping against a JS-heavy site under time pressure.
4. Tracks 1, 5, and 6 are viable fallbacks but weaker pitches: no Pakistan-specific data exists for any of them, so "why this domain" is a harder sell.

## Suggested next step
Since I'm building the scraper piece: if the team leans Real Estate, I'll treat the Kaggle dataset as the primary source (it satisfies criterion 1 outright) and spend scraper effort on a small supplementary scrape (e.g., Graana.com or a narrow Zameen neighborhood page) for bonus freshness, rather than betting the whole pipeline on live scraping. If the team leans AgriTech, I'll start by properly verifying AMIS Punjab's robots.txt and page structure (my automated check hit a TLS error) before committing to it as the scrape target.
