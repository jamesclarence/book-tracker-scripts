"""
LEGACY / NOT RECOMMENDED - kept for reference.

Parses a library list exported in "ISBD" format from a Koha-based OPAC
(Koha is common open-source library software used by many public
libraries). An ISBD export is really just a wall of loosely-formatted
HTML text, not a real structured format, so this has to use regexes to
find title/author pairs and hunt for an ISBN label nearby.

This is fragile: in testing it mismatched or dropped ISBNs on a
meaningful number of records and almost never correctly detected
"graphic novel" format. See parse_library_ris.py for a far more
reliable replacement - if your library's OPAC offers an RIS export
option (Koha ones generally do, alongside ISBD/MARC/BibTeX), use that
instead.
"""
import re


def load_library_shelf_isbd(isbd_path):
    data = open(isbd_path, encoding="utf-8").read()

    # Title / Author, terminated by " / Author." followed by an
    # optional publication statement, then a double <br/>.
    pat = re.compile(r'([^<]{3,300}?)\s*/\s*([^./<]{2,120}?)\.\s*(?:-[^<]*?)?<br/><br/>')
    matches = list(pat.finditer(data))

    raw = []
    for i, m in enumerate(matches):
        title = m.group(1).split("\n")[-1].strip()
        author = m.group(2).split("\n")[-1].strip()
        window_end = matches[i + 1].start() if i + 1 < len(matches) else len(data)
        window = data[m.end():window_end]

        isbn_m = re.search(r'<label>ISBN: </label>([\dXx\s]+?)\s*<br/>', window)
        isbn = ""
        graphic = False
        if isbn_m:
            parts = isbn_m.group(1).strip().split()
            isbn = next((p for p in parts if len(p) == 13), parts[0] if parts else "")
            # "graphic novel" only counts if it shows up soon after the
            # ISBN line, to avoid false positives from unrelated text
            # elsewhere on the page.
            tight_window = data[isbn_m.end(): isbn_m.end() + 900]
            graphic = bool(re.search(r"graphic novel", tight_window, re.I))

        raw.append({
            "title": title, "author": author, "isbn": isbn, "graphic": graphic,
            "bogus": title.startswith("br/>"),  # regex sometimes catches a stray fragment
        })

    # Drop bogus fragments, but salvage an ISBN they happened to carry.
    clean = []
    for r in raw:
        if r["bogus"]:
            if r["isbn"] and clean and not clean[-1]["isbn"]:
                clean[-1]["isbn"] = r["isbn"]
            continue
        clean.append(r)

    def simplify_author(a):
        a = a.split(";")[0].strip()
        a = re.sub(r"^(by|writer,|written by)\s+", "", a, flags=re.I)
        a = re.sub(r"^\[?text by\]?\s+", "", a, flags=re.I)
        return a.strip(" ,")

    out = []
    for r in clean:
        title = re.sub(r"\s+", " ", r["title"]).strip()
        author = simplify_author(r["author"])
        out.append({
            "Title": title,
            "Author": author,
            "Format": "Graphic Novel" if r["graphic"] else "Book",
            "Source": "Library",
            "ISBN": r["isbn"],
        })
    return out


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/library_shelf.isbd.txt"
    rows = load_library_shelf_isbd(path)
    print(f"parsed {len(rows)} rows (accuracy on ISBN/format is not great - see docstring)")
