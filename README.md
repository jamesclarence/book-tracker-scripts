# Book tracker scripts

Scripts for pulling together a personal reading tracker from two sources:
a [Goodreads](https://www.goodreads.com) library export, and exports from
a public library's [Koha](https://koha-community.org/) OPAC (a common
open-source library catalog system). Written for my own library's setup,
but the parsing/merge logic is generic to any Koha-based catalog.

Output is three CSVs - `want_to_read.csv`, `currently_reading.csv`,
`have_read.csv` - meant to be imported into a spreadsheet, with columns:
`Title, Author, Format, Source, Date Added, Date Started, Date Finished,
Rating (1-5), ISBN, Cover, Notes`.

No personal data (actual book titles, reading history, library account
info, etc.) is included in this repo - just the parsing/scraping/merge
logic. You'll need to supply your own exports as input.

## Pipeline

**1. Goodreads export** (`parse_goodreads.py`)
Settings → Import/Export → Export Library gives a clean CSV. This just
reads it with `csv.DictReader`, sorts rows into shelves by the
`Exclusive Shelf` column, and does some light cleanup (ISBN unwrapping,
audiobook format detection, "did not finish"/reread notes).

**2a. Library want-to-read list, RIS export** (`parse_library_ris.py`)
[RIS](https://en.wikipedia.org/wiki/RIS_(file_format)) is a real tagged
bibliographic format - way more reliable to parse than ISBD (below).
Koha OPACs that let you export a list generally offer RIS as one of the
format options alongside ISBD/MARC/BibTeX; prefer RIS if it's available.
Detects "graphic novel" format from the record's subject-heading
keywords rather than a text search, which is much more accurate.

**2b. Library want-to-read list, ISBD export** (`parse_library_isbd.py`)
*Legacy / not recommended* - kept for reference. ISBD exports from Koha
are just loosely-formatted HTML text, not real structured data, so this
has to regex-hunt for title/author pairs and nearby ISBN labels. It
worked, but mismatched or dropped ISBNs on a meaningful fraction of
records. Switched to the RIS parser once I found RIS was an export
option.

**3. Library checkout history** (`parse_checkout_history.py`)
Most Koha OPACs have a "Checkout history" page with a CSV export
covering your full borrowing history. This filters it down to formats
worth tracking (books, paperbacks, audiobooks on CD - drops DVDs and
any deleted/unlinked catalog entries) and guesses graphic-novel format
from the call number.

**4. Checkout dates, scraped from the live page** (`scrape_checkout_dates.js`
+ `apply_checkout_dates.py`)
The checkout-history CSV export doesn't include dates. The web page
does, but only per-row, behind a "+" you'd otherwise have to click on
every single item. `scrape_checkout_dates.js` is a browser-console
snippet that instead reads the date directly out of the page's
DataTables in-memory model (see the file for how/why that works), for
every row in one pass. `apply_checkout_dates.py` then matches those
scraped dates back onto rows in an existing `have_read.csv` by title,
handling the fact that a merged row keeps its Goodreads-style title
wording rather than the library's.

**5. Normalization + merge** (`normalize.py`, `merge.py`)
Goodreads and a library catalog rarely agree on exact title/author
formatting, so before matching, titles get stripped of subtitles,
parenthetical series info, and leading articles, and authors get
reduced to a lowercase last name. Matching tries ISBN first, then
normalized title+author, then title alone. A match merges the two
rows into one, labeled e.g. `"Goodreads & Library"`.

**6. Orchestration** (`build_tracker.py`)
Ties it all together end to end:

```bash
python build_tracker.py \
    --goodreads data/goodreads_export.csv \
    --library-ris data/library_shelf.ris \
    --checkout-history data/checkout_history.csv \
    --out-dir output/
```

## Known limitations

- Only one author per book is tracked (Goodreads' primary-author field;
  a library RIS record's first `AU` tag). Co-authors/illustrators are
  dropped.
- Series/volume matching is imperfect - the aggressive title
  normalization used for cross-source matching sometimes collapses
  distinct volumes of a series into one row if a library catalog record
  happens to format the volume number differently than Goodreads does.
- Checkout-history dates are *checkout* dates, not *finished-reading*
  dates - treat `Date Started` as an approximation for library-sourced
  rows.
