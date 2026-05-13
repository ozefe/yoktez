"""Pure HTML parser for the YOK NTC thesis-assets response body."""

import datetime as dt
import re

from yoktez.assets.models import ThesisAssets
from yoktez.enums import AssetStatus
from yoktez.errors import ParseError

__all__ = ["parse_thesis_assets"]

# Key values stop at a quote (`'` or `"`) or whitespace. YOK NTC has been observed
# emitting a trailing space before the closing quote on the appendix anchor; capping at
# whitespace strips it cleanly.
_PDF_KEY = re.compile(r"""TezGoster\?key=([^'"\s]+)""")
_APPENDIX_KEY = re.compile(r"""EkGoster\?key=([^'"\s]+)""")

_INFO_MSG = re.compile(r"""<span class=['"]pdf-info-msg['"]>(.*?)</span>""", re.DOTALL)
_EMBARGO_DATE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b")

# Preparing-state container: no nested HTML, just prose.
_PREPARING_CONTAINER = re.compile(r"""<div class=['"]pdf-container['"]>([^<]+)</div>""")

_DATE_FORMAT = "%d.%m.%Y"


def parse_thesis_assets(html: str) -> ThesisAssets:
    """Classify a YOK NTC assets response into a `ThesisAssets`.

    Args:
        html: Raw HTML body returned by the assets endpoint.

    Returns:
        A `ThesisAssets` populated according to the wire state. `pdf_key` and
        `appendix_key` are populated only for `AVAILABLE`; `restricted_until` only for
        `UNDER_EMBARGO`; `info_message` for every non-`AVAILABLE` state.

    Raises:
        ParseError: The fragment matches none of the known shapes. Indicates the
            upstream layout changed materially.
    """
    pdf_match = _PDF_KEY.search(html)
    if pdf_match is not None:
        appendix_match = _APPENDIX_KEY.search(html)

        return ThesisAssets(
            status=AssetStatus.AVAILABLE,
            pdf_key=pdf_match.group(1),
            appendix_key=appendix_match.group(1) if appendix_match else None,
            restricted_until=None,
            info_message=None,
        )

    info_match = _INFO_MSG.search(html)
    if info_match is not None:
        info_message = info_match.group(1).strip()

        date_match = _EMBARGO_DATE.search(info_message)
        if date_match is not None:
            return ThesisAssets(
                status=AssetStatus.UNDER_EMBARGO,
                pdf_key=None,
                appendix_key=None,
                restricted_until=dt.datetime.strptime(date_match.group(1), _DATE_FORMAT)
                .replace(tzinfo=dt.UTC)
                .date(),
                info_message=info_message,
            )

        return ThesisAssets(
            status=AssetStatus.NO_PERMIT,
            pdf_key=None,
            appendix_key=None,
            restricted_until=None,
            info_message=info_message,
        )

    preparing_match = _PREPARING_CONTAINER.search(html)
    if preparing_match is not None:
        return ThesisAssets(
            status=AssetStatus.PREPARING,
            pdf_key=None,
            appendix_key=None,
            restricted_until=None,
            info_message=preparing_match.group(1).strip(),
        )

    msg = "Could not classify pdf-container shape"
    raise ParseError(msg)
