"""
Takes the CSV produced by scrape_goodreads_dates.js (title, author,
date_started, date_read - one row per book on a Goodreads shelf) and
backfills Have Read's "Date Started" column for Goodreads-sourced rows
that don't have one yet.

The main Goodreads export (parse_goodreads.py's input) doesn't include
start dates at all - they only live on the site's own shelf pages,
which is why this is a separate scrape/apply pair rather than part of
parse_goodreads.py. Scrape your "read" and "did-not-finish" shelves
with scrape_goodreads_dates.js (per_page=200, with the "Date started"
and "Date read" columns turned on) and combine the output into one CSV
before running this.

Matching is three-tier, strictest first, and a tier is only used when
it resolves to exactly one shelf record - an ambiguous match is
skipped rather than guessed at:

  1. normalize.norm_title_light + author last name - exact title,
     light normalization only.
  2. normalize.norm_title + author last name - aggressive
     normalization (strips subtitles/parentheticals/series wording).
  3. norm_series_title + author last name - a series/volume-aware
     normalization for titles like "Locke & Key, Vol. 4: Keys to the
     Kingdom" vs. a library-style "Locke & Key. Volume 4, Keys to the
     kingdom", which norm_title's subtitle-stripping doesn't reconcile
     (it only strips a ". Volume N..." tail when the period comes
     immediately before "Volume", not a ", Vol. N:" one).

Author matching reduces both sides to a last-name key, combining a
multi-word surname (e.g. "Van Pelt") the same way regardless of
whether the source writes "Last, First" (Goodreads' shelf pages) or
"First Last" (this tracker's convention) - see SURNAME_PREFIXES,
ported from enrich_and_export.py's last-name sort.

Run this on have_read.csv (build_tracker.py's output) BEFORE
enrich_and_export.py, so the backfilled dates make it into the final
workbook.

Usage:
    python apply_goodreads_start_dates.py goodreads_dates.csv \
        have_read.csv have_read_updated.csv
"""
import csv
import re
import sys
from collections import defaultdict
from datetime import datetime

from normalize import norm_title, norm_title_light

# Surname prefixes that belong WITH the following word when reducing an
# author to a last-name key (e.g. "Shelby Van Pelt" -> "Van Pelt", not
# "Pelt"). Ported from enrich_and_export.py's SURNAME_PREFIXES.
SURNAME_PREFIXES = {
    "le", "la", "de", "del", "della", "van", "von", "der", "den",
    "el", "al", "mac", "mc", "di", "du", "st", "st.", "da", "dos", "das",
}

WORD_NUMS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
}


def norm_series_title(t):
    """Finds a volume marker (vol./volume/#, a digit or a spelled-out
    number) and keeps just the series name plus that number, dropping
    everything else - including any subtitle after it. Handles both
    "vol. 4" and "volume 4" (or "volume four") equally, which is the
    gap normalize.norm_title's subtitle-stripping leaves (see module
    docstring, tier 3)."""
    t = (t or "").lower()
    t = re.sub(r"[’']", "", t)
    m = re.search(r"\bvol(?:ume)?\.?\s*#?\s*([a-z]+|\d+)\b", t)
    vol, base = None, t
    if m:
        vol_raw = m.group(1)
        vol = WORD_NUMS.get(vol_raw, vol_raw if vol_raw.isdigit() else None)
        base = t[: m.start()]
    else:
        m2 = re.search(r"#\s*(\d+)", t)
        if m2:
            vol = m2.group(1)
            base = t[: m2.start()]
    base = re.sub(r"[^\w\s]", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    return f"{base} {vol}".strip() if vol else base


def norm_author_last(a):
    """Reduces an author name to a last-name key, handling both "Last,
    First" (Goodreads shelf pages) and "First Last" (this tracker's
    convention) consistently, and combining a multi-word surname the
    same way regardless of which order it appears in."""
    a = (a or "").strip().rstrip(".")
    if not a:
        return ""
    if "," in a:
        tokens = a.split(",")[0].strip().split()
    else:
        tokens = a.split()
        if len(tokens) >= 2 and tokens[-2].lower().strip(".") in SURNAME_PREFIXES:
            tokens = tokens[-2:]
        else:
            tokens = tokens[-1:] if tokens else []
    return re.sub(r"[^\w]", "", " ".join(tokens).lower())


def parse_shelf_date(s):
    s = (s or "").strip()
    if not s:
        return ""
    for fmt in ("%b %d %Y", "%b %Y"):
        try:
            d = datetime.strptime(s, fmt)
            return d.strftime("%Y-%m") if fmt == "%b %Y" else d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def load_shelf_dates(path):
    with open(path, newline="", encoding="utf-8") as f:
        shelf_rows = list(csv.DictReader(f))

    by_light, by_agg, by_series = (
        defaultdict(list), defaultdict(list), defaultdict(list)
    )
    for r in shelf_rows:
        na = norm_author_last(r["author"])
        lt, at, st = (
            norm_title_light(r["title"]),
            norm_title(r["title"]),
            norm_series_title(r["title"]),
        )
        if lt:
            by_light[(lt, na)].append(r)
        if at:
            by_agg[(at, na)].append(r)
        if st:
            by_series[(st, na)].append(r)
    return by_light, by_agg, by_series


def find_shelf_row(title, author, by_light, by_agg, by_series):
    na = norm_author_last(author)
    for index, norm_fn in (
        (by_light, norm_title_light),
        (by_agg, norm_title),
        (by_series, norm_series_title),
    ):
        key = (norm_fn(title), na)
        if key in index and len(index[key]) == 1:
            return index[key][0]
    return None


def apply_start_dates(have_read_rows, by_light, by_agg, by_series):
    filled, no_date_on_shelf, no_match = 0, 0, []
    for row in have_read_rows:
        if "Goodreads" not in row.get("Source", ""):
            continue
        if (row.get("Date Started") or "").strip():
            continue
        shelf_row = find_shelf_row(
            row.get("Title", ""), row.get("Author", ""), by_light, by_agg, by_series
        )
        if not shelf_row:
            no_match.append(row.get("Title", ""))
            continue
        date_started = parse_shelf_date(shelf_row["date_started"])
        if date_started:
            row["Date Started"] = date_started
            filled += 1
        else:
            no_date_on_shelf += 1
    return filled, no_date_on_shelf, no_match


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    dates_path, in_csv, out_csv = sys.argv[1:4]
    by_light, by_agg, by_series = load_shelf_dates(dates_path)

    with open(in_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    filled, no_date_on_shelf, no_match = apply_start_dates(
        rows, by_light, by_agg, by_series
    )
    print(
        f"filled {filled} rows; {no_date_on_shelf} matched but have no start "
        f"date on the shelf page; {len(no_match)} had no match at all"
    )
    for title in no_match:
        print("  no match:", title)

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
