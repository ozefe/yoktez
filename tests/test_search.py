"""Tests for `yoktez.search.SearchService`."""

from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from yoktez import (
    Bilingual,
    Client,
    Division,
    Institute,
    Subject,
    University,
    UniversitySource,
)

FIXTURES = Path(__file__).parent / "fixtures" / "search"
_RESULTS_MANY = (FIXTURES / "results-many.html").read_text("utf-8")


def _build_client(handler: httpx.MockTransport) -> Client:
    return Client(http_client=httpx.Client(transport=handler))


def test_detail_threads_typed_models_into_their_wire_fields():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, text=_RESULTS_MANY)

    university = University(
        display_name="ISTANBUL",
        id="89FAOtbmCQNX2DUa5DInLA",
        yoksis_id="ZDJv5lAIQDOnVGpRdJBQxA",
        source=UniversitySource.TR,
    )
    institute = Institute(
        display_name="SOSYAL",
        id=95,
        yoksis_id="rBc2QrJviXLMztDguO97ZA",
    )
    division = Division(display_name="SINEMA", id=2502)
    subject = Subject(display=Bilingual.parse("Alman = German"), id=1)

    with _build_client(httpx.MockTransport(handler)) as client:
        client.search.detail(
            university=university,
            institute=institute,
            division=division,
            subject=subject,
        )

    body = parse_qs(captured[0].content.decode(), keep_blank_values=True)
    assert body["uniad"] == ["ISTANBUL"]
    assert body["Universite"] == ["89FAOtbmCQNX2DUa5DInLA"]
    assert body["uni_yoksis_id"] == ["ZDJv5lAIQDOnVGpRdJBQxA"]
    assert body["source"] == ["TR"]
    assert body["ensad"] == ["SOSYAL"]
    assert body["Enstitu"] == ["95"]
    assert body["abdad"] == ["SINEMA"]
    assert body["ABD"] == ["2502"]
    assert body["Konu"] == ["Alman = German"]


def test_detail_defaults_emit_empty_strings_and_zero_year_bounds():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, text=_RESULTS_MANY)

    with _build_client(httpx.MockTransport(handler)) as client:
        client.search.detail()

    body = parse_qs(captured[0].content.decode(), keep_blank_values=True)
    assert body["uniad"] == [""]
    assert body["uni_yoksis_id"] == [""]
    assert body["source"] == ["TR"]
    assert body["Enstitu"] == ["0"]
    assert body["ABD"] == ["0"]
    assert body["yil1"] == ["0"]
    assert body["yil2"] == ["0"]


def test_detail_accepts_raw_int_for_institute_and_division():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, text=_RESULTS_MANY)

    with _build_client(httpx.MockTransport(handler)) as client:
        client.search.detail(institute=95, division=2502)

    body = parse_qs(captured[0].content.decode(), keep_blank_values=True)
    assert body["ensad"] == [""]
    assert body["Enstitu"] == ["95"]
    assert body["abdad"] == [""]
    assert body["ABD"] == ["2502"]


def test_detail_rejects_year_min_below_1900():
    with (
        _build_client(
            httpx.MockTransport(lambda _r: httpx.Response(200, text=_RESULTS_MANY))
        ) as client,
        pytest.raises(ValueError, match="1900"),
    ):
        client.search.detail(year_min=1899)


def test_detail_rejects_year_min_greater_than_year_max():
    with (
        _build_client(
            httpx.MockTransport(lambda _r: httpx.Response(200, text=_RESULTS_MANY))
        ) as client,
        pytest.raises(ValueError, match=r"year_min .* must be <= year_max"),
    ):
        client.search.detail(year_min=2024, year_max=2020)
