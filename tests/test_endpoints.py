"""Smoke-test the `_endpoints` module surface."""

from urllib.parse import urlparse

from yoktez import _endpoints as ep

EXPECTED: frozenset[str] = frozenset(
    {
        "BASE",
        "SEARCH",
        "RESULT",
        "RECENT",
        "METADATA",
        "ASSETS",
        "PDF",
        "APPENDIX",
        "UNIVERSITIES",
        "TARAMA_AJAX",
        "ALL_UNIVERSITIES_OLD",
        "ALL_INSTITUTES_OLD",
        "ALL_DIVISIONS_OLD",
        "ALL_SUBJECTS",
        "ALL_DEPARTMENTS",
        "ALL_SECTIONS",
        "KEYWORDS_SEARCH",
    }
)


def test_expected_names_exist():
    public = {
        endpoint
        for endpoint in dir(ep)
        if endpoint.isupper() and not endpoint.startswith("_")
    }
    missing = EXPECTED - public

    assert not missing, f"missing endpoint constants: {sorted(missing)}"


def test_each_constant_is_https_url_at_yokntc():
    for name in EXPECTED:
        value: str = getattr(ep, name)
        url = urlparse(value)

        assert url.scheme == "https", f"{name} is not https"
        assert url.netloc == "tez.yok.gov.tr", f"{name} points outside YOK NTC"
