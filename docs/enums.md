# Enums

Every enum used by the request and response surfaces lives in `yoktez.enums` and is re-exported from the package root. Integer-valued enums subclass `IntEnum`; string-valued ones subclass `StrEnum`. The `coerce()` helper and `from_display()` classmethods bridge the request and response sides.

## Request side: `coerce()`

`coerce(enum_cls, value)` resolves a value to its wire form.

```python
from yoktez import ThesisType
from yoktez.enums import coerce

coerce(ThesisType, ThesisType.MASTER)  # 1
coerce(ThesisType, 1)                  # 1
coerce(ThesisType, "MASTER")           # 1
coerce(ThesisType, "1")                # 1
```

All four forms work for `IntEnum` targets. For `StrEnum` targets, the member name and the wire string are both accepted:

```python
from yoktez import KeywordGroup
from yoktez.enums import coerce

coerce(KeywordGroup, KeywordGroup.SCIENCE)  # "F"
coerce(KeywordGroup, "SCIENCE")              # "F"
coerce(KeywordGroup, "F")                    # "F"
```

### `IntEnum` passthrough

Unknown integers pass through unchanged for `IntEnum` targets:

```python
coerce(ThesisStatus, 99)  # 99 — tolerated; let YOK NTC adjudicate
```

This is deliberate. The wire occasionally introduces new codes; passthrough lets your script use them without waiting for a library release.

### `StrEnum` strictness

Unknown strings raise `ValueError` for `StrEnum` targets:

```python
coerce(KeywordGroup, "bogus")
# ValueError: 'bogus' is not a member of KeywordGroup
```

Small string enums (`KeywordGroup` has three members; `UniversitySource` has two) cannot tolerate typos silently — a typo would produce a broken request.

### Wrong Python type

```python
coerce(ThesisType, 1.5)
# TypeError: Cannot coerce float to ThesisType
```

`coerce` accepts `Enum`, `int`, or `str`. Anything else raises `TypeError`.

## Response side: `from_display()`

`ThesisType` and `ThesisLanguage` expose a `from_display()` classmethod that resolves Turkish wire-form display strings to enum members. The parser uses these to populate `Thesis.degree_type` and `Thesis.language`.

```python
from yoktez import ThesisLanguage, ThesisType

ThesisType.from_display("Yüksek Lisans")    # ThesisType.MASTER
ThesisType.from_display("Doktora")          # ThesisType.DOCTORATE
ThesisLanguage.from_display("Türkçe")       # ThesisLanguage.TURKISH
ThesisLanguage.from_display("İngilizce")    # ThesisLanguage.ENGLISH
```

Unknown display strings raise `ValueError`, which the parser layer wraps in `ParseError`. A previously-unseen Turkish degree-type or language label surfaces as a parser break rather than silent data loss.

> [!NOTE]
> Only Turkish display strings are recognized. The library default `Accept-Language: en` does not change what comes off the wire for these fields — `referenceData.meta.type` and `.lang` carry Turkish strings regardless.

## The enums

### `ThesisType` (`IntEnum`)

Academic degree level.

| Member | Value | Turkish display |
| --- | --- | --- |
| `ALL` | `0` | _request-side only_ |
| `MASTER` | `1` | `Yüksek Lisans` |
| `DOCTORATE` | `2` | `Doktora` |
| `SPECIALIZATION_IN_MEDICINE` | `3` | `Tıpta Uzmanlık` |
| `PROFICIENCY_IN_ART` | `4` | `Sanatta Yeterlik` |
| `SPECIALIZATION_IN_DENTISTRY` | `5` | `Diş Hekimliği Uzmanlık` |
| `MINOR_SPECIALIZATION_IN_MEDICINE` | `6` | `Tıpta Yan Dal Uzmanlık` |
| `EXPERTISE_IN_PHARMACY` | `7` | `Eczacılıkta Uzmanlık` |

`ALL` is a request-side sentinel — it never appears on the response side. `from_display("ALL")` raises `ValueError`.

### `ThesisStatus` (`IntEnum`)

Lifecycle status.

| Member | Value |
| --- | --- |
| `ALL` | `0` |
| `PREPARING` | `1` |
| `APPROVED` | `3` |

Wire code `2` is undocumented and omitted from the enum. Pass `2` through `coerce()` if you need it; the library does not block it.

