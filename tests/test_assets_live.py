"""Opt-in live-network smoke test for `AssetsService`.

Run with `pytest -m live` to hit the real YOK NTC endpoint. Default `pytest` runs skip
this. Proves the wire shape hasn't drifted and that PDF streaming yields actual PDF
bytes; not an exhaustive feature test.
"""

import io

import pytest

from yoktez import AssetStatus, Client

# The SAKARYA-AMASRA-CİDE thesis (MERT AVCI, both PDF and appendix available) is the
# example for the PDFAndAppendix case. Stable enough for a smoke test.
_SAKARYA_KEYS = ("_94imcmQscBkqdlIo-G3tw", "_94imcmQscBkqdlIo-G3tw")


@pytest.mark.live
def test_assets_get_against_real_yok_ntc():
    with Client() as client:
        assets = client.assets.get(_SAKARYA_KEYS)

    assert assets.status is AssetStatus.AVAILABLE
    assert assets.pdf_key


@pytest.mark.live
def test_download_pdf_streams_real_pdf():
    buf = io.BytesIO()
    with Client() as client:
        assets = client.assets.get(_SAKARYA_KEYS)

        assert assets.pdf_key is not None

        client.assets.download_pdf(assets.pdf_key, buf)

    assert buf.getvalue().startswith(b"%PDF-")
