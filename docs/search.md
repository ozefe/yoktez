# Search

`client.search` exposes four query modes against the YOK NTC search surface. All four return the same `SearchResults` wrapper over a tuple of `Thesis` records, so downstream code does not branch on which mode produced them.

## The four modes

| Method | Use when |
| --- | --- |
| `client.search.simple(term, *, field, access, degree_type)` | One free-text query, optionally narrowed to a single field. |
| `client.search.advanced(term1, *, term2, term3, op1, op2, field, match)` | Up to three terms joined by boolean operators. |
| `client.search.detail(*, university, institute, division, subject, ...)` | Multi-filter query (university, year range, degree, language, …). |
| `client.search.recent()` | Last 15 days; no parameters. |

All return `SearchResults`. The same parser handles every shape.

## `SearchResults`

```python
@dataclass(frozen=True, slots=True)
class SearchResults:
    items: tuple[Thesis, ...]
    total: int

    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[Thesis]: ...
    def __getitem__(self, key: int | slice) -> Thesis | SearchResults: ...
```

- `len(results)` returns the size of the result window — the number of cards on the page.
- `results.total` is the **database-wide** match total, parsed from the YOK NTC advisory banner.
- `results[0]` is a `Thesis`; `results[:5]` is a new `SearchResults` with the same `total`.
- Iteration yields `Thesis` records in document order.

> [!IMPORTANT]
> YOK NTC caps the result page at 2,000 cards regardless of how many matches exist. If `results.total > 2000` you only see the first 2,000. Narrow the query (add filters, tighten the year range, scope to a university) to see the remainder.

## `Thesis`

The result-card value object. Every field except the two ID strings is `None`-able because the upstream HTML occasionally omits cells.

```python
@dataclass(frozen=True, slots=True)
class Thesis:
    registration_no: str
    thesis_no: str | None
    display_no: int | None
    title: str | None
    title_translated: str | None
    author: str | None
    year: int | None
    subject_raw: str | None
    degree_type: ThesisType
    language: ThesisLanguage
    affiliation_raw: str
```

See [data models](data-models.md) for full field semantics. The two fields you almost always read first:

- `registration_no` + `thesis_no` — pair these to address the metadata and assets endpoints.
- `display_no` — the integer thesis number a researcher would cite.

## Simple search

```python
from yoktez import Client, SearchField

with Client() as client:
    results = client.search.simple(
        "yapay zeka",
        field=SearchField.ABSTRACT,
    )
    print(f"{results.total} hits, {len(results)} returned on this page")
```

| Parameter | Default | Notes |
| --- | --- | --- |
| `term: str` | — | Free-text query. Required, positional-or-keyword. |
| `field: SearchField \| str \| int` | `SearchField.ALL` | Which field to match. |
| `access: AccessType \| str \| int` | `AccessType.ALL` | Filter by full-text access state. |
| `degree_type: ThesisType \| str \| int` | `ThesisType.ALL` | Filter by degree level. |

All enum-shaped parameters accept three forms:

```python
client.search.simple("term", degree_type=ThesisType.MASTER)
client.search.simple("term", degree_type="MASTER")    # member name
client.search.simple("term", degree_type=1)            # wire code
```

The library prefers the typed form for clarity, but the others are honored — useful for ad-hoc scripts where you don't want to import the enums.

## Advanced search

Joins up to three search terms with boolean operators.

```python
from yoktez import AdvancedOperator, Client, MatchType, SearchField

with Client() as client:
    results = client.search.advanced(
        "sosyal",
        term2="medya",
        term3="uygulama",
        op1=AdvancedOperator.AND,
        op2=AdvancedOperator.OR,
        match=MatchType.INCLUDES,
        field=SearchField.ALL,
    )
```

| Parameter | Default | Notes |
| --- | --- | --- |
| `term1: str` | — | Required. |
| `term2: str \| None` | `None` | Sent as empty string when `None`. |
| `term3: str \| None` | `None` | Sent as empty string when `None`. |
| `op1` | `AdvancedOperator.AND` | Joins `term1` and `term2`. |
| `op2` | `AdvancedOperator.AND` | Joins `(term1 op1 term2)` and `term3`. |
| `field` | `SearchField.ALL` | Which field to match against all terms. |
| `match` | `MatchType.EXACT` | `EXACT` matches as written, `INCLUDES` matches substrings. |

> [!NOTE]
> Boolean precedence on the wire is strictly left-to-right: `(term1 op1 term2) op2 term3`. There are no parentheses on the form surface.

## Detail search

The full filter surface. Every parameter is optional and keyword-only.

```python
from yoktez import Client, ThesisType, ThesisLanguage

with Client() as client:
    unis = client.lookups.universities()
    istanbul = next(u for u in unis if "İSTANBUL" in u.display_name)

    results = client.search.detail(
        university=istanbul,
        year_min=2020,
        year_max=2025,
        degree_type=ThesisType.DOCTORATE,
        language=ThesisLanguage.TURKISH,
    )
```

### Parameter overview