`client.search.detail` defaults to `APPROVED`, not `ALL`. See [search](search.md#why-status-defaults-to-approved).

### `ThesisLanguage` (`IntEnum`)

42 members covering the languages YOK NTC supports. Codes `22-25`, `38`, `40` are gaps preserved at the original integer positions.

```text
ALL=0, TURKISH=1, ENGLISH=2, ARABIC=3, GERMAN=4, FRENCH=5, SPANISH=6,
ITALIAN=7, RUSSIAN=8, POLISH=9, CHINESE=10, KURDISH=11, AZERBAIJANI=12,
BULGARIAN=13, CZECH=14, ROMANIAN=15, DUTCH=16, JAPANESE=17, PERSIAN=18,
GREEK=19, SLOVENIAN=20, MACEDONIAN=21, ADYGHE=26, KYRGYZ=27, BOSNIAN=28,
GEORGIAN=29, KOREAN=30, ARMENIAN=31, ZAZAKI=32, MALAY=33, KAZAKH=34,
UKRAINIAN=35, MONGOLIAN=36, INDONESIAN=37, UZBEK=39, HUNGARIAN=41,
SERBIAN=42, PORTUGUESE=43, ALBANIAN=44, LATVIAN=45, NORWEGIAN=46
```

Turkish display strings (e.g., `"Türkçe"`, `"İngilizce"`) work with `from_display()`.

### `SearchField` (`IntEnum`)

Which field a search should match against.

| Member | Value | Field |
| --- | --- | --- |
| `THESIS_NAME` | `1` | Title |
| `AUTHOR` | `2` | Author |
| `SUPERVISOR` | `3` | Supervisor(s) |
| `SUBJECT` | `4` | Subject(s) |
| `KEYWORD` | `5` | Keyword(s) (curated index) |
| `ABSTRACT` | `6` | Abstract |
| `ALL` | `7` | All fields |

### `AccessType` (`IntEnum`)

Full-text access state.

| Member | Value | Meaning |
| --- | --- | --- |
| `ALL` | `0` | Any access state |
| `AUTHORIZED` | `1` | Has publishing permit; full text accessible |
| `UNAUTHORIZED` | `2` | No publishing permit; full text not accessible |

### `MatchType` (`IntEnum`)

Match mode for advanced search.

| Member | Value |
| --- | --- |
| `EXACT` | `1` |
| `INCLUDES` | `2` |

### `KeywordLanguage` (`IntEnum`)

Language filter for keyword search.

| Member | Value |
| --- | --- |
| `ALL` | `0` |
| `TURKISH` | `1` |
| `ENGLISH` | `2` |

### `AssetStatus` (`IntEnum`)

Asset wire-state classification.

| Member | Value | Meaning |
| --- | --- | --- |
| `AVAILABLE` | `1` | Full text downloadable |
| `UNDER_EMBARGO` | `2` | Restricted until a future date |
| `NO_PERMIT` | `3` | Permanently restricted |
| `PREPARING` | `4` | Upload/processing limbo |

The numeric values are internal — code on this enum branches by member, not value.

### `AdvancedOperator` (`StrEnum`)

Boolean operator for advanced search.

| Member | Value |
| --- | --- |
| `AND` | `"and"` |
| `OR` | `"or"` |
| `NOT` | `"not"` |

### `UniversitySource` (`StrEnum`)

Endpoint scope for university listings.

| Member | Value |
| --- | --- |
| `TR` | `"TR"` |
| `INT` | `"INT"` |

### `KeywordGroup` (`StrEnum`)

Academic group for keyword filtering.

| Member | Value |
| --- | --- |
| `SCIENCE` | `"F"` |
| `SOCIAL_SCIENCES` | `"S"` |
| `MEDICINE` | `"T"` |

The single-letter values are upstream codes (`F` for "Fen", `S` for "Sosyal", `T` for "Tıp").

## When to use which form

- **Typed code (apps, libraries, anything with type checks):** pass enum members.
- **Quick scripts and notebooks:** pass strings (member names or wire forms).
- **Wire-fidelity replays:** pass raw integers / strings; the library doesn't second-guess them.
- **Persisted values across versions:** persist the wire form (`ThesisType(t).value`) and pass it back as `int` / `str`. Member names can be renamed in a future version; wire codes are fixed.

## Internal helpers

The module exposes `coerce`, `coerce_int_enum`, and `coerce_str_enum` from `yoktez.enums`. Only `coerce` is normally needed; the specialized helpers are public for advanced extensibility but are not re-exported from the package root.

The lookup tables `_THESIS_TYPE_BY_DISPLAY` and `_THESIS_LANGUAGE_BY_DISPLAY` are private and may be reorganized without notice. Use `from_display()` instead of touching them.

## See also

- [Search](search.md) — every enum parameter on the search surface.
- [Data models](data-models.md) — `Thesis.degree_type` and `Thesis.language` carry resolved enum members.
- [Errors](errors.md) — `ParseError` wraps `ValueError` from `from_display()`.
