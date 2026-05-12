"""Tests for `coerce` in `yoktez.enums`.

The enum members themselves are not tested: they are data, and asserting their values
would only re-state the source in a second file. The real branching logic is in
`coerce`.
"""

import pytest

from yoktez.enums import (
    AdvancedOperator,
    KeywordGroup,
    ThesisStatus,
    ThesisType,
    coerce,
)

# IntEnum coverage
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=


def test_coerce_intenum_accepts_enum_int_and_member_name():
    assert coerce(ThesisType, ThesisType.MASTER) == 1
    assert coerce(ThesisType, 1) == 1
    assert coerce(ThesisType, "MASTER") == 1
    assert coerce(ThesisType, "1") == 1


def test_coerce_intenum_passes_unknown_int_through():
    # YOK NTC may introduce new codes; tolerate them.
    assert coerce(ThesisStatus, 99) == 99


def test_coerce_intenum_rejects_unknown_string():
    with pytest.raises(ValueError, match="BOGUS"):
        coerce(ThesisType, "BOGUS")


def test_coerce_intenum_rejects_wrong_python_type():
    with pytest.raises(TypeError):
        coerce(ThesisType, 1.5)  # pyright: ignore[reportArgumentType, reportCallIssue]


# StrEnum coverage
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=


def test_coerce_strenum_accepts_enum_name_and_value():
    assert coerce(KeywordGroup, KeywordGroup.SCIENCE) == "F"
    assert coerce(KeywordGroup, "SCIENCE") == "F"
    assert coerce(KeywordGroup, "F") == "F"


def test_coerce_strenum_rejects_unknown_string():
    # Typos in small string-valued enums must fail loudly; no passthrough.
    with pytest.raises(ValueError, match="bogus"):
        coerce(KeywordGroup, "bogus")


def test_coerce_advanced_operator_round_trips_both_forms():
    assert coerce(AdvancedOperator, "AND") == "and"
    assert coerce(AdvancedOperator, "and") == "and"
    assert coerce(AdvancedOperator, AdvancedOperator.OR) == "or"
