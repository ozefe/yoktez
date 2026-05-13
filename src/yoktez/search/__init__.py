"""Search sub-package: `simple`, `advanced`, `detail`, and `recent` queries."""

from typing import TYPE_CHECKING

from yoktez._endpoints import RECENT, SEARCH
from yoktez._helpers import resolve_yoksis_id
from yoktez.enums import (
    AccessType,
    AdvancedOperator,
    MatchType,
    SearchField,
    ThesisLanguage,
    ThesisStatus,
    ThesisType,
    UniversitySource,
    coerce,
)
from yoktez.lookups.models import Division, Institute, Subject, University
from yoktez.search._parser import parse_search_page
from yoktez.search.models import SearchResults, Thesis

if TYPE_CHECKING:
    from yoktez.client import Client

__all__ = ["SearchResults", "SearchService", "Thesis"]

# YOK NTC's web interface doesn't allow year values less than 1900, earlier years are
# guaranteed bad input and should fail fast client-side rather than reach the wire.
_MIN_YEAR = 1900


class SearchService:
    """`client.search` namespace."""

    def __init__(self, client: Client) -> None:
        self.client = client

    def recent(self) -> SearchResults:
        """Fetch theses added to YOK NTC in the last 15 days.

        Returns:
            The "Recently Added" feed. The 15-day window is server-fixed and not
            user-configurable.
        """
        response = self.client.http_client.get(RECENT, params={"islem": "7"})

        return parse_search_page(response.text)

    def simple(
        self,
        term: str,
        *,
        field: SearchField | str | int = SearchField.ALL,
        access: AccessType | str | int = AccessType.ALL,
        degree_type: ThesisType | str | int = ThesisType.ALL,
    ) -> SearchResults:
        """Run a simple keyword search.

        Args:
            term: Free-text query.
            field: Which thesis fields to search.
            access: Full-text access status filter.
            degree_type: Degree-level filter.

        Returns:
            Matching theses.

        Note:
            All enum-shaped args accept the matching `Enum` member, its name (e.g.
            `"MASTER"`), or its raw int code -- unknown int codes pass through to YOK
            NTC unmodified.
        """
        response = self.client.http_client.post(
            SEARCH,
            data={
                "nevi": str(coerce(SearchField, field)),
                "izin": str(coerce(AccessType, access)),
                "tur": str(coerce(ThesisType, degree_type)),
                "neden": term,
                "islem": "1",
            },
        )

        return parse_search_page(response.text)

    def advanced(
        self,
        term1: str,
        *,
        term2: str | None = None,
        term3: str | None = None,
        op1: AdvancedOperator | str = AdvancedOperator.AND,
        op2: AdvancedOperator | str = AdvancedOperator.AND,
        field: SearchField | str | int = SearchField.ALL,
        match: MatchType | str | int = MatchType.EXACT,
    ) -> SearchResults:
        """Run an advanced (multi-term, operator-joined) search.

        Args:
            term1: First search term (required).
            term2: Second term, joined to `term1` by `op1`.
            term3: Third term, joined to `(term1 op1 term2)` by `op2`.
            op1: Boolean operator between `term1` and `term2`.
            op2: Boolean operator between `(term1 op1 term2)` and `term3`.
            field: Which thesis fields to search.
            match: `EXACT` matches as written, `INCLUDES` matches substrings.

        Returns:
            Matching theses.
        """
        response = self.client.http_client.post(
            SEARCH,
            data={
                "keyword": term1,
                "keyword1": term2 or "",
                "keyword2": term3 or "",
                "ops_field": coerce(AdvancedOperator, op1),
                "ops_field1": coerce(AdvancedOperator, op2),
                "nevi": str(coerce(SearchField, field)),
                "tip": str(coerce(MatchType, match)),
                "islem": "4",
                "-find": "  Bul",
            },
        )

        return parse_search_page(response.text)

    def detail(
        self,
        *,
        university: University | str | None = None,
        institute: Institute | int | None = None,
        division: Division | int | None = None,
        subject: Subject | str | None = None,
        degree_type: ThesisType | str | int = ThesisType.ALL,
        year_min: int | None = None,
        year_max: int | None = None,
        access: AccessType | str | int = AccessType.ALL,
        status: ThesisStatus | str | int = ThesisStatus.APPROVED,
        title: str | None = None,
        language: ThesisLanguage | str | int = ThesisLanguage.ALL,
        author: str | None = None,
        supervisor: str | None = None,
        keyword: str | None = None,
        thesis_display_no: int | None = None,
    ) -> SearchResults:
        """Run a detailed multi-filter search.

        Args:
            university: A `University`, a YOKSIS ID string, or `None` to omit.
            institute: An `Institute`, a raw numeric wire ID, or `None` to omit.
            division: A `Division`, a raw numeric wire ID, or `None` to omit.
            subject: A `Subject`, a free-text subject string, or `None` to omit.
            degree_type: Degree-level filter.
            year_min: Lower bound on defense year (inclusive). Must be `>= 1900`.
            year_max: Upper bound on defense year (inclusive).
            access: Full-text access status filter.
            status: Lifecycle status filter. Defaults to `APPROVED`.
            title: Title substring filter.
            language: Language filter.
            author: Author-name substring filter.
            supervisor: Supervisor-name substring filter.
            keyword: Keyword filter.
            thesis_display_no: Human-readable thesis number (the value YOK NTC shows
                next to `Tez No:`).

        Returns:
            Matching theses.

        Raises:
            ValueError: `year_min` is set and below `1900`, or `year_min` exceeds
                `year_max` when both are set.
        """
        if year_min is not None and year_min < _MIN_YEAR:
            msg = f"year_min must be >= {_MIN_YEAR}; got {year_min}"
            raise ValueError(msg)
        if year_min is not None and year_max is not None and year_min > year_max:
            msg = f"year_min ({year_min}) must be <= year_max ({year_max})"
            raise ValueError(msg)

        # Three input shapes per hierarchical filter: typed model (carries display +
        # numeric id + yoksis id), bare id (display unknown -- send empty string), or
        # None (filter omitted -- wire expects empty strings or "0").
        if isinstance(university, University):
            uniad = university.display_name
            universite = university.id
            uni_yoksis = resolve_yoksis_id(university)
            source = coerce(UniversitySource, university.source)
        elif university is not None:
            uniad = ""
            universite = ""
            uni_yoksis = resolve_yoksis_id(university)
            source = UniversitySource.TR.value
        else:
            uniad = ""
            universite = ""
            uni_yoksis = ""
            source = UniversitySource.TR.value

        if isinstance(institute, Institute):
            ensad = institute.display_name
            enstitu = str(institute.id)
        elif institute is not None:
            ensad = ""
            enstitu = str(institute)
        else:
            ensad = ""
            enstitu = "0"

        if isinstance(division, Division):
            abdad = division.display_name
            abd = str(division.id)
        elif division is not None:
            abdad = ""
            abd = str(division)
        else:
            abdad = ""
            abd = "0"

        konu = subject.display.raw if isinstance(subject, Subject) else (subject or "")

        # Wire field names are Turkish.
        response = self.client.http_client.post(
            SEARCH,
            data={
                "uniad": uniad,
                "Universite": universite,
                "uni_yoksis_id": uni_yoksis,
                "source": source,
                "ensad": ensad,
                "Enstitu": enstitu,
                "abdad": abdad,
                "ABD": abd,
                "Konu": konu,
                "Tur": str(coerce(ThesisType, degree_type)),
                "yil1": str(year_min) if year_min is not None else "0",
                "yil2": str(year_max) if year_max is not None else "0",
                "izin": str(coerce(AccessType, access)),
                "Durum": str(coerce(ThesisStatus, status)),
                "TezAd": title or "",
                "Dil": str(coerce(ThesisLanguage, language)),
                "AdSoyad": author or "",
                "DanismanAdSoyad": supervisor or "",
                "Dizin": keyword or "",
                "TezNo": str(thesis_display_no)
                if thesis_display_no is not None
                else "",
                "islem": "2",
                "-find": "  Bul",
            },
        )

        return parse_search_page(response.text)
