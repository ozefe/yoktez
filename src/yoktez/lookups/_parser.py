"""Pure parsers: HTML or JSON response bodies -> primitive tuples / typed records.

Each function is side-effect free and takes only data, never an `httpx.Response`. The
service layer (`yoktez.lookups.__init__`) is responsible for the network call and for
wrapping primitives into domain objects (e.g., running `Bilingual.parse` on names
returned by `parse_eklecikar_list`).
"""

import html as _html
import re
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from yoktez.lookups.models import University

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from yoktez.enums import UniversitySource


__all__ = [
    "parse_eklecikar_list",
    "parse_radio_input_list",
    "parse_universities_json",
]

_NULL_LITERAL = "null"

# Captures `javascript:eklecikar('NAME','ID','SEQ')` and the entity-encoded variant
# `javascript:eklecikar(&#39;NAME&#39;,&#39;ID&#39;,&#39;SEQ&#39;)`. The boundary quote
# style (`'` or `&#39;`) is captured once and back-referenced, so each call must use one
# consistent style. Apostrophes inside NAME are JS-escaped as `\'`, which after HTML
# encoding becomes `\&#39;`; the `(?<!\\)` negative lookbehind on the closing boundary
# prevents the non-greedy `.*?` from stopping early at an escaped quote.
_EKLECIKAR_PATTERN = re.compile(
    r"""javascript:eklecikar\(
        (?P<q>'|&\#39;)
        (?P<name>.*?)
        (?<!\\)(?P=q),
        (?P=q)(?P<id>\d+)(?P=q),
        (?P=q)\d+(?P=q)
        \)""",
    re.VERBOSE | re.DOTALL,
)

# Reverses both JS-escape (`\'`) and the HTML-encoded JS-escape (`\&#39;`); applied
# after `_html.unescape()` so we only need to strip the leading backslash.
_JS_ESCAPED_QUOTE = re.compile(r"\\'")


def parse_universities_json(
    data: Sequence[Mapping[str, str]], *, source: UniversitySource
) -> list[University]:
    """Map the modern JSON payload to `University` records.

    `source` is supplied by the caller (the service knows whether the batch came from
    the TR or INT endpoint) and stamped onto every record so callers downstream can
    issue correctly-scoped detail searches without re-querying.

    Note:
        The modern endpoint always carries a non-`None` `yoksisId`, but the model still
        types it as `str | None` so legacy and modern variants share the same shape.
    """
    return [
        University(
            display_name=entry["displayName"],
            id=entry["kod"],
            yoksis_id=entry["yoksisId"],
            source=source,
        )
        for entry in data
    ]


def parse_radio_input_list(
    markup: str, *, name_attr: str
) -> list[tuple[str, int, str | None]]:
    """Extract `(ad, kod, yoksisId)` triplets from a radio-list HTML fragment.

    Used by the modern AJAX endpoints (`tarama.jsp?ajax=getEnstitu|getABD|...`): each
    option is an `<input name="{name_attr}" ad="..." kod="..." yoksisId="...">`.

    `yoksisId` is returned as `None` when the attribute is missing entirely (e.g., the
    divisions endpoint never carries it) or when it equals the literal string `"null"`
    (the bulk endpoints encode legacy-source entries that way). Only inputs whose
    `name=` matches `name_attr` are considered.
    """
    soup = BeautifulSoup(markup, "lxml")
    triplets: list[tuple[str, int, str | None]] = []

    for tag in soup.find_all("input", attrs={"name": name_attr}):
        ad = _flat(tag.get("ad"))
        kod = _flat(tag.get("kod"))
        if ad is None or kod is None:
            continue

        # BS4 + lxml lowercases HTML attribute names, so the source `yoksisId` surfaces
        # as `yoksisid`.
        yoksis_raw = _flat(tag.get("yoksisid"))
        yoksis_id = None if yoksis_raw in (None, _NULL_LITERAL) else yoksis_raw

        triplets.append((ad, int(kod), yoksis_id))

    return triplets


def parse_eklecikar_list(markup: str) -> list[tuple[str, int]]:
    r"""Extract `(name, id)` pairs from a legacy `eklecikar()` HTML fragment.

    Used by the old `*Ekle.jsp` endpoints and `SearchDizin`: the data lives in
    `<a href="javascript:eklecikar('NAME','ID','SEQ')">` anchors. Regex-based over the
    raw text rather than BS4-walking, because the keyword catalog dump can run to tens
    of MB and BS4 is roughly two orders of magnitude slower than the regex for no useful
    gain (the data of interest only lives in `href` attrs).

    Handles both quote styles in one pass (bare `'` and HTML-encoded `&#39;`) and
    correctly skips JS-escaped apostrophes embedded inside names (e.g.
    `A Clergyman\'s Daughter`).
    """
    pairs: list[tuple[str, int]] = []

    for match in _EKLECIKAR_PATTERN.finditer(markup):
        raw_name = match.group("name")
        unescaped = _html.unescape(raw_name)
        name = _JS_ESCAPED_QUOTE.sub("'", unescaped)

        pairs.append((name, int(match.group("id"))))

    return pairs


def _flat(value: str | list[str] | None) -> str | None:
    """Reduce a BS4 attribute value to a plain `str | None`.

    BS4 returns a list for HTML multi-valued attributes like `class`; the YOK NTC radio
    inputs never use multi-valued attrs for `ad` / `kod` / `yoksisId`, so the first
    element is the truthful value when a list does appear.
    """
    if value is None:
        return None

    if isinstance(value, list):
        return value[0] if value else None

    return value
