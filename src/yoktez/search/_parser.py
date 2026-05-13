"""HTML/JSON parser for YOK NTC search-result pages.

The page mixes BeautifulSoup-friendly DOM with an inline `<script>` block hosting a
JS-object literal. The two halves are correlated; the parser walks the DOM, looks up
each tag's matching JSON entry, and stitches the two into a typed model.
"""

import json
import logging
import re
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from yoktez.enums import ThesisLanguage, ThesisType
from yoktez.errors import ParseError
from yoktez.search.models import SearchResults, Thesis

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bs4 import Tag

__all__ = ["parse_search_page"]

_logger = logging.getLogger("yoktez.search")

_REFERENCE_DATA = re.compile(
    r"const\s+referenceData\s*=\s*(\{.*?\})\s*;",
    re.DOTALL,
)

# YOK NTC emits a trailing comma before the closing `}` of `referenceData`; this is
# valid JS but invalid JSON. Strip it before `json.loads`.
_TRAILING_COMMA = re.compile(r",(\s*})")

_TEZ_NO_PREFIX = re.compile(r"^\s*Tez\s*No\s*:\s*", re.IGNORECASE)

# Captures the database-wide match total from the `.warning-text` advisory block.
# Format: "Arama sonucunda  <N> kayıt bulundu." where <N> uses "." as the Turkish
# thousand-separator (e.g. "66.816" == 66816). The optional follow-up line
# "2.000 tanesi görüntülenmektedir." reports the 2000-card cap and is ignored: the cap
# is a library-side invariant.
_RESULT_TOTAL = re.compile(r"Arama\s+sonucunda\s+([\d.]+)\s+kayıt\s+bulundu")

# Cheap presence check used to distinguish "advisory block is missing" (legitimate
# empty-result page) from "advisory block is present but unparsable" (real degradation
# worth warning about).
_ADVISORY_MARKER = "warning-text"


def parse_search_page(html: str) -> SearchResults:
    """Parse a YOK NTC search-results page into a `SearchResults`.

    Args:
        html: Raw HTML body returned by the search endpoint.

    Returns:
        Parsed results in document order.

    Raises:
        ParseError: The `referenceData` script block is missing or invalid JSON, a
            result-card has no matching JSON entry, or a `from_display` lookup misses
            (e.g., a previously-unseen Turkish degree type or language label arrived on
            the wire).
    """
    reference_data = _extract_reference_data(html)
    soup = BeautifulSoup(html, "lxml")

    return SearchResults(
        items=tuple(
            _result_card_to_thesis(card, reference_data)
            for card in soup.select("div.result-card[data-index]")
        ),
        total=_extract_total(html),
    )


def _extract_total(html: str) -> int:
    match = _RESULT_TOTAL.search(html)
    if match is None:
        # Advisory block is only emitted when the server has something to report; absent
        # block in practice means an empty result set. But if the block IS present and
        # the regex still missed, that is a wire-shape drift worth surfacing.
        if _ADVISORY_MARKER in html:
            _logger.warning(
                "result-total advisory block present but regex did not match; wire "
                "shape may have changed"
            )
        return 0

    return int(match.group(1).replace(".", ""))


def _extract_reference_data(html: str) -> dict[str, dict[str, dict[str, str]]]:
    match = _REFERENCE_DATA.search(html)
    if match is None:
        msg = "referenceData script block not found"
        raise ParseError(msg)

    cleaned = _TRAILING_COMMA.sub(r"\1", match.group(1))
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        msg = f"referenceData block is not valid JSON: {exc}"
        raise ParseError(msg) from exc


def _result_card_to_thesis(
    card: Tag, reference_data: Mapping[str, Mapping[str, Mapping[str, str]]]
) -> Thesis:
    data_index = _str_attr(card, "data-index")
    if data_index is None or data_index not in reference_data:
        msg = f"result-card data-index={data_index!r} has no referenceData entry"
        raise ParseError(msg)

    meta = reference_data[data_index].get("meta", {})

    try:
        degree_type = ThesisType.from_display(meta["type"])
        language = ThesisLanguage.from_display(meta["lang"])
    except (KeyError, ValueError) as exc:
        msg = f"unrecognized type/lang on card data-index={data_index}: {exc}"
        raise ParseError(msg) from exc

    return Thesis(
        registration_no=_str_attr(card, "data-kayitno") or "",
        thesis_no=_str_attr(card, "data-tezno"),
        display_no=_extract_display_no(card),
        title=_stripped_text(card.select_one(".card-title")),
        title_translated=_stripped_text(card.select_one(".text-group .card-info")),
        author=meta.get("author") or None,
        year=_try_int(meta.get("year")),
        subject_raw=meta.get("subject") or None,
        degree_type=degree_type,
        language=language,
        affiliation_raw=meta.get("yer", ""),
    )


def _str_attr(tag: Tag, name: str) -> str | None:
    """Get a string-typed attribute value, flattening BS4's multi-value list shape."""
    value = tag.attrs.get(name)

    if isinstance(value, list):
        return value[0] if value else None

    return value


def _stripped_text(tag: Tag | None) -> str | None:
    """Get a tag's whitespace-stripped text content; `None` for missing or empty."""
    if tag is None:
        return None

    text = tag.get_text(strip=True)
    return text or None


def _try_int(value: str | None) -> int | None:
    """Parse `value` as `int`; return `None` on missing or non-numeric input."""
    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def _extract_display_no(card: Tag) -> int | None:
    for label in card.find_all("strong"):
        if not _TEZ_NO_PREFIX.match(label.get_text(strip=True)):
            continue

        parent = label.parent
        if parent is None:
            continue

        full = parent.get_text(" ", strip=True)
        stripped = _TEZ_NO_PREFIX.sub("", full).strip()

        return _try_int(stripped)

    return None
