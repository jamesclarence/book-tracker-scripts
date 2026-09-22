"""
Parses a library list exported in RIS format from a Koha-based OPAC.

RIS is a real tagged bibliographic format: each record is a block of
lines like

    TY  - BOOK
    AU  - Mitchell,David
    TI  - Cloud atlas: a novel
    SN  - 9780812994711
    KW  - Fiction
    KW  - Graphic novels
    ER  -

...terminated by an "ER" line. Multi-value fields (authors, keywords,
ISBNs) can repeat. This is far more reliable to parse than an ISBD
export (see parse_library_isbd.py) - if your library's OPAC offers an
RIS export option, prefer it.
"""
import re
from normalize import norm_title_light, norm_author


def parse_ris_records(ris_path):
    """Low-level RIS parser -> list of dicts keyed by RIS tag
    (AU/KW/SN are always lists; everything else is a string)."""
    with open(ris_path, encoding="utf-8") as f:
        text = f.read()

    records = []
    cur = None
    last_tag = None

    for raw_line in text.split("\n"):
        line = raw_line.rstrip("\r")

        if line.startswith("TY  - "):
            cur = {"AU": [], "KW": [], "SN": []}
            last_tag = "TY"
            cur["TY"] = line[6:].strip()

        elif line.startswith("ER"):
            if cur is not None:
                records.append(cur)
            cur = None
            last_tag = None

        elif cur is not None and len(line) >= 2 and line[2:6] == "  - ":
            tag = line[:2]
            val = line[6:].strip()
            if tag in ("AU", "KW", "SN"):
                cur[tag].append(val)
            else:
                cur[tag] = val
            last_tag = tag

        elif cur is not None and line.strip():
            # Continuation of a wrapped value (no new tag on this line).
            if last_tag in ("AU", "KW", "SN"):
                if cur[last_tag]:
                    cur[last_tag][-1] = cur[last_tag][-1] + " " + line.strip()
            elif last_tag and last_tag in cur:
                cur[last_tag] = str(cur[last_tag]) + " " + line.strip()

    return records


def author_last_first_to_first_last(a):
    a = a.strip().strip(".")
    if "," in a:
        last, _, first = a.partition(",")
        return f"{first.strip()} {last.strip()}".strip()
    return a


def clean_isbn(v):
    """Some SN fields carry trailing cataloger notes, e.g.
    "0679728759 (trade paper)" or "9780374299255 (hardcover : alk. paper)".
    Keep only the leading digit/X run."""
    v = (v or "").strip()
    m = re.match(r"^([\dXx][\dXx\- ]*[\dXx])", v)
    if m:
        return re.sub(r"[\-\s]", "", m.group(1))
    return v


COMIC_MARKERS = ("comic", "graphic novel")


def detect_format(keywords):
    """Format detection via subject-heading keywords - e.g. "Graphic
    novels", "Comics (Graphic works)", "Superhero comics" - rather than
    a fragile text search over a whole record."""
    for kw in keywords:
        if any(m in kw.lower() for m in COMIC_MARKERS):
            return "Graphic Novel"
    return "Book"


def load_library_shelf_ris(ris_path):
    records = parse_ris_records(ris_path)
    out = []
    for r in records:
        title = re.sub(r"\s+", " ", r.get("TI", "")).strip()
        raw_author = r["AU"][0] if r["AU"] else ""  # first author only, to
                                                      # match how we track
                                                      # a single author per
                                                      # book elsewhere
        author = author_last_first_to_first_last(raw_author)
        isbn = clean_isbn(r["SN"][0]) if r["SN"] else ""
        fmt = detect_format(r["KW"])

        out.append({
            "Title": title,
            "Author": author,
            "Format": fmt,
            "Source": "Library",
            "ISBN": isbn,
            "_nt": norm_title_light(title),
            "_na": norm_author(author),
        })
    return out


if __name__ == "__main__":
    import sys
    from collections import Counter
    path = sys.argv[1] if len(sys.argv) > 1 else "data/library_shelf.ris"
    rows = load_library_shelf_ris(path)
    print(f"parsed {len(rows)} rows")
    print("format breakdown:", Counter(r["Format"] for r in rows))
    print("rows missing an ISBN:", sum(1 for r in rows if not r["ISBN"]))
