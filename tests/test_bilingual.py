"""Tests for `yoktez.bilingual`."""

from yoktez.bilingual import Bilingual


def test_parse_with_separator():
    result = Bilingual.parse("Türkçe = Turkish")

    assert result == Bilingual(raw="Türkçe = Turkish", tr="Türkçe", en="Turkish")


def test_parse_without_separator_leaves_en_none():
    result = Bilingual.parse("Türkçe")

    assert result == Bilingual(raw="Türkçe", tr="Türkçe", en=None)


def test_parse_splits_on_first_separator_only():
    result = Bilingual.parse("a = b = c")

    assert result == Bilingual(raw="a = b = c", tr="a", en="b = c")


def test_parse_strips_inner_whitespace_but_preserves_raw():
    raw = "  Türkçe   =   Turkish  "
    result = Bilingual.parse(raw)

    assert result.raw == raw
    assert result.tr == "Türkçe"
    assert result.en == "Turkish"


def test_parse_empty_string():
    assert Bilingual.parse("") == Bilingual(raw="", tr="", en=None)


def test_parse_separator_only():
    assert Bilingual.parse(" = ") == Bilingual(raw=" = ", tr="", en="")
