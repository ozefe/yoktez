"""Tests for `yoktez.search._parser.parse_search_page`.

Wire-shape fixtures cover the happy path; inline HTML literals cover the empty-results
and malformed-shape branches.
"""

from pathlib import Path

import pytest

from yoktez import ParseError, ThesisLanguage, ThesisType
from yoktez.search._parser import parse_search_page

FIXTURES = Path(__file__).parent / "fixtures" / "search"


def test_parses_a_full_page_of_results_from_search_simple_wire_shape():
    results = parse_search_page((FIXTURES / "results-many.html").read_text("utf-8"))

    assert len(results) == 10
    assert results.total == 66_816
    assert all(isinstance(t.degree_type, ThesisType) for t in results)
    assert all(isinstance(t.language, ThesisLanguage) for t in results)
    assert all(t.registration_no for t in results)


def test_parses_a_single_result_from_search_detail_wire_shape():
    results = parse_search_page((FIXTURES / "results-single.html").read_text("utf-8"))

    assert len(results) == 1
    assert results.total == 1


def test_empty_reference_data_yields_zero_results():
    html = (
        "<html><body>"
        "<div id='results-body'></div>"
        "<script>const referenceData = {};</script>"
        "</body></html>"
    )

    results = parse_search_page(html)
    assert len(results) == 0
    assert results.total == 0


def test_total_strips_turkish_thousand_separator():
    html = (
        "<html><body>"
        "<div class='warning-text'>Arama sonucunda  1.234.567 kayıt bulundu.</div>"
        "<div id='results-body'></div>"
        "<script>const referenceData = {};</script>"
        "</body></html>"
    )

    assert parse_search_page(html).total == 1_234_567


def test_total_defaults_to_zero_when_warning_block_absent():
    html = (
        "<html><body>"
        "<div id='results-body'></div>"
        "<script>const referenceData = {};</script>"
        "</body></html>"
    )

    assert parse_search_page(html).total == 0


def test_missing_reference_data_block_raises_parse_error():
    with pytest.raises(ParseError):
        parse_search_page("<html><body><div class='result-card'></div></body></html>")


def test_card_without_a_matching_reference_data_entry_raises_parse_error():
    html = (
        '<html><body><div class="result-card" data-index="0" '
        'data-kayitno="k" data-tezno="t"></div>'
        "<script>const referenceData = {};</script>"
        "</body></html>"
    )

    with pytest.raises(ParseError):
        parse_search_page(html)
