"""Value objects returned by the `lookups` sub-service.

All models are frozen + slotted so they are immutable, hashable, and cheap to compare.

Two intentional asymmetries:

- `University.id` is a `str` (opaque Base64-like token from the modern JSON endpoint),
  while `Institute.id` / `Division.id` / etc. are `int`.
- `yoksis_id` is `str | None` because the legacy bulk endpoints don't carry one;
  hierarchical lookups (`institutes`, `divisions`) require a non-`None` value.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yoktez.bilingual import Bilingual
    from yoktez.enums import KeywordGroup, UniversitySource

__all__ = [
    "Department",
    "Division",
    "Institute",
    "Keyword",
    "Section",
    "Subject",
    "University",
]


@dataclass(frozen=True, slots=True)
class University:
    """A university (Turkish or international) known to the YOK NTC."""

    display_name: str
    id: str
    yoksis_id: str | None
    source: UniversitySource


@dataclass(frozen=True, slots=True)
class Institute:
    """An institute under a university."""

    display_name: str
    id: int
    yoksis_id: str | None


@dataclass(frozen=True, slots=True)
class Division:
    """A division under an institute."""

    display_name: str
    id: int


@dataclass(frozen=True, slots=True)
class Subject:
    """A subject classifier with bilingual display."""

    display: Bilingual
    id: int


@dataclass(frozen=True, slots=True)
class Keyword:
    """A keyword with bilingual display and an optional academic group."""

    display: Bilingual
    id: int
    group: KeywordGroup | None


@dataclass(frozen=True, slots=True)
class Department:
    """A department. Currently unused by search filters."""

    display_name: str
    id: int


@dataclass(frozen=True, slots=True)
class Section:
    """A section. Currently unused by search filters."""

    display_name: str
    id: int
