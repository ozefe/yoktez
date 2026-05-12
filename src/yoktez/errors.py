"""Exception hierarchy raised by `yoktez`."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime as dt

__all__ = [
    "ParseError",
    "ThesisNoPermitError",
    "ThesisPreparingError",
    "ThesisUnavailableError",
    "ThesisUnderEmbargoError",
    "YoktezError",
]


class YoktezError(Exception):
    """Base class for all `yoktez`-raised exceptions."""


class ParseError(YoktezError):
    """Raised when an expected HTML or JSON shape is absent.

    Indicates the upstream page layout changed materially and the parser can no longer
    locate the element it needs.
    """


class ThesisUnavailableError(YoktezError):
    """Raised when a thesis cannot be downloaded.

    Concrete subclasses (`ThesisUnderEmbargoError`, `ThesisNoPermitError`,
    `ThesisPreparingError`) narrow the cause.
    """

    def __init__(self, *, info_message: str) -> None:
        super().__init__(info_message)

        self.info_message = info_message


class ThesisUnderEmbargoError(ThesisUnavailableError):
    """Raised when a thesis is under author-requested embargo.

    The full text becomes accessible after `restricted_until`.
    """

    def __init__(self, *, info_message: str, restricted_until: dt.date) -> None:
        super().__init__(info_message=info_message)

        self.restricted_until = restricted_until


class ThesisNoPermitError(ThesisUnavailableError):
    """Raised when a thesis has no digital publishing permit from its author."""


class ThesisPreparingError(ThesisUnavailableError):
    """Raised when a thesis is still being prepared and not yet published."""
