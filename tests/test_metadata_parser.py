"""Tests for `yoktez.metadata._parser.parse_thesis_metadata`."""

import json
from pathlib import Path

from yoktez.metadata._parser import parse_thesis_metadata

FIXTURES = Path(__file__).parent / "fixtures" / "metadata"
_RESULT = json.loads((FIXTURES / "result.json").read_text("utf-8"))


def test_keywords_strip_the_strong_label_prefix_before_splitting():
    metadata = parse_thesis_metadata(_RESULT)

    assert metadata.keywords is not None
    assert all("<strong>" not in kw.raw for kw in metadata.keywords)
    assert all("Anahtar Kelime" not in kw.tr for kw in metadata.keywords)


def test_supervisor_strips_strong_label_prefix():
    metadata = parse_thesis_metadata(_RESULT)

    assert metadata.supervisor is not None
    assert "<strong>" not in metadata.supervisor
    assert not metadata.supervisor.startswith("Danışman")


def test_missing_danisman_yields_supervisor_none():
    data = {**_RESULT}
    del data["danisman"]

    metadata = parse_thesis_metadata(data)
    assert metadata.supervisor is None


def test_missing_yer_yields_affiliation_none():
    data = {**_RESULT, "yer": ""}

    metadata = parse_thesis_metadata(data)
    assert metadata.affiliation is None


def test_all_empty_references_yield_references_none():
    data = {
        **_RESULT,
        "apa_ref": "",
        "ieee_ref": "",
        "mla_ref": "",
        "chicago_ref": "",
        "harvard_ref": "",
    }

    metadata = parse_thesis_metadata(data)
    assert metadata.references is None


def test_missing_keywords_yields_keywords_none():
    data = {**_RESULT}
    del data["anahtarKelimeTr"]

    metadata = parse_thesis_metadata(data)
    assert metadata.keywords is None


def test_missing_abstracts_yield_none():
    data = {**_RESULT, "trOzet": "", "enOzet": ""}

    metadata = parse_thesis_metadata(data)
    assert metadata.abstract_tr is None
    assert metadata.abstract_other is None


def test_partial_references_drop_only_missing_fields_to_empty_string():
    data = {
        **_RESULT,
        "ieee_ref": "",
        "mla_ref": "",
        "chicago_ref": "",
        "harvard_ref": "",
    }

    metadata = parse_thesis_metadata(data)
    assert metadata.references is not None
    assert metadata.references.apa
    assert metadata.references.ieee == ""
