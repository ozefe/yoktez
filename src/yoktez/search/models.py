"""Value objects returned by `SearchService`."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from collections.abc import Iterator

    from yoktez.enums import ThesisLanguage, ThesisType

__all__ = ["SearchResults", "Thesis"]


@dataclass(frozen=True, slots=True)
class Thesis:
    """A single thesis as it appears on a YOK NTC search result page.

    Attributes:
        registration_no: Opaque `kayitNo` token; pair with `thesis_no` to address
            metadata/asset endpoints.
        thesis_no: Opaque `data-tezno` token from the result card. `None` only on
            malformed cards.
        display_no: Human-readable thesis number (the value shown next to `Tez No:`);
            `None` when the card omits it.
        title: Original-language title; `None` when the card omits it.
        title_translated: Translated title; `None` when no translation is present.
        author: Author name as displayed; `None` when omitted.
        year: Defense year; `None` when omitted or unparsable.
        subject_raw: Raw subject string from the result card; bilingual parsing is left
            to the caller (subjects can be multi-valued and comma-separated).
        degree_type: Resolved academic degree level.
        language: Resolved thesis language.
        affiliation_raw: Raw institutional affiliation string (university / institute
            / division hierarchy). Parsing is left to the caller.
    """

    registration_no: str
    thesis_no: str | None
    display_no: int | None
    title: str | None
    title_translated: str | None
    author: str | None
    year: int | None
    subject_raw: str | None
    degree_type: ThesisType
    language: ThesisLanguage
    affiliation_raw: str


@dataclass(frozen=True, slots=True)
class SearchResults:
    """Immutable, sliceable wrapper over a sequence of `Thesis`.

    Attributes:
        items: The result theses in result-page order. Capped at 2,000 by YOK NTC.
        total: Number of theses in the YOK NTC database matching the query. May exceed
            `len(items)` when the database-wide total exceeds the 2000-card cap; in that
            case the caller must narrow the query (additional filters, tighter year
            range, ...) to retrieve the remainder.
    """

    items: tuple[Thesis, ...]
    total: int

    def __len__(self) -> int:
        """Return the number of results."""
        return len(self.items)

    def __iter__(self) -> Iterator[Thesis]:
        """Iterate over the results in order."""
        return iter(self.items)

    @overload
    def __getitem__(self, key: int) -> Thesis: ...
    @overload
    def __getitem__(self, key: slice) -> SearchResults: ...
    def __getitem__(self, key: int | slice) -> Thesis | SearchResults:
        """Index by `int` for a single `Thesis`; slice for a new `SearchResults`."""
        if isinstance(key, slice):
            # Slicing yields a window into the same query; `total` describes the
            # underlying match set and is preserved verbatim.
            return SearchResults(self.items[key], total=self.total)

        return self.items[key]
