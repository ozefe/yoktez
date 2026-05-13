"""Cross-package helpers shared by sub-services."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yoktez.lookups.models import Institute, University

__all__ = ["resolve_yoksis_id"]


def resolve_yoksis_id(obj: University | Institute | str) -> str:
    """Resolve `obj` to a YOKSIS ID string usable as a `uniKod`/`ensKod` query value.

    Args:
        obj: A `University`, `Institute`, or a raw YOKSIS ID string. Strings pass
            through unchanged.

    Returns:
        The YOKSIS ID string.

    Raises:
        ValueError: `obj` is a model whose `yoksis_id` is `None`. Hierarchical lookups
            require a non-`None` value; failing here keeps malformed requests off the
            wire.
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