| Parameter | Accepts | Notes |
| --- | --- | --- |
| `university` | `University \| str \| None` | `str` is the YOKSIS ID. A `University` carries display name, opaque ID, YOKSIS ID, and source — all four are sent. |
| `institute` | `Institute \| int \| None` | `int` is the numeric wire ID. `None` sends `"0"`. |
| `division` | `Division \| int \| None` | Same shape as `institute`. |
| `subject` | `Subject \| str \| None` | `str` is sent verbatim (free-text); `Subject.display.raw` is sent for typed input. |
| `degree_type` | `ThesisType \| str \| int` | Default `ALL`. |
| `year_min` | `int \| None` | Must be `>= 1900`. `None` sends `"0"`. |
| `year_max` | `int \| None` | `None` sends `"0"`. |
| `access` | `AccessType \| str \| int` | Default `ALL`. |
| `status` | `ThesisStatus \| str \| int` | **Default `APPROVED`**, not `ALL`. Most callers want only confirmed theses. |
| `title` | `str \| None` | Substring filter on the title. |
| `language` | `ThesisLanguage \| str \| int` | Default `ALL`. |
| `author` | `str \| None` | Substring filter on the author. |
| `supervisor` | `str \| None` | Substring filter on the supervisor. |
| `keyword` | `str \| None` | Keyword filter. |
| `thesis_display_no` | `int \| None` | Human-readable thesis number (the `Tez No:` value). |

### Validation

```python
client.search.detail(year_min=1899)
# ValueError: year_min must be >= 1900; got 1899

client.search.detail(year_min=2024, year_max=2020)
# ValueError: year_min (2024) must be <= year_max (2020)
```

The two checks fail fast before any wire request.

### Why `status` defaults to `APPROVED`

YOK NTC's wire default is `ALL`. The library's default is `APPROVED` because that is what almost every caller wants — `PREPARING` theses don't have downloadable assets, and `ALL` returns both. Override explicitly when you need the others:

```python
results = client.search.detail(status=ThesisStatus.ALL)
```

### Hierarchical models vs raw IDs

Three input shapes per hierarchical filter:

```python
# Typed model — display name, ID, and YOKSIS ID all sent
results = client.search.detail(university=university_model)

# Raw YOKSIS ID — display fields sent empty
results = client.search.detail(university="ZDJv5lAIQDOnVGpRdJBQxA")

# Omitted — wire fields sent empty / zero
results = client.search.detail()
```

Same for `institute` (typed model or `int` numeric ID) and `division` (typed model or `int` numeric ID). Hand-constructed models with `yoksis_id=None` will raise `ValueError` at the call site rather than send a malformed request.

## Recent search

```python
with Client() as client:
    results = client.search.recent()
```

No parameters. Returns the theses added in the last 15 days. The window is server-fixed; the library does not let you change it. Use this for monitoring / "what's new" panels.

## Empty result handling

A successful query with no matches returns `SearchResults(items=(), total=0)`. The advisory banner that carries the database total is omitted entirely by YOK NTC on empty pages, so the parser falls back to zero without warning.

```python
results = client.search.simple("ThisWillNeverMatch_XYZABC123")
assert len(results) == 0
assert results.total == 0
```

This is intentionally indistinguishable in the return value from "the wire shape changed and we lost the total" — the latter is logged to `yoktez.search` at WARNING level if the advisory banner exists but the regex misses it. See [logging](logging.md).

## Slicing semantics

```python
results = client.search.simple("yapay zeka")

first_page = results[:25]    # SearchResults
second_page = results[25:50] # SearchResults
top_result = results[0]      # Thesis
```

Slices return a new `SearchResults` whose `total` is preserved from the source query. The slice is a window into the same query, not a re-query: the database-wide match total stays correct.

Negative indices work. Out-of-bounds indices raise `IndexError`.

## Iterating safely

```python
with Client() as client:
    results = client.search.simple("yapay zeka")

    for thesis in results:
        if thesis.thesis_no is None:
            # Malformed search-result card; cannot address metadata/assets endpoints.
            continue

        meta = client.metadata.get(thesis)
        ...
```

Always guard on `thesis_no is not None` before passing a `Thesis` to `client.metadata.get` or `client.assets.get`. The library will raise `ValueError` if you don't, but checking up front gives you cleaner control flow when you want to skip rather than crash.

## Round-tripping a thesis from a search

```python
results = client.search.simple("yapay zeka")
thesis = results[0]

# Find every other thesis with the same display_no — useful when display_no is the
# stable identifier across a database migration.
again = client.search.detail(thesis_display_no=thesis.display_no)
```

`display_no` is the integer thesis number printed on the cover page (`Tez No: 286722`). It is stable across sessions and a natural cross-reference. `registration_no` and `thesis_no` are opaque tokens — they survive across requests but should be treated as opaque, not parsed.

## Gotchas

### `degree_type=ThesisType.ALL` is the default, not "any"

`ALL` is a sentinel `0` that the wire treats as "no filter". `MASTER` is `1`. There is no value that means "everything but `ALL`".

### `match=MatchType.EXACT` only applies to advanced search

Simple search has no match-type parameter. Advanced search defaults to `EXACT`.

### `field=SearchField.KEYWORD` searches the YOK NTC keyword index, not free text

The keyword index is curated; arbitrary words won't appear there. Use `SearchField.ABSTRACT` for free-text matching against the body.

### Unicode in queries works without escaping

YOK NTC speaks UTF-8 over `application/x-www-form-urlencoded`. The library uses httpx's form encoder; you don't need to manually URL-encode Turkish characters.

```python
client.search.simple("eğitim")    # works fine
client.search.simple("İSTANBUL")  # works fine — dotted İ included
```

### Live network smoke tests

The repository's `tests/test_search_live.py` is opt-in via `pytest -m live`. Default `pytest` runs skip them. They're useful as a one-shot "is the wire shape still what we expect?" check after a long pause.

## See also

- [Metadata](metadata.md) — the natural next call after `search`.
- [Assets](assets.md) — the call after that, for downloading PDFs.
- [Lookups](lookups.md) — get a typed `University` / `Institute` / `Subject` to pass into `detail`.
- [Enums](enums.md) — every enum used by the search surface.
