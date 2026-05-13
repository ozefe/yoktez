"""Top-level `Client` -- the single entry point for the `yoktez` library."""

from typing import TYPE_CHECKING, Self

from yoktez._http import DEFAULT_USER_AGENT, build_http_client
from yoktez.assets import AssetsService
from yoktez.lookups import LookupsService
from yoktez.metadata import MetadataService
from yoktez.search import SearchService

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import TracebackType

    import httpx

__all__ = ["Client"]


class Client:
    """Synchronous YOK NTC client.

    Wraps an `httpx.Client` and exposes four lazily-instantiated sub-services: `search`,
    `metadata`, `assets`, and `lookups`.

    Use as a context manager to release the underlying HTTP connection pool
    deterministically.

    Args:
        timeout: Per-request timeout in seconds. Ignored when `http_client` is supplied.
        retries: Connection-level retry count. Ignored when `http_client` is supplied.
        user_agent: Override for the default browser-style User-Agent. Ignored when
            `http_client` is supplied.
        extra_headers: Additional default headers merged on top of the library defaults.
            Ignored when `http_client` is supplied.
        http_client: Pre-built `httpx.Client` to use instead of constructing one. When
            supplied, the client is NOT closed by `close()` / `__exit__`; ownership
            stays with the caller.
    """

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        retries: int = 3,
        user_agent: str = DEFAULT_USER_AGENT,
        extra_headers: Mapping[str, str] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if http_client is None:
            headers: dict[str, str] = {"user-agent": user_agent}
            if extra_headers:
                headers.update(extra_headers)

            self.http_client = build_http_client(
                timeout=timeout,
                retries=retries,
                headers=headers,
            )

            self._owns_http = True
        else:
            self.http_client = http_client

            self._owns_http = False

        # Sub-services hold a back-reference to this Client; eager construction would
        # force every import path even when only one service is used.
        self._search: SearchService | None = None
        self._metadata: MetadataService | None = None
        self._assets: AssetsService | None = None
        self._lookups: LookupsService | None = None

        self._closed = False

    @property
    def search(self) -> SearchService:
        """The search sub-service. Instantiated on first access."""
        if self._search is None:
            self._search = SearchService(self)

        return self._search

    @property
    def metadata(self) -> MetadataService:
        """The metadata sub-service. Instantiated on first access."""
        if self._metadata is None:
            self._metadata = MetadataService(self)

        return self._metadata

    @property
    def assets(self) -> AssetsService:
        """The assets sub-service. Instantiated on first access."""
        if self._assets is None:
            self._assets = AssetsService(self)

        return self._assets

    @property
    def lookups(self) -> LookupsService:
        """The lookups sub-service. Instantiated on first access."""
        if self._lookups is None:
            self._lookups = LookupsService(self)

        return self._lookups

    def close(self) -> None:
        """Close the underlying `httpx.Client` and release its connection pool.

        Note:
            No-op when the HTTP client was injected via `http_client=` (ownership stays
            with the caller) or when `close()` has already run.
        """
        if self._closed:
            return

        if self._owns_http:
            self.http_client.close()

        self._closed = True

    def __enter__(self) -> Self:
        """Bind this `Client` to the `with` statement variable.

        Returns:
            `self`, so `with Client() as c: ...` makes the client available as `c`.

        Note:
            No I/O happens here: the underlying `httpx.Client` was already constructed
            (or injected) in `__init__`.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Delegate to `close()` on `with`-block exit.

        Note:
            Does nothing if the underlying HTTP client was injected via the
            `http_client` constructor parameter (ownership stays with the caller).
            Exceptions raised inside the `with` block propagate unchanged: we never
            swallow them.
        """
        self.close()
