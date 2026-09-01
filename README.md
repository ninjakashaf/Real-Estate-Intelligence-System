# Real Estate Intelligence System

Week 03 Group Hackathon (Edversity AI Solutions Engineering Program) — an
end-to-end AI solution for **Track 2: Real Estate Intelligence**. We scrape
property listings from Zameen.com, engineer features, and train a
Scikit-Learn regression model to predict property price.

## Team

- Aamina Zaka
- Aliza
- Kashaf
- Massab
- Zayn

## Project pipeline

1. **Data acquisition** (`scraper/`) — Playwright scraper pulls listings
   from Zameen.com into `data/raw/zameen_raw.csv`.
2. **Cleaning & EDA** (`notebooks/`) — handle missing values, strip
   currency symbols, inspect distributions.
3. **Feature engineering** (`notebooks/`) — at least 3 engineered features
   (e.g. `Price_per_SqFt`, `Area_per_Room`).
4. **Modeling** (`notebooks/`) — 80/20 train-test split, Scikit-Learn
   regression model (e.g. `RandomForestRegressor`).
5. **Evaluation** — MAE/MSE reported in the notebook.

## Repo structure

```
.
├── data/
│   ├── raw/          # scraper output, untouched
│   └── processed/     # cleaned + feature-engineered dataset for modeling
├── docs/
│   └── data-source-research.md   # track/data-source research behind our domain choice
├── notebooks/         # the graded .ipynb lives here
├── reports/            # presentation deck (.pdf) and other exportable assets
├── scraper/
│   ├── zameen_scraper.py
│   └── README.md       # scraper-specific setup & usage
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # only needed for the scraper
```

## Branching (per assignment rubric)

We use feature branches and PRs rather than committing straight to `main`:

- `feature/data-scraping`
- `feature/feature-engineering`
- `feature/model-training`

Open a PR into `main` for review before merging.

## Deliverables checklist

- [ ] Jupyter Notebook (`.ipynb`)
- [ ] Dataset (`.csv`) — `data/raw/zameen_raw.csv` and/or `data/processed/`
- [ ] Presentation Deck (`.pdf`) — in `reports/`
- [ ] GitHub Repo Link (this repo) with clean commit history & PRs
- [ ] 3-minute Video Pitch
