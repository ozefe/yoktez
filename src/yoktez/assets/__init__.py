"""Assets sub-package: download-key fetch + PDF/appendix streaming."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yoktez.client import Client

__all__ = ["AssetsService"]


class AssetsService:
    """`client.assets` namespace."""

    def __init__(self, client: Client) -> None:
        self.client = client
