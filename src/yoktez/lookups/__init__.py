"""Lookups sub-package: universities, institutes, divisions, subjects, keywords."""

from typing import TYPE_CHECKING, cast

from yoktez._endpoints import (
    ALL_DEPARTMENTS,
    ALL_SECTIONS,
    ALL_SUBJECTS,
    KEYWORDS_SEARCH,
    TARAMA_AJAX,
    UNIVERSITIES,
)
from yoktez._helpers import resolve_yoksis_id
from yoktez.bilingual import Bilingual
from yoktez.enums import KeywordGroup, KeywordLanguage, UniversitySource, coerce
from yoktez.lookups._parser import (
    parse_eklecikar_list,
    parse_radio_input_list,
    parse_universities_json,
)
from yoktez.lookups.models import (
    Department,
    Division,
    Institute,
    Keyword,
    Section,
    Subject,
    University,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from yoktez.client import Client

__all__ = [
    "Department",
    "Division",
    "Institute",
    "Keyword",
    "LookupsService",
    "Section",
    "Subject",
    "University",
]


class LookupsService:
    """`client.lookups` namespace.

    Holds a per-instance memoization cache keyed by `(method_name, *normalized_args)`,
    where every arg is reduced to a primitive (`str` for YOKSIS IDs, `StrEnum.value`,
    `IntEnum.value`, `None`). One cache per `Client`; no locks -- one Client per thread
    for concurrent callers.
    """

    def __init__(self, client: Client) -> None:
        self.client = client
        self._cache: dict[tuple[object, ...], object] = {}

    def universities(
        self, source: UniversitySource | str = UniversitySource.TR
    ) -> list[University]:
        """Fetch every university tracked by YOK NTC, scoped by `source`.

        `source` may be a `UniversitySource` member, its wire string (`"TR"`, `"INT"`),
        or its member name. Result is memoized per source value. Each returned record
        carries the resolved `UniversitySource` so callers can issue correctly-scoped
        detail searches without re-querying.
        """
        source_value = coerce(UniversitySource, source)
        source_member = UniversitySource(source_value)

        return self._memoize(
            ("universities", source_value),
            lambda: parse_universities_json(
                self.client.http_client.get(
                    UNIVERSITIES, params={"type": source_value}
                ).json(),
                source=source_member,
            ),
        )

    def institutes(self, university: University | str) -> list[Institute]:
        """Fetch every institute that belongs to `university`.

        `university` is either a `University` (must carry a non-`None` `yoksis_id`) or a
        YOKSIS ID string. Result is memoized per university YOKSIS ID.

        Raises:
            ValueError: `university` is a `University` whose `yoksis_id` is `None`
                (legacy-source records cannot drive hierarchical lookups).
        """
        university_id = resolve_yoksis_id(university)

        return self._memoize(
            ("institutes", university_id),
            lambda: [
                Institute(display_name=ad, id=kod, yoksis_id=yoksis)
                for ad, kod, yoksis in parse_radio_input_list(
                    self.client.http_client.get(
                        TARAMA_AJAX,
                        params={"ajax": "getEnstitu", "uniKod": university_id},
                    ).text,
                    name_attr="selected_institute",
                )
            ],
        )

    def divisions(
        self, university: University | str, institute: Institute | str
    ) -> list[Division]:
        """Fetch every division under `institute` of `university`.

        Both arguments accept a model instance (with a non-`None` `yoksis_id`) or a
        YOKSIS ID string. Result is memoized on the (university, institute) pair.

        Raises:
            ValueError: either argument is a model whose `yoksis_id` is `None`.
        """
        university_id = resolve_yoksis_id(university)
        institute_id = resolve_yoksis_id(institute)

        return self._memoize(
            ("divisions", university_id, institute_id),
            lambda: [
                Division(display_name=ad, id=kod)
                for ad, kod, _ in parse_radio_input_list(
                    self.client.http_client.get(
                        TARAMA_AJAX,
                        params={
                            "ajax": "getABD",
                            "uniKod": university_id,
                            "ensKod": institute_id,
                        },
                    ).text,
                    name_attr="selected_abd",
                )
            ],
        )

    def all_universities(self) -> list[University]:
        """Fetch every university YOK NTC knows, Turkish and international combined.

        Composed from two `universities()` calls (`TR` and `INT`); the legacy endpoint
        exposes only stringified numeric IDs and no YOKSIS IDs, which makes it useless
        for driving hierarchical lookups. Inner calls are memoized, so this composition
        is effectively free after the first run.
        """
        return self._memoize(
            ("all_universities",),
            lambda: [
                *self.universities(UniversitySource.TR),
                *self.universities(UniversitySource.INT),
            ],
        )

    def all_institutes(self) -> list[Institute]:
        """Fetch every institute YOK NTC knows, from the modern bulk endpoint.

        Entries whose source endpoint had no YOKSIS ID surface here with
        `yoksis_id=None` (the wire encodes them as the literal string `"null"`).
        """
        return self._memoize(
            ("all_institutes",),
            lambda: [
                Institute(display_name=ad, id=kod, yoksis_id=yoksis)
                for ad, kod, yoksis in parse_radio_input_list(
                    self.client.http_client.get(
                        TARAMA_AJAX, params={"ajax": "getAllEnstitu"}
                    ).text,
                    name_attr="selected_institute",
                )
            ],
        )

    def all_divisions(self) -> list[Division]:
        """Fetch every division YOK NTC knows, from the modern bulk endpoint."""
        return self._memoize(
            ("all_divisions",),
            lambda: [
                Division(display_name=ad, id=kod)
                for ad, kod, _ in parse_radio_input_list(
                    self.client.http_client.get(
                        TARAMA_AJAX, params={"ajax": "getAllABD"}
                    ).text,
                    name_attr="selected_abd",
                )
            ],
        )

    def all_subjects(self) -> list[Subject]:
        """Fetch every subject classifier YOK NTC knows.

        Each subject's display name is bilingual (`Turkish = English`) and is wrapped in
        `Bilingual` so callers can pick the half they need without re-parsing the raw
        string.
        """
        return self._memoize(
            ("all_subjects",),
            lambda: [
                Subject(display=Bilingual.parse(name), id=numeric_id)
                for name, numeric_id in parse_eklecikar_list(
                    self.client.http_client.get(ALL_SUBJECTS).text
                )
            ],
        )

    def all_departments(self) -> list[Department]:
        """Fetch every department YOK NTC knows."""
        return self._memoize(
            ("all_departments",),
            lambda: [
                Department(display_name=name, id=numeric_id)
                for name, numeric_id in parse_eklecikar_list(
                    self.client.http_client.get(ALL_DEPARTMENTS).text
                )
            ],
        )

    def all_sections(self) -> list[Section]:
        """Fetch every section YOK NTC knows."""
        return self._memoize(
            ("all_sections",),
            lambda: [
                Section(display_name=name, id=numeric_id)
                for name, numeric_id in parse_eklecikar_list(
                    self.client.http_client.get(ALL_SECTIONS).text
                )
            ],
        )

    def keywords(
        self,
        *,
        group: KeywordGroup | str | None = None,
        language: KeywordLanguage | str | int = KeywordLanguage.ALL,
        first_letter: str | None = None,
        search: str | None = None,
    ) -> list[Keyword]:
        """Fetch keywords from modern endpoint, optionally filtered.

        Each filter argument is optional; the wire defaults are an empty string for
        `grup` / `ilkHarf` / `aranan` and `0` (`ALL`) for `dil`. The returned records
        carry the filter `group` (if any) so callers can attribute results back to their
        academical group without re-querying. Memoized on the full filter tuple.
        """
        if group is None:
            group_wire = ""
            group_member = None
        else:
            group_wire = coerce(KeywordGroup, group)
            group_member = KeywordGroup(group_wire)

        language_value = coerce(KeywordLanguage, language)
        first_letter_value = first_letter or ""
        search_value = search or ""

        return self._memoize(
            (
                "keywords",
                group_wire,
                language_value,
                first_letter_value,
                search_value,
            ),
            lambda: [
                Keyword(
                    display=Bilingual.parse(name), id=keyword_id, group=group_member
                )
                for name, keyword_id in parse_eklecikar_list(
                    self.client.http_client.post(
                        KEYWORDS_SEARCH,
                        data={
                            "grup": group_wire,
                            "ilkHarf": first_letter_value,
                            "dil": str(language_value),
                            "aranan": search_value,
                            "tip2": "2",
                            "islem": "1",
                        },
                    ).text
                )
            ],
        )

    def all_keywords(self) -> list[Keyword]:
        """Fetch every keyword YOK NTC knows.

        Thin wrapper around `keywords()` with no filters applied. The underlying
        single-filter cache means repeated calls share storage with an equivalent
        `keywords()` call.
        """
        return self.keywords()

    def refresh(self) -> None:
        """Clear the entire per-instance lookup cache.

        The cache has no TTL and is single-threaded (one Client per thread). Call this
        when YOKSIS IDs are suspected to have rotated or when a long-lived Client should
        re-fetch on the next call.
        """
        self._cache.clear()

    def _memoize[T](self, key: tuple[object, ...], fetch: Callable[[], T]) -> T:
        """Return the cached value for `key`, fetching once and storing on miss.

        The cache stores `object` internally so all methods share one dict; the return
        is cast back to the fetch callable's declared type. This keeps the cache
        one-line at every call site without leaking generics into the dict.
        """
        if key not in self._cache:
            self._cache[key] = fetch()

        return cast("T", self._cache[key])
