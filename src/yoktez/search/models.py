"""Value objects returned by `SearchService`."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from collections.abc import Iterator

    from yoktez.enums import ThesisLanguage, ThesisType

__all__ = ["SearchResults", "Thesis"]


@dataclass(frozen=True, slots=True)
class Thesis:
    """A single thesis as it appears on a YOK NTC search result page."""

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
    """Immutable, sliceable wrapper over a sequence of `Thesis`."""

    items: tuple[Thesis, ...]

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
            return SearchResults(self.items[key])

        return self.items[key]
