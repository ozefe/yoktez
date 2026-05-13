"""HTTP client construction for the YOK NTC session.

Exposes `build_http_client`, which wraps `httpx.Client` with the session-friendly
defaults the YOK NTC JSP/AJAX surface expects: follow-redirects, browser-style
User-Agent, etc.
"""

import logging
from typing import TYPE_CHECKING

import httpx

from yoktez._endpoints import BASE

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "DEFAULT_USER_AGENT",
    "build_http_client",
    "default_transport",
]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3"
)

_DEFAULT_TIMEOUT = 30.0
_DEFAULT_RETRIES = 3

_logger = logging.getLogger("yoktez.http")


def _log_response(response: httpx.Response) -> None:
    request = response.request
    _logger.debug(
        "%s %s -> %d",
        request.method,
        request.url,
        response.status_code,
    )


def default_transport(retries: int = _DEFAULT_RETRIES) -> httpx.HTTPTransport:
    """Build the default `httpx.HTTPTransport` with connection-level retries.

    Args:
        retries: Connection-level retry count. httpx retries only `ConnectError` and
            `ConnectTimeout`; status codes are not retried.

    Returns:
        A fresh transport ready to be passed into `httpx.Client(transport=...)`.
    """
    return httpx.HTTPTransport(retries=retries)


def build_http_client(
    *,
    base_url: str = BASE,
    timeout: float = _DEFAULT_TIMEOUT,
    retries: int = _DEFAULT_RETRIES,
    headers: Mapping[str, str] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """Construct an `httpx.Client` pre-configured for YOK NTC.

    Args:
        base_url: Origin for relative request URLs. Defaults to the YOK NTC base.
        timeout: Per-operation timeout in seconds.
        retries: Connection-level retry count passed to `httpx.HTTPTransport`. Ignored
            when `transport` is supplied.
        headers: Additional default headers merged on top of the library defaults;
            entries here win on conflict.
        transport: Pre-built transport to inject. When omitted, a fresh
            `default_transport(retries)` is constructed.

    Returns:
        An `httpx.Client` with `follow_redirects=True` and the merged header set already
        applied.

    Raises:
        ValueError: `retries` is negative.
    """
    if retries < 0:
        msg = "Retries must be >= 0"
        raise ValueError(msg)

    default_headers: dict[str, str] = {
        "user-agent": DEFAULT_USER_AGENT,
        "accept-language": "en",
    }
    if headers:
        default_headers.update(headers)

    return httpx.Client(
        headers=default_headers,
        timeout=timeout,
        follow_redirects=True,
        base_url=base_url,
        transport=transport if transport is not None else default_transport(retries),
        event_hooks={"response": [_log_response]},
    )
