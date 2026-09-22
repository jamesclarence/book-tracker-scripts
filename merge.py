"""
Merges a Goodreads-derived list with a library-derived list, deduping
entries that represent the same book so you don't end up with two rows
for one title.

Matching, in priority order:
  1. Exact ISBN match.
  2. Normalized (title, author) match.
  3. Normalized title alone (fallback for author-formatting mismatches
     between sources, e.g. "Rucka, Greg" vs. "Greg Rucka").

Whichever source's row is created FIRST becomes the "base" row that
survives; the other source just contributes its Source label, ISBN (if
the base row is missing one), and Notes. Each dict passed in must
already have "_nt" and "_na" keys from normalize.py.
"""


def merge(primary_list, secondary_list, secondary_label_suffix="Library"):
    """primary_list is typically Goodreads rows (kept as-is on a match);
    secondary_list is typically library rows. Rows only in
    secondary_list are appended as new rows with Source = secondary
    only.
    """
    by_isbn = {}
    by_title_author = {}
    merged = []

    for row in primary_list:
        d = dict(row)
        d["_from_primary"] = True
        merged.append(d)
        if row["ISBN"]:
            by_isbn[row["ISBN"]] = merged[-1]
        if row["_nt"]:
            by_title_author[(row["_nt"], row["_na"])] = merged[-1]

    for row in secondary_list:
        target = None
        if row["ISBN"] and row["ISBN"] in by_isbn:
            target = by_isbn[row["ISBN"]]
        elif row["_nt"] and (row["_nt"], row["_na"]) in by_title_author:
            target = by_title_author[(row["_nt"], row["_na"])]
        elif row["_nt"]:
            for m in merged:
                if m["_nt"] == row["_nt"]:
                    target = m
                    break

        if target:
            # Only relabel as "merged" if we matched an actual primary-
            # source row - two secondary-only rows colliding with each
            # other (e.g. two catalog records for the same physical
            # item) should stay under the secondary source, not get
            # mislabeled as a primary match.
            if target.get("_from_primary"):
                target["Source"] = f"{target['Source']} & {secondary_label_suffix}"
            if not target["ISBN"] and row["ISBN"]:
                target["ISBN"] = row["ISBN"]
            existing_notes = target.get("Notes") or ""
            new_notes = row.get("Notes") or ""
            if new_notes and new_notes not in existing_notes:
                target["Notes"] = (existing_notes + "; " + new_notes).strip("; ")
        else:
            d = dict(row)
            merged.append(d)
            if row["ISBN"]:
                by_isbn[row["ISBN"]] = merged[-1]
            if row["_nt"]:
                by_title_author[(row["_nt"], row["_na"])] = merged[-1]

    return merged
