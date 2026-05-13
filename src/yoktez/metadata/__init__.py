"""Metadata sub-package: per-thesis structured detail fetch."""

from typing import TYPE_CHECKING

from yoktez._endpoints import METADATA
from yoktez.metadata._parser import parse_thesis_metadata
from yoktez.metadata.models import Affiliation, References, ThesisMetadata
from yoktez.search.models import Thesis

if TYPE_CHECKING:
    from yoktez.client import Client

__all__ = [
    "Affiliation",
    "MetadataService",
    "References",
    "ThesisMetadata",
]


class MetadataService:
    """`client.metadata` namespace."""

    def __init__(self, client: Client) -> None:
        self.client = client

    def get(self, thesis_or_keys: Thesis | tuple[str, str]) -> ThesisMetadata:
        """Fetch the structured metadata for a thesis.

        Args:
            thesis_or_keys: Either a `Thesis` (typically returned by a search) or an
                explicit `(registration_no, thesis_no)` tuple.

        Returns:
            The parsed `ThesisMetadata`.

        Raises:
            ValueError: A `Thesis` was passed with `thesis_no=None`. Such instances
                originate from malformed search-result cards and cannot address the
                metadata endpoint; pass an explicit `(registration_no, thesis_no)` tuple
                instead.
        """
        if isinstance(thesis_or_keys, Thesis):
            if thesis_or_keys.thesis_no is None:
                msg = (
                    f"{thesis_or_keys!r} has thesis_no=None; pass an explicit "
                    "(registration_no, thesis_no) tuple instead"
                )
                raise ValueError(msg)

            registration_no = thesis_or_keys.registration_no
            thesis_no = thesis_or_keys.thesis_no
        else:
            registration_no, thesis_no = thesis_or_keys

        response = self.client.http_client.get(
            METADATA, params={"kayitNo": registration_no, "tezNo": thesis_no}
        )
        return parse_thesis_metadata(response.json())
