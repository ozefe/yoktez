"""Tests for `yoktez.errors`."""

import datetime as dt

from yoktez.errors import ThesisUnavailableError, ThesisUnderEmbargoError


def test_unavailable_stores_info_message():
    err = ThesisUnavailableError(info_message="no permit")

    assert err.info_message == "no permit"


def test_under_embargo_stores_info_message_and_date():
    until = dt.date(2026, 4, 27)
    err = ThesisUnderEmbargoError(info_message="embargo", restricted_until=until)

    assert err.info_message == "embargo"
    assert err.restricted_until == until
