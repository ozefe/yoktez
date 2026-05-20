# Data models

Every record returned by `yoktez` is a `@dataclass(frozen=True, slots=True)`. They are immutable, slotted, and (with one exception) hashable. Type information is `py.typed`, so downstream pyright / mypy trusts the annotations.

## Quick table

| Model | Module | Hashable | Returned by |
| --- | --- | --- | --- |
| `Bilingual` | `yoktez.bilingual` | yes | nested in keywords, subjects |
| `Thesis` | `yoktez.search.models` | yes | `client.search.*` |
| `SearchResults` | `yoktez.search.models` | yes | `client.search.*` |
| `Affiliation` | `yoktez.metadata.models` | yes | `ThesisMetadata.affiliation` |
| `References` | `yoktez.metadata.models` | yes | `ThesisMetadata.references` |
| `ThesisMetadata` | `yoktez.metadata.models` | **no** | `client.metadata.get(...)` |
| `ThesisAssets` | `yoktez.assets.models` | yes | `client.assets.get(...)` |
| `University` | `yoktez.lookups.models` | yes | `client.lookups.universities(...)` |
| `Institute` | `yoktez.lookups.models` | yes | `client.lookups.institutes(...)` |
| `Division` | `yoktez.lookups.models` | yes | `client.lookups.divisions(...)` |
| `Subject` | `yoktez.lookups.models` | yes | `client.lookups.all_subjects()` |
| `Keyword` | `yoktez.lookups.models` | yes | `client.lookups.keywords(...)` |
| `Department` | `yoktez.lookups.models` | yes | `client.lookups.all_departments()` |
| `Section` | `yoktez.lookups.models` | yes | `client.lookups.all_sections()` |

The single unhashable record is `ThesisMetadata` — its `keywords: list[Bilingual] | None` field disables `__hash__`. Use `(registration_no, thesis_no)` as a dict key if you need one.

## `Bilingual`

```python
@dataclass(order=True, frozen=True, slots=True)
class Bilingual:
    raw: str
    tr: str
    en: str | None

    @classmethod
    def parse(cls, raw_text: str) -> Self: ...
```

Parses a `"Turkish = English"` pair. Splits on the first `=` only:

```python
Bilingual.parse("Türkçe = Turkish")
# Bilingual(raw="Türkçe = Turkish", tr="Türkçe", en="Turkish")

Bilingual.parse("a = b = c")
# Bilingual(raw="a = b = c", tr="a", en="b = c")

Bilingual.parse("Türkçe")
# Bilingual(raw="Türkçe", tr="Türkçe", en=None)

Bilingual.parse("  Türkçe   =   Turkish  ")
# Bilingual(raw="  Türkçe   =   Turkish  ", tr="Türkçe", en="Turkish")
```

`raw` is preserved verbatim. `tr` and `en` are whitespace-stripped. `en is None` when no separator is present.

`order=True` is set, so `Bilingual` supports `<` / `<=` / `>` / `>=` lexicographically by `(raw, tr, en)`. Useful for sorting.

## `Thesis`

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

| Field | When `None` |
| --- | --- |
| `registration_no` | Never; always `""` minimum. |
| `thesis_no` | When the result card was malformed. Filter these out. |
| `display_no` | When the card omits the `Tez No:` strong-label cell. |
| `title` | When the card omits the title cell. |
| `title_translated` | When no translation is provided. |
| `author` | When the card omits the author. |
| `year` | When the year is missing or unparsable. |
| `subject_raw` | When the subject cell is empty. |
| `affiliation_raw` | Never; empty string when truly absent. |

`subject_raw` and `affiliation_raw` are deliberately raw — subjects can be multi-valued and semicolon-separated, affiliations are slash-separated. Parsing is left to the caller; use `Affiliation.parse(thesis.affiliation_raw)` to structure the latter.

`degree_type` and `language` are resolved on the response side via `from_display()` on the matching enums (see [enums](enums.md)). They never default to `ALL`; that sentinel is request-side only.

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

