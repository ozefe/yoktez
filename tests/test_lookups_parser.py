"""Tests for `yoktez.lookups._parser`.

Each parser is a pure text -> primitives function, so tests work on small inline inputs
that exercise one logical branch at a time. Fixtures stay out of the parser test
surface; the service tests exercise integration end-to-end.
"""

from yoktez.lookups._parser import (
    parse_eklecikar_list,
    parse_radio_input_list,
    parse_universities_json,
)
from yoktez.lookups.models import University


def test_universities_json_maps_kod_displayname_yoksisid_into_record_fields():
    parsed = parse_universities_json(
        [{"kod": "abc", "displayName": "X", "yoksisId": "y"}]
    )

    assert parsed == [University(display_name="X", id="abc", yoksis_id="y")]


def test_radio_input_list_returns_none_when_yoksis_attribute_is_missing():
    # The divisions endpoint never carries `yoksisId` on its `<input>` tags.
    parsed = parse_radio_input_list('<input name="x" ad="A" kod="1">', name_attr="x")

    assert parsed == [("A", 1, None)]


def test_radio_input_list_coerces_literal_null_yoksis_to_none():
    # The bulk endpoint encodes legacy entries' yoksisId as the literal string "null"
    # instead of omitting the attribute. Both shapes must surface as Python `None`.
    parsed = parse_radio_input_list(
        '<input name="x" ad="A" kod="1" yoksisId="null">', name_attr="x"
    )

    assert parsed == [("A", 1, None)]


def test_eklecikar_parses_bare_and_entity_encoded_quotes_to_the_same_pair():
    bare = parse_eklecikar_list("<a href=\"javascript:eklecikar('NAME','5','0')\">")
    encoded = parse_eklecikar_list(
        '<a href="javascript:eklecikar(&#39;NAME&#39;,&#39;5&#39;,&#39;0&#39;)">'
    )

    assert bare == encoded == [("NAME", 5)]


def test_eklecikar_unescapes_apostrophes_embedded_in_names():
    # JS-escapes apostrophes inside the name as `\'`; after HTML encoding that is
    # `\&#39;`. The parser must reverse both layers so callers see plain `'`.
    parsed = parse_eklecikar_list(
        '<a href="javascript:eklecikar(&#39;O\\&#39;Brien&#39;,'
        '&#39;1&#39;,&#39;0&#39;)">'
    )

    assert parsed == [("O'Brien", 1)]
