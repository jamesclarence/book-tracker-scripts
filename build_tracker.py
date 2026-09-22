"""
End-to-end pipeline: reads a Goodreads export + a library RIS export +
a library checkout-history export, merges/dedupes them, and writes out
three CSVs (want_to_read.csv, currently_reading.csv, have_read.csv)
ready to import into a spreadsheet.

Usage:
    python build_tracker.py \
        --goodreads data/goodreads_export.csv \
        --library-ris data/library_shelf.ris \
        --checkout-history data/checkout_history.csv \
        --out-dir output/

All three inputs are optional - pass only the ones you have. Column
layout:
    Title, Author, Format, Source, Date Added, Date Started,
    Date Finished, Rating (1-5), ISBN, Cover, Notes
"""
import argparse
import csv
import datetime
import os

from parse_goodreads import load_goodreads
from parse_library_ris import load_library_shelf_ris
from parse_checkout_history import load_checkout_history
from merge import merge

COLUMNS = [
    "Title", "Author", "Format", "Source", "Date Added", "Date Started",
    "Date Finished", "Rating (1-5)", "ISBN", "Cover", "Notes",
]


def to_iso(d):
    return d.isoformat() if d else ""


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for r in rows:
            # Prefix ISBNs with an apostrophe so spreadsheet apps don't
            # auto-convert them to numbers and strip leading zeros on
            # 10-digit ISBNs.
            isbn = ("'" + r["ISBN"]) if r.get("ISBN") else ""
            w.writerow([
                r.get("Title", ""), r.get("Author", ""), r.get("Format", ""),
                r.get("Source", ""), to_iso(r.get("Date Added")),
                to_iso(r.get("Date Started")), to_iso(r.get("Date Finished")),
                r.get("Rating") or "", isbn, "", r.get("Notes", ""),
            ])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--goodreads", help="Goodreads library export CSV")
    ap.add_argument("--library-ris", help="Library shelf/list export in RIS format")
    ap.add_argument("--checkout-history", help="Library checkout-history export CSV")
    ap.add_argument("--out-dir", default="output")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    goodreads = {"Want to Read": [], "Currently Reading": [], "Have Read": []}
    if args.goodreads:
        goodreads = load_goodreads(args.goodreads)

    library_shelf = load_library_shelf_ris(args.library_ris) if args.library_ris else []
    checkout_history = load_checkout_history(args.checkout_history) if args.checkout_history else []

    want_to_read = merge(goodreads["Want to Read"], library_shelf)
    have_read = merge(goodreads["Have Read"], checkout_history)
    currently_reading = goodreads["Currently Reading"]

    want_to_read.sort(key=lambda b: b.get("Date Added") or datetime.date.min, reverse=True)
    currently_reading.sort(key=lambda b: b.get("Date Added") or datetime.date.min, reverse=True)
    have_read.sort(key=lambda b: b.get("Date Finished") or datetime.date.min, reverse=True)

    write_csv(os.path.join(args.out_dir, "want_to_read.csv"), want_to_read)
    write_csv(os.path.join(args.out_dir, "currently_reading.csv"), currently_reading)
    write_csv(os.path.join(args.out_dir, "have_read.csv"), have_read)

    print("Want to Read:", len(want_to_read))
    print("Currently Reading:", len(currently_reading))
    print("Have Read:", len(have_read))


if __name__ == "__main__":
    main()
