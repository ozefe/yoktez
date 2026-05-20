# Lookups

`client.lookups` resolves the catalogs YOK NTC uses to filter searches: universities, institutes, divisions, subjects, keywords, departments, sections. Every call is memoized per `Client` instance.

## The method surface

| Method | Returns | Notes |
| --- | --- | --- |
| `universities(source=UniversitySource.TR)` | `list[University]` | Scope is required; defaults to `TR`. |
| `institutes(university)` | `list[Institute]` | Hierarchical — needs a university's YOKSIS ID. |
| `divisions(university, institute)` | `list[Division]` | Hierarchical — needs both YOKSIS IDs. |
| `all_universities()` | `list[University]` | TR + INT, combined and uniform. |
| `all_institutes()` | `list[Institute]` | Bulk dump across every university. |
| `all_divisions()` | `list[Division]` | Bulk dump. |
| `all_subjects()` | `list[Subject]` | Bilingual names parsed into `Bilingual`. |
| `keywords(*, group, language, first_letter, search)` | `list[Keyword]` | Filterable. |
| `all_keywords()` | `list[Keyword]` | Shortcut for `keywords()` with no filters. |
| `all_departments()` | `list[Department]` | Not currently usable as a search filter. |
| `all_sections()` | `list[Section]` | Not currently usable as a search filter. |
| `refresh()` | `None` | Clear the per-instance cache. |

## Memoization

Every call is memoized on `Client.lookups._cache: dict[tuple[object, ...], object]`. The cache key is `(method_name, *normalized_primitive_args)`. Cache lookups normalize the arguments first, so all these hit the same key:

```python
client.lookups.universities(UniversitySource.TR)
client.lookups.universities("TR")
client.lookups.universities("TR")   # all three resolve to the same cache entry
```

The cache has no TTL. Call `client.lookups.refresh()` to clear it.

> [!NOTE]
> The cache is per-`Client`. Two `Client` instances have independent caches. This is intentional — one-`Client`-per-thread keeps multi-threaded callers honest without locks (see [concurrency](concurrency.md)).

## Universities

```python
from yoktez import Client, UniversitySource

with Client() as client:
    tr_unis = client.lookups.universities()                     # default TR
    int_unis = client.lookups.universities(UniversitySource.INT)
    all_unis = client.lookups.all_universities()                # TR + INT

    istanbul = next(u for u in tr_unis if "İSTANBUL" in u.display_name)
    print(istanbul.id, istanbul.yoksis_id, istanbul.source.name)
```

```python
@dataclass(frozen=True, slots=True)
class University:
    display_name: str
    id: str             # opaque Base64-like token
    yoksis_id: str | None
    source: UniversitySource
```

`University.id` is a `str` (not `int`); the modern endpoint returns an opaque Base64-like token. The `source` field carries the endpoint origin (`TR` or `INT`), preserved so a downstream `client.search.detail(university=u)` can re-issue with the correct scope without you remembering it.

### Why `all_universities()` composes two calls

`all_universities()` calls `universities(TR)` and `universities(INT)` and concatenates. It does **not** hit the legacy `uniEkle.jsp` endpoint. The legacy endpoint exposes only numeric IDs and no YOKSIS ID, which would make its records useless for hierarchical lookups (`institutes()` and `divisions()` need YOKSIS IDs).

After the first `universities(TR)` and `universities(INT)` calls, `all_universities()` is effectively free — the underlying calls are memoized.

## Institutes and divisions

```python
with Client() as client:
    unis = client.lookups.universities()
    istanbul = next(u for u in unis if "İSTANBUL" in u.display_name)

    inst = client.lookups.institutes(istanbul)
    sosyal = next(i for i in inst if "SOSYAL" in i.display_name)

    div = client.lookups.divisions(istanbul, sosyal)
    print(f"{len(div)} divisions under {sosyal.display_name}")
```

Both methods accept either a typed model or a YOKSIS ID string:

```python
# Equivalent calls — both hit the same cache key after normalization.
client.lookups.institutes(istanbul)
client.lookups.institutes("ZDJv5lAIQDOnVGpRdJBQxA")
```

### Legacy-source rejection

`University` and `Institute` instances loaded from a legacy bulk endpoint (e.g., the old `uniEkle.jsp`) have `yoksis_id=None`. Passing one to `institutes()` or `divisions()` raises:

```python
legacy = University(display_name="X", id="42", yoksis_id=None, source=UniversitySource.TR)
client.lookups.institutes(legacy)
# ValueError: University(...) has yoksis_id=None; need non-None value to drive hierarchical lookups
```

The library raises loudly at the call site rather than send `?uniKod=None` to the wire.

## Subjects

```python
with Client() as client:
    subjects = client.lookups.all_subjects()
    print(subjects[0].id, subjects[0].display.tr, "/", subjects[0].display.en)
```

```python
@dataclass(frozen=True, slots=True)
class Subject:
    display: Bilingual
    id: int
```

`Subject.display` is pre-parsed into a `Bilingual`, so `.tr` / `.en` are ready to use:

