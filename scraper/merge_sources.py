"""
Merge the per-source raw CSVs (Zameen, OLX, ...) into one combined file.

Both scrapers now write the same 11-column schema:
    url, type, purpose, area, bedroom, bath, added, price, location, location_city, source

This script concatenates any number of raw CSVs, backfills a `source`
column for older files that predate it (e.g. a zameen_raw.csv scraped
before the source column was added — pass its source name explicitly with
--sources), de-duplicates by URL (keeping the first occurrence), and writes
one combined file. Run validate_and_promote.py on the combined output next.

Usage:
    # Simple case: every input file already has a `source` column
    python merge_sources.py ../data/raw/zameen_raw.csv ../data/raw/olx_raw.csv

    # One file predates the `source` column -- tell it what to backfill
    python merge_sources.py ../data/raw/zameen_raw.csv ../data/raw/olx_raw.csv \\
        --sources Zameen OLX

    # Custom output path
    python merge_sources.py ../data/raw/*.csv --out ../data/raw/combined_raw.csv
"""

import argparse
import csv
from pathlib import Path

FIELDS = ["url", "type", "purpose", "area", "bedroom", "bath", "added", "price", "location", "location_city", "source"]


def load_csv(path: Path, fallback_source: str | None):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if not row.get("source"):
            if not fallback_source:
                raise SystemExit(
                    f"{path} has no `source` column and no fallback was given for it. "
                    f"Pass --sources with one name per input file (same order), e.g.:\n"
                    f"  python merge_sources.py {path} ... --sources Zameen ..."
                )
            row["source"] = fallback_source
        # keep only the known columns, in the known order (drops any stray extra columns)
        for col in FIELDS:
            row.setdefault(col, "")
    return rows


def main():
    ap = argparse.ArgumentParser(description="Merge per-source raw listing CSVs into one file.")
    ap.add_argument("inputs", nargs="+", help="Raw CSV files to merge (e.g. zameen_raw.csv olx_raw.csv).")
    ap.add_argument("--sources", nargs="*", default=None,
                     help="Fallback source name per input file, same order, for files that predate the "
                          "`source` column. Only needed for rows missing it; a file that already has "
                          "`source` on every row doesn't need an entry here.")
    ap.add_argument("--out", default="../data/raw/combined_raw.csv", help="Output path for the merged CSV.")
    args = ap.parse_args()

    input_paths = [Path(p) for p in args.inputs]
    fallbacks = args.sources or []
    if fallbacks and len(fallbacks) != len(input_paths):
        raise SystemExit(f"--sources needs one entry per input file: got {len(fallbacks)} names for {len(input_paths)} files.")

    all_rows = []
    seen_urls = set()
    per_file_counts = {}
    dupes_dropped = 0

    for i, path in enumerate(input_paths):
        fallback = fallbacks[i] if fallbacks else None
        rows = load_csv(path, fallback)
        kept = 0
        for row in rows:
            u = row.get("url", "")
            if u and u in seen_urls:
                dupes_dropped += 1
                continue
            if u:
                seen_urls.add(u)
            all_rows.append(row)
            kept += 1
        per_file_counts[str(path)] = (len(rows), kept)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Merged {len(input_paths)} file(s) -> {out_path}")
    for path, (total, kept) in per_file_counts.items():
        print(f"  {path}: {total} rows read, {kept} kept ({total - kept} were cross-file duplicates)")
    print(f"Dropped {dupes_dropped} duplicate URL(s) across files.")
    print(f"Total: {len(all_rows)} unique rows.")

    # quick per-source breakdown
    counts = {}
    for row in all_rows:
        counts[row["source"]] = counts.get(row["source"], 0) + 1
    print("By source:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
