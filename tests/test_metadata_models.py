"""Tests for `yoktez.metadata.models`."""

import pytest

from yoktez import Affiliation


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "MARMARA / TÜRKİYAT / TÜRK DİLİ / Türk Dili Bilim Dalı",
            ("MARMARA", "TÜRKİYAT", "TÜRK DİLİ", "Türk Dili Bilim Dalı"),
        ),
        ("U / I / D", ("U", "I", "D", None)),
        ("U / I", ("U", "I", None, None)),
        ("Just A University", ("Just A University", None, None, None)),
        ("", ("", None, None, None)),
        ("U / I /", ("U", "I", None, None)),
        ("U / I / D / S1 / S2", ("U", "I", "D", "S1 / S2")),
    ],
)
def test_parse(raw: str, expected: tuple[str, str | None, str | None, str | None]):
    result = Affiliation.parse(raw)

    assert (
        result.university,
        result.institute,
        result.division,
        result.section,
    ) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "U / I / D / S",
        "U / I / D",
        "U / I",
        "Only",
        "",
        "U / I /",
        "U / I / D / S1 / S2",
    ],
)
def test_parse_preserves_raw_verbatim(raw: str):
    assert Affiliation.parse(raw).raw == raw