`items` is a tuple, not a list — immutability is preserved through the dataclass `frozen=True` AND the storage type. `total` is the database-wide match total, not `len(items)`. The two values differ once `total > 2000` (the upstream's hard cap).

Slicing returns a new `SearchResults` with the same `total`. Indexing returns a single `Thesis`.

## `Affiliation`

```python
@dataclass(frozen=True, slots=True)
class Affiliation:
    raw: str
    university: str
    institute: str | None
    division: str | None
    section: str | None

    @classmethod
    def parse(cls, raw_text: str) -> Self: ...
```

Four-tier institutional hierarchy. See [metadata](metadata.md) for parsing semantics and edge cases.

## `References`

```python
@dataclass(frozen=True, slots=True)
class References:
    apa: str
    ieee: str
    mla: str
    chicago: str
    harvard: str
```

Five pre-formatted citations, returned verbatim from YOK NTC including HTML markup (`<i>...</i>` around titles).

## `ThesisMetadata`

```python
@dataclass(frozen=True, slots=True)
class ThesisMetadata:
    supervisor: str | None
    affiliation: Affiliation | None
    keywords: list[Bilingual] | None
    abstract_tr: str | None
    abstract_other: str | None
    references: References | None
```

The unhashable one. Every field is `None`-able; check before reading.

## `ThesisAssets`

```python
@dataclass(frozen=True, slots=True)
class ThesisAssets:
    status: AssetStatus
    pdf_key: str | None
    appendix_key: str | None
    restricted_until: dt.date | None
    info_message: str | None
```

See [assets](assets.md) for the population matrix per `status` value.

## `University`

```python
@dataclass(frozen=True, slots=True)
class University:
    display_name: str
    id: str
    yoksis_id: str | None
    source: UniversitySource
```

`id` is a `str` because the modern endpoint returns an opaque Base64-like token. `yoksis_id` is `None` for records sourced from legacy bulk endpoints; the modern `getUniversities.jsp` always carries it.

`source` is required (no default) so a hand-constructed `University` can't accidentally lose its scope.

## `Institute` / `Division`

```python
@dataclass(frozen=True, slots=True)
class Institute:
    display_name: str
    id: int
    yoksis_id: str | None

@dataclass(frozen=True, slots=True)
class Division:
    display_name: str
    id: int
```

`Institute.id` and `Division.id` are `int` (wire form is numeric). `Division` does not have a `yoksis_id` because the divisions endpoint never emits one.

## `Subject` / `Keyword`

```python
@dataclass(frozen=True, slots=True)
class Subject:
    display: Bilingual
    id: int

@dataclass(frozen=True, slots=True)
class Keyword:
    display: Bilingual
    id: int
    group: KeywordGroup | None
```

Both have a pre-parsed `display: Bilingual` rather than raw strings. `Keyword.group` is populated only when the fetch was scoped to a single group.

## `Department` / `Section`

```python
@dataclass(frozen=True, slots=True)
class Department:
    display_name: str
    id: int

@dataclass(frozen=True, slots=True)
class Section:
    display_name: str
    id: int
```

Plain display + numeric ID. Not currently usable as search filters; exposed for completeness.

## Patterns

### Immutability

```python
thesis = results[0]
thesis.title = "new title"
# dataclasses.FrozenInstanceError: cannot assign to field 'title'
```

Every record is frozen. To produce a modified copy, use `dataclasses.replace`:

```python
import dataclasses
modified = dataclasses.replace(thesis, title="new title")
```

### Hashing

```python
unique_theses = set(results)
seen_unis = {u for u in client.lookups.universities()}
```

All models except `ThesisMetadata` are hashable and work as set / dict keys.

### Equality

Frozen dataclasses get structural equality for free:

```python
results[0] == results[0]  # True (same instance and value)
Thesis(...) == Thesis(...)  # True if all fields match
```

### `repr`

Default dataclass `repr` is verbose. For logs or terminals, print specific fields:

```python
print(f"{thesis.year} {thesis.title}")
```

### Serialization

The library does not provide JSON serializers. `dataclasses.asdict(thesis)` produces a dict that `json.dumps` can encode — caveat: it does not handle `datetime.date` directly (`ThesisAssets.restricted_until`), so write a `default=` callable for `json.dumps` if you use it:

```python
import dataclasses, datetime as dt, json

def _default(o):
    if isinstance(o, dt.date):
        return o.isoformat()
    raise TypeError

json.dumps(dataclasses.asdict(assets), default=_default)
```

## See also

- [Bilingual](metadata.md#keywords--bilingual-pairs) and [Affiliation](metadata.md#affiliation--the-four-tier-hierarchy) parsing semantics.
- [Enums](enums.md) — the enum types referenced from these models.
- [Errors](errors.md) — what gets raised when a model can't be constructed.
