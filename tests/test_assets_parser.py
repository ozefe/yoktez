"""Tests for `yoktez.assets._parser.parse_thesis_assets`."""

import datetime as dt
from pathlib import Path

import pytest

from yoktez import AssetStatus
from yoktez.assets._parser import parse_thesis_assets

FIXTURES = Path(__file__).parent / "fixtures" / "assets"

_EMBARGO_DATE = dt.date(2026, 9, 27)

_PDF_KEY = "zD1B0cW7zVr3VcnZjitVXtAqtgkKvvqMutQwIUIXmM-g0PV2p_ZOJcXBD-iLlvX_"
_PDF_AND_APPENDIX_PDF_KEY = (
    "WY5CM7tPNE2z_YM6pBu0t17r1jeShVIPVejCmJ7iKpjK5XHS7yAAxPZoZy1-5U3H"
)
_PDF_AND_APPENDIX_APPENDIX_KEY = (
    "6ZtRe5rnHrr74rjfYBQv_rPw-OvOQh0usVuMN7yxxEv_3iKZyZCxwGSp2Uij4be3"
)


@pytest.mark.parametrize(
    (
        "fixture",
        "expected_status",
        "expected_pdf_key",
        "expected_appendix_key",
        "expected_restricted_until",
        "expects_info_message",
    ),
    [
        ("pdf.html", AssetStatus.AVAILABLE, _PDF_KEY, None, None, False),
        (
            "pdf-and-appendix.html",
            AssetStatus.AVAILABLE,
            _PDF_AND_APPENDIX_PDF_KEY,
            _PDF_AND_APPENDIX_APPENDIX_KEY,
            None,
            False,
        ),
        # EN-variant fixtures intentionally omitted: the classifier regex doesn't read
        # message language, so the EN fixtures duplicate the TR coverage.
        (
            "under-embargo-tr.html",
            AssetStatus.UNDER_EMBARGO,
            None,
            None,
            _EMBARGO_DATE,
            True,
        ),
        ("no-permit-tr.html", AssetStatus.NO_PERMIT, None, None, None, True),
        ("preparing-tr.html", AssetStatus.PREPARING, None, None, None, True),
    ],
)
def test_parse_thesis_assets_classifies_every_wire_state(  # noqa: PLR0913
    fixture: str,
    expected_status: AssetStatus,
    expected_pdf_key: str | None,
    expected_appendix_key: str | None,
    expected_restricted_until: dt.date | None,
    expects_info_message: bool,
):
    html = (FIXTURES / fixture).read_text("utf-8")

    assets = parse_thesis_assets(html)

    assert assets.status is expected_status
    assert assets.pdf_key == expected_pdf_key
    assert assets.appendix_key == expected_appendix_key
    assert assets.restricted_until == expected_restricted_until
    assert bool(assets.info_message) is expects_info_message
