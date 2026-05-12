"""Search sub-package: `simple`, `advanced`, `detail`, and `recent` queries."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yoktez.client import Client

__all__ = ["SearchService"]


class SearchService:
    """`client.search` namespace."""

    def __init__(self, client: Client) -> None:
        self.client = client
