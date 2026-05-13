"""Cross-package helpers shared by sub-services."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yoktez.lookups.models import Institute, University

__all__ = ["resolve_yoksis_id"]


def resolve_yoksis_id(obj: University | Institute | str) -> str:
    """Resolve `obj` to a YOKSIS ID string usable as a `uniKod`/`ensKod` query value.

    Strings pass through unchanged. Model instances must carry a non-`None` `yoksis_id`
    because we can only drive hierarchical lookups via `yoksis_id`. The call raises
    `ValueError` rather than silently issuing a malformed request.
    """
    if isinstance(obj, str):
        return obj

    if obj.yoksis_id is None:
        msg = (
            f"{obj!r} has yoksis_id=None; need non-None value to drive hierarchical "
            "lookups"
        )
        raise ValueError(msg)

    return obj.yoksis_id
