"""Bilingual `Turkish = English` value pairs as returned by YOK NTC."""

from dataclasses import dataclass, field
from typing import Self

__all__ = ["Bilingual"]

# YOK NTC concatenates bilingual halves with a literal "=" surrounded by whitespace; the
# convention is stable across all bilingual fields (subjects, keywords, ...).
_SEPARATOR = "="


@dataclass(order=True, frozen=True, slots=True)
class Bilingual:
    """A bilingual display field with its Turkish and English halves.

    Construct directly when both halves are known (`Bilingual(raw=..., tr=..., en=...)`)
    or via `Bilingual.parse(raw)` for the common YOK NTC `"Turkish = English"` form.

    Attributes:
        raw: The original string as returned by YOK NTC, preserved verbatim.
        tr: The Turkish half, stripped of surrounding whitespace.
        en: The English half, stripped of surrounding whitespace, or `None` if no
            separator was present.
    """

    raw: str
    tr: str = field(kw_only=True)
    en: str | None = field(kw_only=True)

    @classmethod
    def parse(cls, raw_text: str) -> Self:
        """Parse a `"Turkish = English"` string into a `Bilingual`.

        Args:
            raw_text: Source string. Preserved verbatim in `raw`.

        Returns:
            A `Bilingual` with whitespace-stripped halves.

        Note:
            Splits on the first separator only; further occurrences stay in the English
            half (e.g., a term like `"X = Y = Z"` becomes `tr="X"`, `en="Y = Z"`). When
            no separator is present the entire input becomes `tr` and `en` is `None`.
        """
        tr, sep, en = raw_text.partition(_SEPARATOR)

        return cls(raw=raw_text, tr=tr.strip(), en=en.strip() if sep else None)
