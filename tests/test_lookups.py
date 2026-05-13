"""Tests for `yoktez.lookups.LookupsService`.

Targets the behavior the service adds on top of the parsers and the HTTP client:
memoization, input coercion, legacy-source rejection, multi-source composition,
domain-object wrapping, and filter-arg propagation. Fixtures only show up where an
integration check is the actual point; smaller inputs go inline.
"""

import httpx
import pytest

from yoktez import (
    Client,
    Institute,
    KeywordGroup,
    University,
    UniversitySource,
)


def _build_client(handler: httpx.MockTransport) -> Client:
    return Client(http_client=httpx.Client(transport=handler))


def test_results_are_cached_by_argument_tuple():
    hits = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        hits["count"] += 1
        return httpx.Response(200, json=[])

    with _build_client(httpx.MockTransport(handler)) as client:
        client.lookups.universities(UniversitySource.TR)
        client.lookups.universities("TR")  # coerces to the same cache key
        client.lookups.universities(UniversitySource.TR)

        assert hits["count"] == 1

        client.lookups.universities(UniversitySource.INT)

        assert hits["count"] == 2


def test_refresh_invalidates_the_cache():
    hits = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        hits["count"] += 1
        return httpx.Response(200, json=[])

    with _build_client(httpx.MockTransport(handler)) as client:
        client.lookups.universities()
        client.lookups.refresh()
        client.lookups.universities()

    assert hits["count"] == 2


def test_institutes_treats_university_object_and_yoksis_string_as_equivalent():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text='<input name="selected_institute" ad="A" kod="1" yoksisId="Y">'
        )

    uni = University(
        display_name="X",
        id="opaque",
        yoksis_id="YOK",
        source=UniversitySource.TR,
    )

    with _build_client(httpx.MockTransport(handler)) as client:
        from_obj = client.lookups.institutes(uni)
        from_str = client.lookups.institutes("YOK")

    assert from_obj == from_str


def test_institutes_rejects_university_without_yoksis_id():
    legacy = University(
        display_name="L",
        id="42",
        yoksis_id=None,
        source=UniversitySource.TR,
    )

    with (
        _build_client(httpx.MockTransport(lambda _r: httpx.Response(200))) as client,
        pytest.raises(ValueError, match="University"),
    ):
        client.lookups.institutes(legacy)


def test_divisions_rejects_institute_without_yoksis_id():
    legacy = Institute(display_name="L", id=1, yoksis_id=None)

    with (
        _build_client(httpx.MockTransport(lambda _r: httpx.Response(200))) as client,
        pytest.raises(ValueError, match="Institute"),
    ):
        client.lookups.divisions("U", legacy)


def test_all_universities_composes_results_from_both_modern_sources():
    def handler(request: httpx.Request) -> httpx.Response:
        source = request.url.params["type"]
        return httpx.Response(
            200,
            json=[{"kod": source, "displayName": f"UNI_{source}", "yoksisId": "y"}],
        )

    with _build_client(httpx.MockTransport(handler)) as client:
        names = {u.display_name for u in client.lookups.all_universities()}

    assert names == {"UNI_TR", "UNI_INT"}


def test_universities_threads_the_requested_source_onto_every_record():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{"kod": "k", "displayName": "D", "yoksisId": "y"}],
        )

    with _build_client(httpx.MockTransport(handler)) as client:
        tr_results = client.lookups.universities(UniversitySource.TR)
        int_results = client.lookups.universities(UniversitySource.INT)

    assert all(u.source is UniversitySource.TR for u in tr_results)
    assert all(u.source is UniversitySource.INT for u in int_results)


def test_all_subjects_wraps_each_name_in_bilingual():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<a href=\"javascript:eklecikar('TR_term = EN_term','1','0')\">",
        )

    with _build_client(httpx.MockTransport(handler)) as client:
        [subject] = client.lookups.all_subjects()

    assert subject.display.tr == "TR_term"
    assert subject.display.en == "EN_term"


def test_keywords_propagates_filter_group_into_every_returned_record():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=(
                "<a href=\"javascript:eklecikar('X = Y','1','0')\">"
                "<a href=\"javascript:eklecikar('A = B','2','0')\">"
            ),
        )

    with _build_client(httpx.MockTransport(handler)) as client:
        scoped = client.lookups.keywords(group=KeywordGroup.SCIENCE)
        unscoped = client.lookups.keywords()

    assert all(k.group is KeywordGroup.SCIENCE for k in scoped)
    assert all(k.group is None for k in unscoped)
