"""
Parses a library checkout-history CSV export (the kind you can download
from most Koha-based OPACs under "Checkout history"). This export
covers everything you've ever borrowed, so it's used to help populate a
"Have Read" list, filtered down to formats worth tracking.
"""
import csv
import re
from normalize import norm_title, norm_author

KEEP_ITEM_TYPES = {"Book", "Book - Paperback", "Audiobook on CD"}


def load_checkout_history(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out = []
    for r in rows:
        title = (r.get("Title") or "").strip()
        if not title or title == "No bibliographic record":
            continue  # deleted/unlinked catalog entries

        item_type = (r.get("Item type") or "").strip()
        if item_type not in KEEP_ITEM_TYPES:
            continue  # drop DVDs, periodicals, etc.

        call_no = (r.get("Call number") or "")
        fmt = (
            "Audiobook" if "Audio" in item_type
            else "Graphic Novel" if "GRAPHIC NOVEL" in call_no.upper()
            else "Book"
        )

        title_clean = re.sub(r"\s*/\s*$", "", title)
        title_clean = re.sub(r"\s{2,}", " ", title_clean).strip()
        title_clean = title_clean.replace("&amp;", "&")
        author = (r.get("Author") or "").strip().rstrip(",").replace("&amp;", "&")

        out.append({
            "Title": title_clean,
            "Author": author,
            "Format": fmt,
            "Source": "Library",
            "ISBN": "",  # checkout-history exports don't include ISBNs
            "Notes": "Date checked out not available from this export",
            "_nt": norm_title(title_clean),
            "_na": norm_author(author),
        })
    return out


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/checkout_history.csv"
    rows = load_checkout_history(path)
    print(f"kept {len(rows)} rows (books/paperbacks/audiobooks on CD only)")
