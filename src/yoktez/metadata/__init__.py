"""Metadata sub-package: per-thesis structured detail fetch."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yoktez.client import Client

__all__ = ["MetadataService"]


class MetadataService:
    """`client.metadata` namespace."""

    def __init__(self, client: Client) -> None:
        self.client = client
