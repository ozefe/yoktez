# yoktez documentation

Typed Python client for the [National Thesis Center of Turkey](https://tez.yok.gov.tr/UlusalTezMerkezi/) (YOK NTC). This documentation set is the reference and guide for the library; the top-level [`README.md`](../README.md) is the marketing/quickstart surface.

## Map

- [Getting started](getting-started.md) — install, first script, what to expect.
- [The `Client` class](client.md) — construction, configuration, HTTP injection, cleanup.
- [Search](search.md) — `simple`, `advanced`, `detail`, `recent`; filters, slicing, totals.
- [Metadata](metadata.md) — per-thesis structured detail, citations, affiliations, bilingual fields.
- [Assets](assets.md) — the two-step download flow, status branches, streaming to disk or memory.
- [Lookups](lookups.md) — universities, institutes, divisions, subjects, keywords, departments, sections; memoization.
- [Data models](data-models.md) — every returned dataclass, its fields, and when each field is `None`.
- [Enums](enums.md) — every enum, valid wire codes, the `coerce()` helper, the `from_display()` classmethods.
- [Errors](errors.md) — the `YoktezError` hierarchy, `httpx` error pass-through, recovery patterns.
- [Concurrency](concurrency.md) — single-thread design, one-`Client`-per-thread pattern, thread-pool recipes.
- [Logging](logging.md) — logger names, what each emits, how to silence the noisy ones.
- [Design notes](design.md) — why sync-only, why frozen dataclasses, why coerce-on-input, etc.
- [Cookbook](cookbook.md) — short recipes for the most common tasks.

## Reading order

If you are evaluating the library, skim [getting started](getting-started.md) and [search](search.md), then jump into [cookbook](cookbook.md).

If you are integrating it into a larger app, read [the `Client` class](client.md), [concurrency](concurrency.md), and [errors](errors.md) before writing any code.

If you are extending it (patching a parser, adding a wire variant), start from [design notes](design.md), then the relevant sub-package page.

## Conventions

- Code examples assume `from yoktez import Client` and a Python 3.14+ interpreter.
- Every example uses `with Client() as client:` so the underlying connection pool is always released.
- "YOK NTC" refers to the upstream service. "yoktez" refers to the library.
- File paths in cross-references are relative to the repository root (`src/yoktez/client.py`).
