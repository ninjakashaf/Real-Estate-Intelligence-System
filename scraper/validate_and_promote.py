"""
Data-quality gate between data/raw and data/processed.

Run this after the scraper. It checks the raw CSV against a handful of
sanity rules, prints a report, and — only if every check passes — writes
the file into data/processed/. This is NOT the cleaning/EDA step (that
still belongs in the notebook: fillna, stripping currency symbols, etc.)
It's a much cheaper gate that catches "the scraper broke" before you waste
notebook time on a bad file: right shape, right columns, not mostly empty,
no duplicate listings, at least N rows.

When a file is promoted, a sequential `id` column (1, 2, 3, ...) is added
as the first column of the processed output — the raw file in data/raw/
is left untouched; only the promoted copy gets numbered.

Usage:
    python validate_and_promote.py
    python validate_and_promote.py --raw ../data/raw/zameen_raw.csv --min-rows 3000
    python validate_and_promote.py --force   # copy even if some checks fail (prints warnings, still fails hard checks)
"""

import argparse
import csv
import sys
from pathlib import Path

REQUIRED_COLUMNS = ["url", "type", "purpose", "area", "bedroom", "bath", "added", "price", "location", "location_city", "source"]

# Columns that should basically never be blank — if too many rows are
# missing these, the scraper likely broke (selector changed, wrong page, etc.)
CRITICAL_COLUMNS = ["url", "price", "area", "location", "location_city", "source"]

MAX_MISSING_RATE = 0.05  # fail if more than 5% of rows are missing a critical field


def load_rows(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def write_numbered(fieldnames, rows, processed_path: Path):
    """Write rows to processed_path with a sequential `id` column (1..N) as
    the first column. This numbering is only applied to the promoted output
    — the raw file in data/raw/ is left untouched."""
    out_fields = ["id"] + [c for c in fieldnames if c != "id"]
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    with open(processed_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for i, row in enumerate(rows, start=1):
            row = dict(row)
            row["id"] = i
            writer.writerow(row)


def validate(path: Path, min_rows: int):
    checks = []  # (name, passed: bool, detail: str)

    if not path.exists():
        print(f"FAIL: {path} does not exist. Run the scraper first.")
        sys.exit(1)

    fieldnames, rows = load_rows(path)

    # 1. Required columns present (and no unexpected extras that suggest a schema drift)
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in (fieldnames or [])]
    checks.append(("required columns present", not missing_cols, f"missing: {missing_cols}" if missing_cols else "ok"))

    # 2. Row count
    checks.append((f"row count >= {min_rows}", len(rows) >= min_rows, f"found {len(rows)} rows"))

    # 3. No duplicate URLs (the scraper de-dupes, but this catches a hand-edit or a merge mistake)
    urls = [r.get("url", "") for r in rows]
    dupes = len(urls) - len(set(urls))
    checks.append(("no duplicate URLs", dupes == 0, f"{dupes} duplicate URL(s) found"))

    # 4. Missing-value rate on critical columns
    for col in CRITICAL_COLUMNS:
        if col not in (fieldnames or []):
            continue
        missing = sum(1 for r in rows if not (r.get(col) or "").strip())
        rate = missing / len(rows) if rows else 1.0
        checks.append((f"'{col}' missing rate <= {MAX_MISSING_RATE:.0%}", rate <= MAX_MISSING_RATE,
                       f"{missing}/{len(rows)} rows missing ({rate:.1%})"))

    # 5. Sanity check on purpose/type values (should be one of the known buckets, not garbage)
    bad_purpose = sum(1 for r in rows if r.get("purpose") not in ("For Sale", "For Rent", "Unknown"))
    checks.append(("'purpose' values look sane", bad_purpose == 0, f"{bad_purpose} row(s) with an unexpected purpose value"))

    source_counts = {}
    for r in rows:
        s = r.get("source") or "(blank)"
        source_counts[s] = source_counts.get(s, 0) + 1

    return checks, rows, source_counts


def main():
    ap = argparse.ArgumentParser(description="Validate the scraped dataset and promote it to data/processed if it passes.")
    ap.add_argument("--raw", default="../data/raw/combined_raw.csv",
                     help="Path to the raw CSV to validate — typically the output of merge_sources.py.")
    ap.add_argument("--processed", default="../data/processed/listings_validated.csv",
                     help="Where to copy the file if it passes validation.")
    ap.add_argument("--min-rows", type=int, default=3000, help="Minimum acceptable row count.")
    ap.add_argument("--force", action="store_true",
                     help="Promote anyway even if a check fails (still shows the report). Use sparingly.")
    args = ap.parse_args()

    raw_path = Path(args.raw)
    processed_path = Path(args.processed)

    checks, rows, source_counts = validate(raw_path, args.min_rows)

    print(f"\nValidation report for {raw_path}")
    print("-" * 60)
    all_passed = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"[{status}] {name} — {detail}")
    print("-" * 60)
    print("Rows by source: " + ", ".join(f"{k}={v}" for k, v in sorted(source_counts.items())))
    print("-" * 60)

    if all_passed or args.force:
        fieldnames, _ = load_rows(raw_path)
        write_numbered(fieldnames, rows, processed_path)
        verb = "Promoted" if all_passed else "Force-promoted (some checks FAILED — see above)"
        print(f"{verb}: {raw_path} -> {processed_path} ({len(rows)} rows, numbered id 1-{len(rows)})")
        sys.exit(0 if all_passed else 2)
    else:
        print(f"NOT promoted to {processed_path} — fix the issues above (or re-run the scraper) and try again.")
        print("(Use --force to copy anyway, e.g. to unblock teammates while you investigate.)")
        sys.exit(1)


if __name__ == "__main__":
    main()
