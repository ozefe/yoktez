"""Tests for `yoktez.metadata.MetadataService`."""

from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from yoktez import Client, Thesis, ThesisLanguage, ThesisType

FIXTURES = Path(__file__).parent / "fixtures" / "metadata"
_RESULT = (FIXTURES / "result.json").read_text("utf-8")


def _build_client(handler: httpx.MockTransport) -> Client:
    return Client(http_client=httpx.Client(transport=handler))


def _make_thesis(*, thesis_no: str | None = "tez-abc") -> Thesis:
    return Thesis(
        registration_no="kay-xyz",
        thesis_no=thesis_no,
        display_no=1,
        title="T",
        title_translated=None,
        author="A",
        year=2020,
        subject_raw=None,
        degree_type=ThesisType.MASTER,
        language=ThesisLanguage.TURKISH,
        affiliation_raw="U / I",
    )


@pytest.mark.parametrize(
    ("input_arg", "expected_kayit", "expected_tez"),
    [
        (_make_thesis(), "kay-xyz", "tez-abc"),
        (("kay-foo", "tez-bar"), "kay-foo", "tez-bar"),
    ],
)
def test_get_threads_keys_into_query(
    input_arg: Thesis | tuple[str, str],
    expected_kayit: str,
    expected_tez: str,
):
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, text=_RESULT)

    with _build_client(httpx.MockTransport(handler)) as client:
        client.metadata.get(input_arg)

    query = parse_qs(captured[0].url.query.decode())
    assert query["kayitNo"] == [expected_kayit]
    assert query["tezNo"] == [expected_tez]


def test_get_raises_value_error_when_thesis_carries_no_thesis_no():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_RESULT)

    with (
        _build_client(httpx.MockTransport(handler)) as client,
        pytest.raises(ValueError, match="thesis_no=None"),
    ):
        client.metadata.get(_make_thesis(thesis_no=None))
