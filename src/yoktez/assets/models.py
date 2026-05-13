"""Value objects returned by `AssetsService`."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime as dt

    from yoktez.enums import AssetStatus

__all__ = ["ThesisAssets"]


@dataclass(frozen=True, slots=True)
class ThesisAssets:
    """Download-key bundle and access status for a single thesis.

    Attributes:
        status: Which of the wire states the thesis is in.
        pdf_key: Opaque download token for the full-text PDF; `None` unless `status` is
            `AVAILABLE`.
        appendix_key: Opaque download token for the optional appendix archive; `None`
            unless an appendix exists alongside the PDF.
        restricted_until: Embargo expiry date; populated only when `status` is
            `UNDER_EMBARGO`.
        info_message: User-facing reason text as surfaced by YOK NTC; populated for the
            non-`AVAILABLE` states and `None` otherwise.
    """

    status: AssetStatus
    pdf_key: str | None
    appendix_key: str | None
    restricted_until: dt.date | None
    info_message: str | None
