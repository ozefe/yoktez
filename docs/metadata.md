# Metadata

`client.metadata` fetches per-thesis structured detail: supervisor, full affiliation hierarchy, bilingual keywords, Turkish and other-language abstracts, and pre-formatted citations in five styles.

## The single method

```python
client.metadata.get(thesis_or_keys: Thesis | tuple[str, str]) -> ThesisMetadata
```

`thesis_or_keys` accepts either:

- A `Thesis` returned by a search call. The library reads `thesis.registration_no` and `thesis.thesis_no` off it.
- A `(registration_no, thesis_no)` tuple. Use this when you persisted the keys and don't have the `Thesis` around.

## The return shape

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

Every field is `None`-able because the upstream JSON occasionally omits or empties fields.

> [!NOTE]
> `ThesisMetadata` is the one returned record without `__hash__`. The `list[Bilingual]` field makes the dataclass unhashable; `frozen=True` is preserved for immutability but `hash()` will raise. Use the `registration_no` + `thesis_no` pair as a dict key if you need one.

## Basic example

```python
from yoktez import Client

with Client() as client:
    thesis = client.search.simple("yapay zeka")[0]
    meta = client.metadata.get(thesis)

    print(meta.supervisor)
    if meta.affiliation is not None:
        print(meta.affiliation.university)
    print(meta.abstract_tr[:200] if meta.abstract_tr else "(no Turkish abstract)")
```

## `Affiliation` — the four-tier hierarchy

```python
@dataclass(frozen=True, slots=True)
class Affiliation:
    raw: str
    university: str
    institute: str | None
    division: str | None
    section: str | None
```

Parsed from a slash-separated string. Tiers are populated left-to-right; missing trailing tiers become `None`.

```python
Affiliation.parse("U / I / D / S")
# Affiliation(raw=..., university="U", institute="I", division="D", section="S")

Affiliation.parse("U / I")
# Affiliation(raw=..., university="U", institute="I", division=None, section=None)

Affiliation.parse("Just A University")
# Affiliation(raw=..., university="Just A University", institute=None, division=None, section=None)
```

### Trailing-slash equivalence

```python
a = Affiliation.parse("U / I /")
b = Affiliation.parse("U / I")
assert a.university == b.university and a.institute == b.institute and a.division is None
```

`"U / I /"` parses as 2 tiers, not 3 with a blank `institute`. This makes the trailing-slash and no-trailing-slash forms round-trip identically.

### More than four tiers

If YOK NTC ever returns more than four tiers, the surplus folds back into `section` joined by `" / "`:

```python
Affiliation.parse("U / I / D / S1 / S2")
# Affiliation(raw=..., university="U", institute="I", division="D", section="S1 / S2")
```

This branch is defensive — the upstream has not been observed emitting more than four tiers. The library preserves data rather than dropping it or raising.

## `References` — five pre-formatted citations

```python
@dataclass(frozen=True, slots=True)
class References:
    apa: str
    ieee: str
    mla: str
    chicago: str
    harvard: str
```

Each field is a citation string in the corresponding style. The values are returned verbatim from YOK NTC, **including HTML markup** like `<i>...</i>` around the title.

```python
meta = client.metadata.get(thesis)
if meta.references is not None:
    print(meta.references.apa)
# GÜRLEK, M. (2011). <i>İbrahim Bin Abdullah'ın Cerrah-Name...</i> (Tez No. 286722) [Doktora tezi, MARMARA ÜNİVERSİTESİ]. Ulusal Tez Merkezi.
```

If you need plain text, strip the markup yourself — the library does not do it for you, because the embedded tags are part of the wire data and stripping them is lossy.

`meta.references is None` only when every one of the five fields is empty. A partial response (e.g., only APA populated) returns a `References` with the missing styles as empty strings.

```python
meta.references
# References(apa="GÜRLEK, M. (2011)...", ieee="", mla="", chicago="", harvard="")
```

## `keywords` — bilingual pairs

`keywords` is a `list[Bilingual]` (or `None`). Each element parses a YOK NTC `"Turkish = English"` pair:

```python
@dataclass(order=True, frozen=True, slots=True)
class Bilingual:
    raw: str
    tr: str
    en: str | None
```

```python
meta = client.metadata.get(thesis)
if meta.keywords is not None:
    for kw in meta.keywords:
        print(kw.tr, "=", kw.en)
# Cerrah-name = Cerrah-name
# Dil bilim = Linguistics
# Edebiyat = Literature
# ...
```

`en is None` when no `=` separator was present in the source. `tr` and `en` are stripped of surrounding whitespace; `raw` preserves the original verbatim.

> [!TIP]
> When the thesis is monolingual, the keyword pair often has identical TR and EN halves (e.g., `"Cerrah-name = Cerrah-name"`). This is not a parser bug — it is how YOK NTC represents the case.

## Abstracts

```python
meta.abstract_tr     # the Turkish abstract, or None
meta.abstract_other  # the non-Turkish abstract, or None
```

`abstract_other` is typically English but may be the thesis's primary non-Turkish language for theses written in German, French, Russian, etc. The library does not detect the language — read `thesis.language` for that.

## Identifying a thesis without a full `Thesis`

```python
metadata = client.metadata.get(("kayit_xxx", "tez_yyy"))
```

Use the tuple form when:

- You persisted only the keys (e.g., in a database column) and don't want to round-trip a search just to rebuild the `Thesis`.
- You are iterating over registration numbers from an external source.

The tuple is `(registration_no, thesis_no)` — the order matches the constructor argument order on `Thesis`.

## When `thesis_no` is `None`

```python
malformed = Thesis(registration_no="r", thesis_no=None, ...)
client.metadata.get(malformed)
# ValueError: Thesis(...) has thesis_no=None; pass an explicit (registration_no, thesis_no) tuple instead
```

A `Thesis` with `thesis_no=None` originated from a malformed search-result card. The metadata endpoint requires both keys; sending a `None` would silently fetch the wrong thesis or 500. The library raises at the call site instead.

The standard pattern is to filter these out at search-iteration time:

```python
for t in results:
    if t.thesis_no is None:
        continue
    meta = client.metadata.get(t)
```

## Errors

- `ValueError` — the `Thesis` had `thesis_no=None`. See above.
- `httpx.HTTPStatusError` — the wire returned a non-2xx response. Re-raised unwrapped.
- `httpx.TimeoutException` / `httpx.NetworkError` — transport failure. Re-raised unwrapped.

The library does not currently raise `ParseError` from the metadata path — the upstream returns JSON, and missing keys are treated as absent fields (the matching attribute becomes `None`).

## Live smoke test

```python
# tests/test_metadata_live.py exercises this. Run with `pytest -m live`.
```

The live tests prove the wire JSON shape hasn't drifted. They are not exhaustive.

## See also

- [Search](search.md) — fetch the `Thesis` first.
- [Assets](assets.md) — the next typical call.
- [Data models](data-models.md) — full field reference for every returned dataclass.
