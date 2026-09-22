"""
Shared title/author normalization used to match the same book across
different sources (e.g. Goodreads vs. a library catalog export), which
rarely agree on exact title/author formatting.
"""
import re


def norm_title(t):
    """Aggressive normalization for matching titles ACROSS different
    sources (Goodreads vs. library), which format titles differently -
    e.g. "Cloud Atlas: A Novel" vs. "Cloud atlas". Strips subtitles,
    parenthetical series info, and leading articles.

    NOTE: this intentionally collapses volume/series numbering in some
    cases, which can merge separate books in a series into one row if
    you're not careful. See merge.py for how this tradeoff is handled.
    """
    t = t or ""
    t = t.split(":")[0].split(";")[0]
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"\.\s*(volume|vol|book)\b.*", "", t, flags=re.I)
    t = re.sub(r"[^a-z0-9 ]", "", t.lower())
    t = re.sub(r"^(the|a|an)\s+", "", t.strip())
    t = re.sub(r"\s+", " ", t).strip()
    return t


def norm_title_light(t):
    """Light normalization for matching titles WITHIN the same source
    (e.g. two exports from the same library catalog), where formatting
    is already consistent and volume/series distinctions must be kept.
    """
    t = t or ""
    t = t.strip()
    t = re.sub(r"\s*/\s*$", "", t)  # trailing MARC "/" punctuation
    t = re.sub(r"\.$", "", t)
    t = re.sub(r"[^a-z0-9]", "", t.lower())
    return t


def norm_author(a):
    a = a or ""
    a = a.split(";")[0].split("&")[0].split(",")[0]
    a = re.sub(r"[^a-z ]", "", a.lower())
    parts = a.split()
    return parts[-1] if parts else ""
