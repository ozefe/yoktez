"""Test that the public `yoktez` surface re-exports every documented name."""

import yoktez

EXPECTED_PUBLIC_NAMES: frozenset[str] = frozenset(
    {
        "AccessType",
        "AdvancedOperator",
        "Affiliation",
        "AssetStatus",
        "Bilingual",
        "Client",
        "Department",
        "Division",
        "Institute",
        "Keyword",
        "KeywordGroup",
        "KeywordLanguage",
        "MatchType",
        "ParseError",
        "References",
        "SearchField",
        "SearchResults",
        "Section",
        "Subject",
        "Thesis",
        "ThesisLanguage",
        "ThesisMetadata",
        "ThesisNoPermitError",
        "ThesisPreparingError",
        "ThesisStatus",
        "ThesisType",
        "ThesisUnavailableError",
        "ThesisUnderEmbargoError",
        "University",
        "UniversitySource",
        "YoktezError",
        "__version__",
    }
)


def test_public_surface_is_complete_and_sorted():
    assert set(yoktez.__all__) == EXPECTED_PUBLIC_NAMES
    assert all(hasattr(yoktez, name) for name in EXPECTED_PUBLIC_NAMES)
    assert list(yoktez.__all__) == sorted(yoktez.__all__)

    # Spot-check that `__version__` is populated, not just declared.
    assert isinstance(yoktez.__version__, str)
    assert yoktez.__version__
