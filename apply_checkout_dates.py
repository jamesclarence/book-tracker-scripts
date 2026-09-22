"""
Takes the TSV produced by scrape_checkout_dates.js (Title, Item type,
Date - tab separated, one row per checkout) and applies checkout dates
into a "Have Read" CSV's "Date Started" column for rows whose Source
mentions "Library".

Matching is two-tier because a merged row (Source == "<primary> &
Library") keeps its ORIGINAL title from the primary source (e.g.
Goodreads), which is often worded differently than the library's
catalog title - "Babylon's Ashes (The Expanse, #6)" vs.
"Babylon's ashes". A library-only row, by contrast, keeps the library's
own title verbatim, so it needs only light normalization.

  1. Light normalization (normalize.norm_title_light) - exact match,
     preserves volume/series numbering. Tried first.
  2. Aggressive normalization (normalize.norm_title) - strips
     subtitles/parentheticals, for matching a primary-source title
     against the library's wording. Tried second.

A still-checked-out item (date == "(Checked out)") gets a note instead
of a date. A title checked out more than once gets its most recent
date, with the earlier date(s) preserved in the Notes column.

Usage:
    python apply_checkout_dates.py checkout_dates.tsv have_read.csv have_read_updated.csv
"""
import csv
import datetime
import sys
from collections import defaultdict

from normalize import norm_title, norm_title_light

STILL_CHECKED_OUT = "(Checked out)"


def load_checkout_dates(tsv_path):
    by_light = defaultdict(list)
    with open(tsv_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            title, item_type, date_str = line.split("\t")
            by_light[norm_title_light(title)].append((date_str, title))

    by_fuzzy = defaultdict(list)
    for entries in by_light.values():
        for date_str, orig_title in entries:
            by_fuzzy[norm_title(orig_title)].append((date_str, orig_title))

    return by_light, by_fuzzy


def most_recent(date_strs):
    parsed = [datetime.datetime.strptime(d, "%m/%d/%Y").date() for d in date_strs]
    return max(parsed).strftime("%m/%d/%Y")


def apply_dates(have_read_rows, by_light, by_fuzzy):
    updated, skipped = 0, []

    for r in have_read_rows:
        if "Library" not in r.get("Source", ""):
            continue

        candidates = by_light.get(norm_title_light(r["Title"]))
        if not candidates:
            candidates = by_fuzzy.get(norm_title(r["Title"]))
        if not candidates:
            skipped.append(r["Title"])
            continue

        dates = [d for d, _ in candidates]
        real_dates = [d for d in dates if d != STILL_CHECKED_OUT]
        notes = (r.get("Notes") or "").replace(
            "Date checked out not available from this export", ""
        ).strip("; ").strip()

        if not real_dates:
            extra = "Still checked out per library history as of latest check"
            r["Notes"] = (notes + "; " + extra).strip("; ") if notes else extra
            updated += 1
            continue

        chosen = real_dates[0] if len(real_dates) == 1 else most_recent(real_dates)
        r["Date Started"] = datetime.datetime.strptime(chosen, "%m/%d/%Y").date().isoformat()

        if len(set(real_dates)) > 1:
            others = ", ".join(sorted(set(real_dates) - {chosen}))
            extra = f"Checked out from library multiple times (also {others})"
            notes = (notes + "; " + extra).strip("; ") if notes else extra
        r["Notes"] = notes
        updated += 1

    return updated, skipped


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    dates_path, in_csv, out_csv = sys.argv[1:4]
    by_light, by_fuzzy = load_checkout_dates(dates_path)

    with open(in_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    updated, skipped = apply_dates(rows, by_light, by_fuzzy)
    print(f"updated {updated} rows; {len(skipped)} library rows had no matching checkout record")
    for t in skipped:
        print("  no match:", t)

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