```python
alman = next(s for s in subjects if s.display.tr.startswith("Alman"))
print(alman.display.raw)   # "Alman Dili ve Edebiyatı = German Linguistics and Literature"
print(alman.display.tr)    # "Alman Dili ve Edebiyatı"
print(alman.display.en)    # "German Linguistics and Literature"
```

Pass a `Subject` directly to `client.search.detail(subject=...)`. The library sends `subject.display.raw` on the wire.

## Keywords

```python
from yoktez import Client, KeywordGroup, KeywordLanguage

with Client() as client:
    # Everything, no filter
    all_keywords = client.lookups.all_keywords()

    # Just the medicine keywords
    medical = client.lookups.keywords(group=KeywordGroup.MEDICINE)

    # Turkish keywords starting with "A" matching the substring "antropoloji"
    matches = client.lookups.keywords(
        language=KeywordLanguage.TURKISH,
        first_letter="A",
        search="antropoloji",
    )
```

```python
@dataclass(frozen=True, slots=True)
class Keyword:
    display: Bilingual
    id: int
    group: KeywordGroup | None
```

`Keyword.group` is populated only when the fetch was scoped to a single group; unscoped calls return `None`. This lets you attribute results back to a group without re-querying.

> [!IMPORTANT]
> `all_keywords()` returns ~88,000 records and the wire response is ~25 MB. The first call is slow; subsequent calls hit the cache. Consider whether you actually need all keywords or whether you can filter via `keywords(...)`.

### Filter combinations

The four kwargs to `keywords()` are independent. Any combination works, including all four together:

```python
client.lookups.keywords(
    group=KeywordGroup.SCIENCE,
    language=KeywordLanguage.ENGLISH,
    first_letter="M",
    search="molecule",
)
```

Each unique tuple memoizes separately. `client.lookups.keywords()` and `client.lookups.all_keywords()` share the same cache entry (the latter is a thin wrapper over the former).

## Departments and sections

```python
with Client() as client:
    departments = client.lookups.all_departments()
    sections = client.lookups.all_sections()
```

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

These are exposed for completeness — `Department` and `Section` lists exist on the upstream — but they are not currently usable as search filters. The detail search surface does not expose `department=` or `section=` parameters.

## `refresh()`

```python
with Client() as client:
    unis = client.lookups.universities()
    # ...time passes; suspect YOKSIS IDs have rotated...
    client.lookups.refresh()
    unis = client.lookups.universities()  # re-fetched
```

`refresh()` clears the entire per-instance cache. There is no per-method invalidation; cache misses are cheap enough that selective invalidation isn't worth the API complexity.

YOK NTC rotates YOKSIS IDs more often than you'd expect. From the upstream notes:

> The YOKSIS IDs ... are not static, they change with each refresh. They don't even stay the same within the same session. Old YOKSIS IDs work as well and I don't know if they have some sort of expiration.

In practice this means: cached IDs continue working long after they were captured (the upstream tolerates stale tokens), so refreshing is mostly a precaution. If you start seeing unexpected empty institute/division lists, call `refresh()` and retry once.

## Combining lookups with `search.detail`

```python
with Client() as client:
    unis = client.lookups.universities()
    istanbul = next(u for u in unis if "İSTANBUL ÜNİVERSİTESİ" in u.display_name)

    institutes = client.lookups.institutes(istanbul)
    sosyal = next(i for i in institutes if "SOSYAL" in i.display_name)

    divisions = client.lookups.divisions(istanbul, sosyal)
    cinema = next(d for d in divisions if "SİNEMA" in d.display_name)

    # All three typed models thread cleanly into detail().
    results = client.search.detail(
        university=istanbul,
        institute=sosyal,
        division=cinema,
        year_min=2020,
    )
```

The typed flow is the recommended one — every model carries the necessary IDs, the library does the right thing with the source scope, and pyright catches mistakes at compile time.

## Gotchas

### `universities()` returns only one source

By default `universities()` returns Turkish universities only. Call `universities(UniversitySource.INT)` for international ones, or `all_universities()` for both.

### Caches survive `client.close()` — until the `Client` is GC'd

The cache lives on the `LookupsService` attached to the `Client`. Closing the `Client` releases the HTTP pool but does not clear the cache. The cache dies when the `Client` itself is garbage-collected.

### `all_keywords()` is slow on the first call

Tens of MB of HTML, parsed via regex (not BS4) for speed. Even so, expect multiple seconds on the first call. Subsequent calls are dict lookups.

### The legacy bulk endpoints are present in `_endpoints.py` but unused

`ALL_UNIVERSITIES_OLD`, `ALL_INSTITUTES_OLD`, `ALL_DIVISIONS_OLD` are documented in `src/yoktez/_endpoints.py` but no service hits them. They are kept as documentation of endpoints that exist; the modern composition is preferred because it preserves YOKSIS IDs.

## See also

- [Search](search.md) — `detail()` is the primary consumer of lookup results.
- [Data models](data-models.md) — full field reference.
- [Concurrency](concurrency.md) — one-`Client`-per-thread caching trade-offs.
