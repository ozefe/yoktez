"""Smoke-test the `_endpoints` module surface."""

from urllib.parse import urlparse

from yoktez import _endpoints as ep


def test_each_constant_is_https_url_at_yokntc():
    names = [n for n in dir(ep) if n.isupper() and not n.startswith("_")]

    assert names, "no endpoint constants discovered in yoktez._endpoints"

    for name in names:
        value: str = getattr(ep, name)
        url = urlparse(value)

        assert url.scheme == "https", f"{name} is not https"
        assert url.netloc == "tez.yok.gov.tr", f"{name} points outside YOK NTC"
