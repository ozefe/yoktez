"""Tests for `yoktez.client.Client`."""

import httpx

from yoktez.client import Client
from yoktez.search import SearchService


def _mock_http_client() -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200)),
        base_url="https://test/",
    )


def test_sub_service_is_lazy_memoized_and_back_references_parent():
    # One sub-service stands in for all: every sub-service uses the same lazy `_<name>`
    # cache + `Service(self)` construction in `Client`. A bug there breaks all of them;
    # testing one is enough.
    with Client(http_client=_mock_http_client()) as client:
        first = client.search

        assert isinstance(first, SearchService)
        assert client.search is first  # memoized
        assert first.client is client  # back-references parent


def test_owned_http_client_is_closed_on_exit():
    with Client() as client:
        inner = client.http_client

    assert inner.is_closed


def test_injected_http_client_is_not_closed_on_exit():
    external = _mock_http_client()

    try:
        with Client(http_client=external):
            pass

        assert not external.is_closed
    finally:
        external.close()


def test_close_is_idempotent():
    client = Client(http_client=_mock_http_client())

    client.close()
    client.close()  # must not raise
