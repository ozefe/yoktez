"""Value objects returned by `MetadataService`."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from yoktez.bilingual import Bilingual

__all__ = ["Affiliation", "References", "ThesisMetadata"]

# YOK NTC concatenates affiliation tiers with a literal "/" surrounded by whitespace.
# The tier hierarchy is fixed: university / institute / division / section.
_SEPARATOR = "/"
_MAX_TIERS = 4


@dataclass(frozen=True, slots=True)
class Affiliation:
    """A four-tier institutional affiliation.

    Attributes:
        raw: The original slash-separated string as returned by YOK NTC, preserved
            verbatim.
        university: The university name (always populated; equals the entire input when
            no separator was present).
        institute: The institute name. `None` when the source has fewer than two tiers.
        division: The division name. `None` when the source has fewer than three tiers.
        section: The section name. `None` when the source has fewer than four tiers.
            When the source carries more than four tiers, surplus chunks fold back into
            `section` joined by ` / ` (rare; defensive).
    """

    raw: str
    university: str
    institute: str | None
    division: str | None
    section: str | None

    @classmethod
    def parse(cls, raw_text: str) -> Self:
        """Parse a `"University / Institute / Division / Section"` string.

        Args:
            raw_text: Source string. Preserved verbatim in `raw`.

        Returns:
            An `Affiliation` with whitespace-stripped tiers. Missing trailing tiers
            (including empty trailing chunks like in `"U / I /"`) become `None`.
        """
        parts = [chunk.strip() for chunk in raw_text.split(_SEPARATOR)]

        # Empty trailing chunks ("U / I /") read as 2 tiers, not 3 with a blank
        # institute -- otherwise the trailing-slash and no-trailing-slash forms would
        # parse to different shapes.
        while len(parts) > 1 and not parts[-1]:
            parts.pop()

        # Surplus tiers beyond the four-slot hierarchy fold back into the section slot
        # joined by " / "; YOK NTC has not been observed emitting more than four tiers,
        # this branch is defensive.
        if len(parts) > _MAX_TIERS:
            parts = [
                *parts[: _MAX_TIERS - 1],
                f" {_SEPARATOR} ".join(parts[_MAX_TIERS - 1 :]),
            ]
        parts.extend([""] * (_MAX_TIERS - len(parts)))

        university, institute, division, section = parts

        return cls(
            raw=raw_text,
            university=university,
            institute=institute or None,
            division=division or None,
            section=section or None,
        )


@dataclass(frozen=True, slots=True)
class References:
    """Pre-formatted citation strings as returned by YOK NTC.

    Each field carries the wire-form HTML markup (e.g., `<i>...</i>` around the title)
    verbatim; callers wanting plain text are responsible for stripping it.

    Attributes:
        apa: APA-style reference.
        ieee: IEEE-style reference.
        mla: MLA-style reference.
        chicago: Chicago-style reference.
        harvard: Harvard-style reference.
    """

    apa: str
    ieee: str
    mla: str
    chicago: str
    harvard: str


@dataclass(frozen=True, slots=True)
class ThesisMetadata:
    """Structured per-thesis detail.

    Attributes:
        supervisor: Supervisor name as returned (uppercased, `PROF. DR. ...`-style);
            `None` when the source omits it.
        affiliation: Parsed hierarchy; `None` when the source omits it.
        keywords: Bilingual keywords (`Turkish = English` pairs). `None` when the source
            omits the keyword field entirely; an empty list is impossible in practice
            but collapses to `None` as well.
        abstract_tr: Turkish abstract; `None` when absent.
        abstract_other: Non-Turkish abstract (typically English, but may match the
            thesis's primary non-Turkish language); `None` when absent.
        references: Pre-formatted citation strings; `None` when no `*_ref` field was
            populated.
    """

    supervisor: str | None
    affiliation: Affiliation | None
    keywords: list[Bilingual] | None
    abstract_tr: str | None
    abstract_other: str | None
    references: References | None
