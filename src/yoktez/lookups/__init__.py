"""Lookups sub-package: universities, institutes, divisions, subjects, keywords."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yoktez.client import Client

__all__ = ["LookupsService"]


class LookupsService:
    """`client.lookups` namespace."""

    def __init__(self, client: Client) -> None:
        self.client = client
