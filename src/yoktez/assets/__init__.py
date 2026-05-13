"""Assets sub-package: download-key fetch + PDF/appendix streaming."""

from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from yoktez._endpoints import APPENDIX, ASSETS, PDF
from yoktez.assets._parser import parse_thesis_assets
from yoktez.assets.models import ThesisAssets
from yoktez.search.models import Thesis

if TYPE_CHECKING:
    from yoktez.client import Client

__all__ = ["AssetsService", "ThesisAssets"]

_DEFAULT_CHUNK_SIZE = 2**16


class AssetsService:
    """`client.assets` namespace."""

    def __init__(self, client: Client) -> None:
        self.client = client

    def get(self, thesis_or_keys: Thesis | tuple[str, str]) -> ThesisAssets:
        """Fetch the asset bundle for a thesis.

        Args:
            thesis_or_keys: Either a `Thesis` (typically returned by a search) or an
                explicit `(registration_no, thesis_no)` tuple.

        Returns:
            The parsed `ThesisAssets`. Inspect `.status` before calling `download_pdf` /
            `download_appendix` -- the download key is only populated for the
            `AVAILABLE` state.

        Raises:
            ValueError: A `Thesis` was passed with `thesis_no=None`. Such instances
                originate from malformed search-result cards and cannot address the
                assets endpoint; pass an explicit `(registration_no, thesis_no)` tuple
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
            ASSETS, params={"kayitNo": registration_no, "tezNo": thesis_no}
        )
        return parse_thesis_assets(response.text)

    def download_pdf(
        self,
        key: str,
        dest: Path | str | BinaryIO,
        *,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
    ) -> None:
        """Stream the full-text PDF identified by `key` into `dest`.

        Args:
            key: Download token from `ThesisAssets.pdf_key`.
            dest: Filesystem path (`Path` or `str`, opened for writing in binary mode
                and closed afterwards) or a pre-opened binary file-like (written to but
                not closed -- ownership stays with the caller).
            chunk_size: Bytes per `iter_bytes` chunk. Larger values trade memory for
                fewer syscalls.

        Raises:
            httpx.HTTPStatusError: The server returned a non-2xx status.
        """
        self._stream_to_dest(PDF, key, dest, chunk_size)

    def download_appendix(
        self,
        key: str,
        dest: Path | str | BinaryIO,
        *,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
    ) -> None:
        """Stream the appendix archive identified by `key` into `dest`.

        Args:
            key: Download token from `ThesisAssets.appendix_key`.
            dest: Same semantics as `download_pdf.dest`.
            chunk_size: Bytes per `iter_bytes` chunk.

        Raises:
            httpx.HTTPStatusError: The server returned a non-2xx status.

        Note:
            The appendix is typically a RAR archive but YOK NTC does not guarantee the
            format; inspect `Content-Type` on the response if the caller needs to
            branch.
        """
        self._stream_to_dest(APPENDIX, key, dest, chunk_size)

    def _stream_to_dest(
        self,
        url: str,
        key: str,
        dest: Path | str | BinaryIO,
        chunk_size: int,
    ) -> None:
        with self.client.http_client.stream(
            "GET", url, params={"key": key}
        ) as response:
            response.raise_for_status()

            if isinstance(dest, (str, Path)):
                with Path(dest).open("wb") as fh:
                    fh.writelines(response.iter_bytes(chunk_size))
            else:
                for chunk in response.iter_bytes(chunk_size):
                    dest.write(chunk)
