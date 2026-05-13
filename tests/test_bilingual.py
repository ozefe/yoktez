"""Tests for `yoktez.bilingual`."""

import pytest

from yoktez.bilingual import Bilingual


@pytest.mark.parametrize(
    ("raw", "expected_tr", "expected_en"),
    [
        ("Türkçe = Turkish", "Türkçe", "Turkish"),
        ("Türkçe", "Türkçe", None),
        ("a = b = c", "a", "b = c"),
        ("  Türkçe   =   Turkish  ", "Türkçe", "Turkish"),
        ("", "", None),
        (" = ", "", ""),
    ],
)
def test_parse(raw: str, expected_tr: str, expected_en: str | None):
    result = Bilingual.parse(raw)

    assert result == Bilingual(raw=raw, tr=expected_tr, en=expected_en)
