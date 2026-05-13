"""Opt-in live-network smoke test for `MetadataService`.

Run with `pytest -m live` to hit the real YOK NTC endpoint. Default `pytest` runs skip
this. Proves the wire shape hasn't drifted from what the parser expects; not an
exhaustive feature test.
"""

import pytest

from yoktez import Client


@pytest.mark.live
def test_metadata_get_against_real_yok_ntc():
    # The doc thesis (`MEHMET GÜRLEK`, 2011) is stable and used as the fixture upstream;
    # its keys are well-known.
    with Client() as client:
        metadata = client.metadata.get(
            ("Gqu0scu9o-F0RmNv9a07Jg", "4k77eqFvoAqeZbjb7Q2iMQ")
        )

    assert metadata.supervisor
    assert metadata.affiliation is not None
    assert metadata.affiliation.university
