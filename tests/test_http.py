"""Tests for `yoktez._http`."""

import httpx
import pytest

from yoktez._endpoints import SEARCH
from yoktez._http import build_http_client


def _capture(into: dict[str, httpx.Request]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        into["request"] = request

        return httpx.Response(200, json={"path": request.url.path})

    return httpx.MockTransport(handler)


def test_request_carries_default_headers_and_reaches_endpoint():
    captured: dict[str, httpx.Request] = {}

    with build_http_client(transport=_capture(captured)) as client:
        response = client.get(SEARCH)

    assert response.json() == {"path": "/UlusalTezMerkezi/SearchTez"}
    assert "Mozilla" in captured["request"].headers["user-agent"]
    assert captured["request"].headers["accept-language"] == "en"


def test_extra_headers_merge_and_override_defaults():
    captured: dict[str, httpx.Request] = {}
    headers = {"user-agent": "custom/1.0", "X-Foo": "bar"}

    with build_http_client(headers=headers, transport=_capture(captured)) as client:
        client.get(SEARCH)

    assert captured["request"].headers["user-agent"] == "custom/1.0"
    assert captured["request"].headers["x-foo"] == "bar"
    assert captured["request"].headers["accept-language"] == "en"


def test_negative_retries_rejected():
    with pytest.raises(ValueError, match="Retries must be >= 0"):
        build_http_client(retries=-1)
