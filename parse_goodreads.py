"""
Parse a Goodreads library export CSV into the three shelves we care about:
Want to Read, Currently Reading, and Have Read.

Goodreads lets you export your whole library as a CSV from
Settings > Import/Export > Export Library. It's already clean, tabular
data, so this is a straightforward csv.DictReader pass with some light
normalization for matching against other sources later.
"""
import csv
import datetime
from normalize import norm_title, norm_author


def clean_isbn(v):
    """Goodreads wraps ISBNs like ="9780316403979" to stop spreadsheet
    apps from mangling them as numbers. Strip that wrapper."""
    v = (v or "").strip()
    if v.startswith('="') and v.endswith('"'):
        v = v[2:-1]
    return v.strip()


def parse_date_slash(v):
    """Goodreads dates are 'YYYY/MM/DD'."""
    v = (v or "").strip()
    if not v:
        return None
    try:
        return datetime.datetime.strptime(v, "%Y/%m/%d").date()
    except ValueError:
        return None


def load_goodreads(csv_path):
    """Returns {"Want to Read": [...], "Currently Reading": [...], "Have Read": [...]}
    where each entry is a dict of normalized book fields."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out = {"Want to Read": [], "Currently Reading": [], "Have Read": []}
    shelf_to_tab = {
        "to-read": "Want to Read",
        "currently-reading": "Currently Reading",
        "read": "Have Read",
        "did-not-finish": "Have Read",
    }

    for r in rows:
        tab = shelf_to_tab.get(r.get("Exclusive Shelf", ""))
        if not tab:
            continue

        binding = (r.get("Binding") or "").lower()
        fmt = "Audiobook" if "audio" in binding else "Book"
        isbn = clean_isbn(r.get("ISBN13")) or clean_isbn(r.get("ISBN"))

        try:
            rating = float(r.get("My Rating") or 0)
        except ValueError:
            rating = 0

        notes = []
        if r.get("Exclusive Shelf") == "did-not-finish":
            notes.append("Did not finish")
        try:
            read_count = int(r.get("Read Count") or 0)
        except ValueError:
            read_count = 0
        if read_count > 1:
            notes.append(f"Reread ({read_count}x)")

        title = r["Title"].strip()
        author = r["Author"].strip()  # Goodreads' primary-author field; co-authors
                                       # live in "Additional Authors" but we only
                                       # track one author per book for simplicity.

        out[tab].append({
            "Title": title,
            "Author": author,
            "Format": fmt,
            "Source": "Goodreads",
            "Date Added": parse_date_slash(r.get("Date Added")),
            "Date Started": None,
            "Date Finished": parse_date_slash(r.get("Date Read")),
            "Rating": int(rating) if rating else None,
            "ISBN": isbn,
            "Notes": "; ".join(notes),
            "_nt": norm_title(title),
            "_na": norm_author(author),
        })

    return out


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/goodreads_export.csv"
    shelves = load_goodreads(path)
    for tab, rows in shelves.items():
        print(f"{tab}: {len(rows)} rows")
