# Design notes

This page records the architectural choices behind `yoktez`. It answers _why_ decisions were made; the code answers _what_ they are. Read this if you are extending the library, considering a fork, or trying to predict how a future change will land.

## Synchronous-only API

The library exposes no `async def`, no `asyncio`, no `httpx.AsyncClient`. Reasons:

- The YOK NTC service is HTTP/1.1 over a small number of endpoints. The cost of a sync request — connection pool acquire, blocking write, blocking read — is dominated by upstream latency, not by the Python event loop.
- An async surface doubles the API: every method needs an `async` counterpart, every test needs an async variant, every docstring needs to address both.
- Async libraries are easy to call from sync code via `asyncio.run(...)`. Sync libraries are easy to call from async code via `asyncio.to_thread(...)`. The cost is symmetric, but the maintenance burden of a sync codebase is lower.
- Concurrency strategy is a caller concern. The library standardizes on "one `Client` per thread" and provides `examples/multithreaded_pool.py` as a reference.

If async is critical for your use case, wrap the sync calls in `asyncio.to_thread`. See [concurrency](concurrency.md).

## Frozen, slotted dataclasses for value objects

Every returned record is `@dataclass(frozen=True, slots=True)`.

- **stdlib-only:** no Pydantic (Rust core, validation we don't need against trusted upstream), no `attrs` (no decisive advantage on 3.14+).
- **Immutable:** records can't be accidentally mutated after construction. Pyright catches `thesis.title = "..."` at compile time; Python catches it at runtime as `FrozenInstanceError`.
- **Hashable when possible:** any record with hashable fields gets `__hash__` for free. Use as set / dict keys.
- **Slotted:** smaller memory footprint, faster attribute access. No `__dict__` per instance.
- **Fast:** dataclass construction is competitive with hand-written `__init__` since 3.11+.

The one exception is `ThesisMetadata`, whose `list[Bilingual]` field makes the auto-generated `__hash__` undefined. Use the `(registration_no, thesis_no)` tuple as a key when you need one.

## Coerce-on-input enum handling

Enum-shaped parameters accept three forms: the typed `Enum` member, its `name` (member identifier), or its raw `value` (wire code). `int` values for `IntEnum` targets pass through unchanged when they don't match a known member.

Reasons:

- **Type-safe app code:** `client.search.simple("...", degree_type=ThesisType.MASTER)` is the recommended form. Pyright catches typos and renames.
- **Ergonomic scripts:** `client.search.simple("...", degree_type="MASTER")` works without importing the enum. Useful in notebooks, REPLs, ad-hoc tools.
- **Wire-stable:** `client.search.simple("...", degree_type=1)` reproduces an exact wire payload. Useful when porting curl commands.
- **Forward-compatible:** unknown ints pass through, so the library tolerates new YOK NTC codes without a release.

`StrEnum` strings are validated (not passed through) because the value sets are tiny and a typo would silently produce a broken request.

See [enums](enums.md) for the full coercion contract.

## Two-step asset download

`client.assets.get(...)` returns a `ThesisAssets` with `status` and (when available) `pdf_key` / `appendix_key`. Actually streaming the bytes requires a second call to `download_pdf` / `download_appendix`.

Reasons:

- Honest to the underlying wire: the YOK NTC UI shows status first, downloads on click.
- Lets callers inspect embargo dates, appendix availability, and info messages before committing to a stream.
- Keeps each method small and testable.
- The download key carries an implicit session affinity, so the two-step pattern matches "session lifetime" semantics rather than "one shot" semantics.

A single-method API (`download_or_raise(...)`) is easy to build on top; the reverse (split a single method into status + download) is hard.

## Hierarchical logger naming

Loggers are named `yoktez.<concern>`:

- `yoktez.http` — high-volume request log (one DEBUG per response).
- `yoktez.search` — wire-shape WARNINGs.
- `yoktez.lookups` — wire-shape WARNINGs.
- `yoktez.assets` — DEBUG when a download completes.

Operators can silence the high-volume DEBUG channel (`yoktez.http`) without losing the rare WARNINGs (`yoktez.search`). A single `logging.getLogger("yoktez").setLevel(...)` still catches all children via Python's parent propagation. See [logging](logging.md).

## `src/yoktez/` layout

The package lives at `src/yoktez/` rather than `yoktez/` at the project root. Reasons:

- Prevents accidental shadowing of the package during tests. Without `src/`, running `pytest` from the repo root imports `yoktez` from the source tree instead of the installed wheel — usually fine, but a footgun.
- Standard layout for modern Python libraries (PyPA recommendation).
- `pyproject.toml` declares `packages = ["src/yoktez"]` and `pythonpath = ["src"]`.

## `hatchling` build backend

Pure-Python, zero build dependencies beyond `hatchling` itself, supports PEP 621 metadata in `pyproject.toml`. No reason to reach for `setuptools` here.

## Sub-packages by concern

Each public sub-service (`search`, `metadata`, `assets`, `lookups`) lives in its own sub-package with three files:

```text
src/yoktez/search/
├── __init__.py    — SearchService (the sub-package IS the service namespace)
├── models.py      — Thesis, SearchResults
└── _parser.py     — pure text -> models
```

Reasons:

- Each concern owns its parser, models, and service. Easier to evolve independently than a flat layout.
- The sub-package's `__init__.py` _is_ the service module. No separate `service.py` file. Easier imports.
- The `_parser.py` modules are private (`_`-prefixed) but accessed by tests via the qualified name. Pyright `strict` mode tolerates this; the underscore signals "not part of the public API" without hiding it from tooling.

## `coerce`, `default_transport`, and `Client.http_client` are public

These three names do not start with `_`. They are not re-exported from the package root but are addressable from `yoktez.enums`, `yoktez._http`, and the `Client` instance.

Reasons:

- Pyright `strict` flags `_private` symbols imported by tests as `reportPrivateUsage`. Tests legitimately need these.
- Real users have legitimate use cases: swap transports, introspect the underlying httpx client, write custom coercion code.
- None are re-exported at the package root, so the top-level public surface stays small.

The naming convention: leading `_` means "private from the package root" not "private absolutely". Underscore-prefixed module names (`_http`, `_endpoints`, `_helpers`, `_parser`) signal stability is not guaranteed; non-underscore public names within them follow standard semver.

## `parse_eklecikar_list` uses regex over BeautifulSoup

The legacy `eklecikar()` HTML fragments can reach tens of megabytes for the keyword catalog dump (~88,000 anchors). BS4 + lxml DOM construction is two orders of magnitude slower than a single compiled regex pass for data that only lives in `href` attributes.

The regex handles three edge cases:

1. Bare-quoted `'NAME'` vs entity-encoded `&#39;NAME&#39;` boundary styles.
2. JS-escaped apostrophes inside names (`O\'Brien` rendered as `O\&#39;Brien`).
3. The non-greedy `.*?` is anchored by a `(?<!\\)` lookbehind on the closing quote, so escaped quotes don't prematurely terminate the match.

`parse_radio_input_list` keeps BS4 — the modern AJAX endpoints emit small fragments where DOM construction overhead is irrelevant and the code is more readable.

## `from_display()` classmethods over a single coerce-everything

`ThesisType.from_display(name)` and `ThesisLanguage.from_display(name)` resolve Turkish wire-form strings to enum members. They are response-side counterparts to `coerce(enum_cls, value)` (request-side).

Reasons:

- Symmetric to `coerce`: request-side coercion and response-side resolution are distinct concepts.
- The display-name tables are private to each enum (`_THESIS_TYPE_BY_DISPLAY`, etc.) — clean encapsulation.
- Turkish keys only: that's what comes off the wire. English keys are documentation prose, not wire data.
- Unknown strings raise `ValueError`, which the parser layer wraps in `ParseError`. Wire-shape drift surfaces at the parser, not as a corrupted enum value silently propagating.

## `HTTPTransport(retries=3)` only — no status-code retries

The library does not retry on 5xx, `ReadTimeout`, or any other status-code-aware retry policy. `HTTPTransport(retries=3)` retries `ConnectError` / `ConnectTimeout` at the TCP layer only.

Reasons:

- Keeps the failure surface explicit. Status-code retries are easy to wrap externally with smarter policy (exponential backoff, jitter, retry budget).
- The library doesn't know your retry budget. A library-side retry can compound your application's own retries.
- Operational simplicity. The library does one thing.

If real-world usage shows transient 5xx is hurting batch reliability, this could be revisited. See [future directions](#future-directions).

## Retry breadcrumbs omitted from HTTP DEBUG logging

`httpx.HTTPTransport(retries=3)` retries connection errors inside the transport with no exposed hook surface. Logging retry attempts would require wrapping a custom `BaseTransport` purely for visibility, which would broaden the testing surface (the `MockTransport`-based test pattern bypasses retries entirely) for marginal operator value. The existing response-hook DEBUG already proves each request reached the wire.

## Search WARNING gated on `"warning-text" in html`

An unconditional WARNING on every `_extract_total` miss would flood operators with non-degradation noise (empty result pages legitimately omit the `.warning-text` advisory block). The substring gate distinguishes "block missing" (legitimate, silent) from "block present but unparsable" (real wire-shape drift, worth logging).

## Logging is not a tested surface

The DEBUG / WARNING breadcrumbs are best-effort observability for operators, not part of the library's contract. The underlying parse / fetch / stream is already covered by surrounding tests; asserting on log records would test the act of logging, not behavior. Logging instrumentation can be added or removed without test churn.

## Generic `_memoize[T]` helper

`LookupsService._memoize[T](key, fetch)` centralizes the cache contract: `(method_name, *normalized_primitive_args)` keys, store-on-miss, cast-back-to-`T` on hit. Every cached lookup method is a one-line call to `_memoize`.

Reasons:

- Eliminates per-method cache boilerplate.
- The cache dict is shared across methods — one `dict[tuple[object, ...], object]` for the whole `LookupsService`.
- Keys are tuples of primitives, so `==` and `hash()` are well-defined regardless of method argument types.
- `cast("T", value)` re-types the cached `object` to the callable's declared return on the way out. Keeps `pyright --strict` happy without leaking generics into the dict definition.

## `resolve_yoksis_id(obj)` lives at the package root

The helper resolves `University | Institute | str` to a YOKSIS ID string and raises `ValueError` when a legacy-source model carries `yoksis_id=None`.

It lives at `src/yoktez/_helpers.py` rather than inside `lookups` or `search` because both sub-services import it. A single home prevents the two copies from drifting; pyright `strict` flags cross-package private-name imports, so the file is module-level rather than scoped to one sub-package.

## `Affiliation.parse` collapses trailing empty tiers

`"U / I /"` parses as 2 tiers, not 3 with a blank `institute`. This means the trailing-slash and no-trailing-slash forms round-trip identically.

When more than four tiers appear (defensive; not observed in practice), surplus folds back into `section` joined by `" / "` rather than raising. Preserves data rather than dropping it.

## `parse_search_page` strips trailing JSON comma via `re.sub`

YOK NTC's `referenceData` block emits a trailing comma before the closing `}` (valid JS, invalid JSON). The library strips it before `json.loads` via `re.sub(r",(\s*})", r"\1", text)`.

Why not `str.strip(",")`? The comma is _inside_ the JSON object, immediately before the final `}`. `str.strip` operates on the string's edges and can't reach it. The regex says exactly what we mean ("drop a comma immediately before the closing brace") and survives arbitrary whitespace.

## Live tests opt-in via marker filter

`pyproject.toml` sets `addopts = [..., "-m", "not live", ...]`. The default `pytest` invocation deselects `@pytest.mark.live` tests; an explicit `pytest -m live` overrides (the last `-m` wins).

Reasons:

- pytest's built-in marker filtering covers the requirement.
- A `conftest.py` hook would duplicate behavior pytest already ships.
- Live tests prove the wire shape hasn't drifted from what the parser expects; they don't exhaustively cover feature behavior.

## Future directions

Tracked in `.dev/PROJECT-SPEC.md`; here is the shortlist:

- **CLI binary (`yoktez-cli`)** — separate package depending on `yoktez`. Pursue once the API has stabilized and at least one external script demands it.
- **Statistics endpoints (`IstatistikiBilgiler`)** — by-university, by-year, by-subject, by-type. Add a `client.statistics` sub-service when needed.
- **Export adapters** — JSON, CSV, SQLite/FTS5, Parquet writers. Likely an extras-installed sub-package or a sibling package.
- **Language detection on titles / abstracts** — opt-in field annotators. Pursue when at least one researcher flags metadata-language errors as a real problem.
- **Robust retry on 5xx and `ReadTimeout`** — if real-world usage shows transient failures harm batch reliability.

## See also

- [`.dev/PROJECT-SPEC.md`](../.dev/PROJECT-SPEC.md) — full project spec, including the decision log this page summarizes.
- [`.github/CONTRIBUTING.md`](../.github/CONTRIBUTING.md) — workflow and code-style expectations.
