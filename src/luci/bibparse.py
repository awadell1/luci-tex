from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path

import bibtexparser


@contextmanager
def _suppress_bibtexparser_warnings():
    """Temporarily silence noisy bibtexparser warnings about nonstandard types."""
    logger = logging.getLogger("bibtexparser.bparser")
    prev_level = logger.level
    try:
        logger.setLevel(logging.ERROR)
        yield
    finally:
        logger.setLevel(prev_level)


def _author_last_names(author_field: str) -> list[str]:
    """Extract last names from a BibTeX/BibLaTeX author field.

    Supports common "Last, First" and "First Last" variants, splits on top-level
    " and ", and ignores brace-wrapped groups. The special biblatex marker
    "others" is ignored.
    """
    # Split on top-level "and"; biblatex also uses "and others" which we filter
    parts = re.split(r"\s+and\s+", author_field)
    last_names: list[str] = []
    for name in parts:
        name = name.strip().strip("{}")
        if not name or name.lower() == "others":
            continue
        if "," in name:
            last = name.split(",", 1)[0].strip()
        else:
            toks = name.split()
            last = toks[-1].strip() if toks else ""
        last = last.strip("{}")
        if last:
            last_names.append(last)
    return last_names


def parse_bibliographies(bib_files: Iterable[Path]) -> dict[str, list[str]]:
    """Parse .bib files (BibTeX or BibLaTeX) and return key -> author last names.

    - Handles non-standard (biblatex) entry types by ignoring type validity and
      focusing on field extraction.
    - Prefers "author" field; falls back to "editor" if author is missing.
    - Returns a mapping of entry key to a list of last names (in order).
    """
    author_map: dict[str, list[str]] = {}

    for bib in bib_files:
        try:
            with open(bib, encoding="utf-8") as fh, _suppress_bibtexparser_warnings():
                parser = bibtexparser.bparser.BibTexParser()
                parser.ignore_nonstandard_types = False  # accept biblatex types
                parser.common_strings = True
                parser.homogenize_fields = False
                db = bibtexparser.load(fh, parser=parser)
        except Exception as exc:  # pragma: no cover - defensive
            logging.warning("Failed to parse %s: %s", bib, exc)
            continue

        for entry in db.entries:
            # bibtexparser normalizes the key as "ID" in v1.x
            key = entry.get("ID") or entry.get("id")
            if not key:
                continue
            # Prefer author; fall back to editor if needed (common in biblatex)
            auth = entry.get("author") or entry.get("authors")
            if not auth:
                auth = entry.get("editor")
            if not auth:
                continue
            names = _author_last_names(auth)
            if names:
                author_map[key] = names

    return author_map
