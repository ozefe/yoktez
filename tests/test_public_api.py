"""Test that the public `yoktez` surface is internally consistent."""

import yoktez


def test_every_name_in_all_is_resolvable():
    assert all(hasattr(yoktez, name) for name in yoktez.__all__)


def test_all_is_sorted():
    assert list(yoktez.__all__) == sorted(yoktez.__all__)


def test_version_is_populated():
    assert isinstance(yoktez.__version__, str)
    assert yoktez.__version__
