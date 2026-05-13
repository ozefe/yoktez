"""Opt-in live-network smoke tests for `SearchService`.

Run with `pytest -m live` to hit the real YOK NTC endpoints. Default `pytest` runs skip
these. They prove the wire shape hasn't drifted from what the parser expects; they don't
exhaustively cover feature behavior.
"""

import pytest

from yoktez import Client, ThesisType


@pytest.mark.live
def test_recent_returns_results():
    with Client() as client:
        results = client.search.recent()

    assert len(results) > 0
    assert results[0].registration_no


@pytest.mark.live
def test_simple_returns_results():
    with Client() as client:
        results = client.search.simple("bilgisayar")

    assert len(results) > 0
    assert results[0].registration_no


@pytest.mark.live
def test_advanced_returns_results():
    with Client() as client:
        results = client.search.advanced("yapay", term2="zeka")

    assert len(results) > 0
    assert results[0].registration_no


@pytest.mark.live
def test_detail_returns_results():
    with Client() as client:
        results = client.search.detail(
            degree_type=ThesisType.DOCTORATE,
            year_min=2020,
            year_max=2024,
        )

    assert len(results) > 0
    assert results[0].registration_no
