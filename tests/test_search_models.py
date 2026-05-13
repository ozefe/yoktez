"""Tests for `yoktez.search.models`."""

from yoktez import SearchResults, Thesis, ThesisLanguage, ThesisType


def _example_thesis() -> Thesis:
    return Thesis(
        registration_no="reg-1",
        thesis_no="opaque-1",
        display_no=1004858,
        title="T",
        title_translated="T-en",
        author="A",
        year=2026,
        subject_raw="S",
        degree_type=ThesisType.DOCTORATE,
        language=ThesisLanguage.TURKISH,
        affiliation_raw="U / I",
    )


def test_search_results_supports_len_iter_and_int_indexing():
    thesis = _example_thesis()
    results = SearchResults((thesis, thesis, thesis))

    assert len(results) == 3
    assert list(results) == [thesis, thesis, thesis]
    assert results[0] is thesis
    assert results[-1] is thesis


def test_search_results_slicing_returns_a_new_search_results():
    thesis = _example_thesis()
    results = SearchResults((thesis, thesis, thesis))

    sliced = results[:2]

    assert isinstance(sliced, SearchResults)
    assert len(sliced) == 2
