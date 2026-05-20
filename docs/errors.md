# Errors

`yoktez` has a small exception hierarchy for library-side failures and re-raises `httpx` errors unwrapped for transport / status failures.

## Hierarchy

```text
Exception
├── YoktezError                     — base; never raised directly
│   ├── ParseError                  — wire-shape drift; parser can't proceed
│   └── ThesisUnavailableError      — base for download-state exceptions; never raised directly
│       ├── ThesisUnderEmbargoError  — has `restricted_until: date`
│       ├── ThesisNoPermitError
│       └── ThesisPreparingError

httpx.HTTPError                     — re-raised unwrapped
├── httpx.RequestError
│   ├── httpx.TimeoutException
│   ├── httpx.NetworkError
│   ├── httpx.ProtocolError
│   └── httpx.TooManyRedirects
└── httpx.HTTPStatusError
```

Plus `ValueError` for client-side input validation, raised eagerly before any wire request.

## `YoktezError`

```python
class YoktezError(Exception): ...
```

Base for every library-raised exception. Catch `YoktezError` to handle "anything the library knows about" without catching unrelated stdlib errors.

```python
from yoktez import Client, YoktezError

with Client() as client:
    try:
        results = client.search.simple("...")
    except YoktezError as exc:
        log.exception("yoktez raised %s", type(exc).__name__)
```

The class itself is never raised; only its subclasses are.

## `ParseError`

```python
class ParseError(YoktezError): ...
```

The expected HTML or JSON shape is absent. Indicates the upstream layout changed materially. Specifically raised when:

- The `referenceData` script block is missing from a search result page.
- The `referenceData` JSON is malformed (not parseable after the trailing-comma strip).
- A search result card has no matching `referenceData` entry by `data-index`.
- A `from_display()` lookup fails (a previously-unseen Turkish degree-type or language label).
- The assets HTML fragment matches none of the four known shapes.

```python
from yoktez import Client, ParseError

with Client() as client:
    try:
        results = client.search.simple("...")
    except ParseError as exc:
        log.error("YOK NTC wire shape changed: %s", exc)
        # Pin the dependency to a known-good version, file a bug, or apply a workaround.
```

A `ParseError` almost always means the library needs an update. Report it via [`github.com/ozefe/yoktez/issues`](https://github.com/ozefe/yoktez/issues) — please include the raw response body if you can capture it.

## `ThesisUnavailableError` and subclasses

```python
class ThesisUnavailableError(YoktezError):
    info_message: str
    def __init__(self, *, info_message: str) -> None: ...

class ThesisUnderEmbargoError(ThesisUnavailableError):
    restricted_until: dt.date
    def __init__(self, *, info_message: str, restricted_until: dt.date) -> None: ...

class ThesisNoPermitError(ThesisUnavailableError): ...
class ThesisPreparingError(ThesisUnavailableError): ...
```

> [!IMPORTANT]
> The library does **not** currently raise these automatically. `client.assets.get(...)` returns a `ThesisAssets` regardless of state; your code branches on `.status`. The exception classes exist for callers who prefer exception-driven control flow; wrap the call yourself if you want that pattern. See [assets](assets.md#thesisunavailableerror-related-but-not-raised-here).

When you do raise them yourself:

```python
from yoktez import (
    AssetStatus, Client,
    ThesisNoPermitError, ThesisPreparingError, ThesisUnderEmbargoError,
)

def fetch_or_raise(client: Client, thesis):
    assets = client.assets.get(thesis)
    match assets.status:
        case AssetStatus.AVAILABLE:
            return assets
        case AssetStatus.UNDER_EMBARGO:
            raise ThesisUnderEmbargoError(
                info_message=assets.info_message,
                restricted_until=assets.restricted_until,
            )
        case AssetStatus.NO_PERMIT:
            raise ThesisNoPermitError(info_message=assets.info_message)
        case AssetStatus.PREPARING:
            raise ThesisPreparingError(info_message=assets.info_message)
```

## `httpx` errors pass through unwrapped

The library does not wrap `httpx` exceptions. They surface to your code with their full context (`exc.request`, `exc.response`, etc.).

```python
import httpx
from yoktez import Client

with Client(timeout=1.0) as client:
    try:
        client.search.simple("...")
    except httpx.TimeoutException as exc:
        # exc.request is populated; exc.response may or may not be
        log.warning("timeout against %s", exc.request.url)
    except httpx.HTTPStatusError as exc:
        log.error("HTTP %d at %s", exc.response.status_code, exc.request.url)
```

This is intentional: wrapping `httpx` errors in a library-specific class would lose detail (no `.response` access) and add maintenance burden whenever httpx's hierarchy evolves.

The full hierarchy:

```text
httpx.HTTPError
├── httpx.RequestError (carries .request)
│   ├── httpx.TransportError
│   │   ├── httpx.TimeoutException
│   │   │   ├── httpx.ConnectTimeout
│   │   │   ├── httpx.ReadTimeout
│   │   │   ├── httpx.WriteTimeout
│   │   │   └── httpx.PoolTimeout
│   │   ├── httpx.NetworkError
│   │   │   ├── httpx.ConnectError
│   │   │   ├── httpx.ReadError
│   │   │   ├── httpx.WriteError
│   │   │   └── httpx.CloseError
│   │   ├── httpx.ProtocolError
│   │   ├── httpx.ProxyError
│   │   └── httpx.UnsupportedProtocol
│   ├── httpx.DecodingError
│   └── httpx.TooManyRedirects
└── httpx.HTTPStatusError (carries .request and .response)
```

`httpx.HTTPStatusError` is raised by the assets downloader (which calls `response.raise_for_status()`). Search, metadata, and lookups do not call `raise_for_status` themselves — they parse whatever body comes back, which can mean a `ParseError` on a 5xx HTML error page.

> [!TIP]
> If you want consistent HTTP-status handling across all four sub-services, install an httpx event hook:
>
> ```python
> import httpx
> from yoktez import Client
>
> def _raise_on_4xx_5xx(response: httpx.Response) -> None:
>     response.raise_for_status()
>
> http = httpx.Client(
>     base_url="https://tez.yok.gov.tr/UlusalTezMerkezi",
>     follow_redirects=True,
>     event_hooks={"response": [_raise_on_4xx_5xx]},
> )
> with Client(http_client=http) as client:
>     ...
> ```

## `ValueError` — client-side input validation

Raised eagerly, before any wire request, for invalid inputs:

```python
client.search.detail(year_min=1899)
# ValueError: year_min must be >= 1900; got 1899

client.search.detail(year_min=2024, year_max=2020)
# ValueError: year_min (2024) must be <= year_max (2020)

client.metadata.get(thesis_with_no_thesis_no)
# ValueError: ... has thesis_no=None; pass an explicit (registration_no, thesis_no) tuple instead

client.assets.get(thesis_with_no_thesis_no)
# ValueError: ... has thesis_no=None; pass an explicit (registration_no, thesis_no) tuple instead

client.lookups.institutes(university_with_no_yoksis_id)
# ValueError: ... has yoksis_id=None; need non-None value to drive hierarchical lookups

Client(retries=-1)
# ValueError: Retries must be >= 0

coerce(KeywordGroup, "bogus")
# ValueError: 'bogus' is not a member of KeywordGroup
```

These are `ValueError` (stdlib), not `YoktezError`. Catch them when the input might come from untrusted code:

```python
try:
    results = client.search.detail(year_min=user_input)
except ValueError as exc:
    raise BadRequest(str(exc)) from exc
```

## `TypeError`

```python
coerce(ThesisType, 1.5)
# TypeError: Cannot coerce float to ThesisType
```

Raised by `coerce()` when given something that's neither `Enum`, `int`, nor `str`. Rare; usually indicates a real bug at the call site.

## Recovery patterns

### Retry transient transport errors

```python
import time
import httpx
from yoktez import Client

def with_retry(call, attempts=3, base_delay=0.5):
    for attempt in range(attempts):
        try:
            return call()
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt == attempts - 1:
                raise
            time.sleep(base_delay * (2**attempt))

with Client() as client:
    results = with_retry(lambda: client.search.simple("..."))
```

The library's built-in retry (`HTTPTransport(retries=3)`) only retries `ConnectError` / `ConnectTimeout`. Anything else needs an external loop.

### Distinguish wire drift from bad input

```python
from yoktez import Client, ParseError

with Client() as client:
    try:
        results = client.search.simple("...")
    except ValueError:
        # Bad input — your bug or the user's
        raise
    except ParseError:
        # Wire shape changed — file a bug, pin the version
        raise
    except httpx.HTTPError:
        # Transport / status — retry or fail gracefully
        raise
```

The three layers correspond to: client-side bug, library-side bug, environmental issue.

### Aggregating per-thesis failures in a batch

```python
results = client.search.simple("yapay zeka")
failures = []
for thesis in results[:50]:
    try:
        meta = client.metadata.get(thesis)
        # ...
    except (ValueError, httpx.HTTPError, ParseError) as exc:
        failures.append((thesis.registration_no, exc))

log.info("processed %d; %d failures", 50 - len(failures), len(failures))
```

Per-iteration `try` keeps a single bad card from killing the batch.

## See also

- [Assets](assets.md) — state branching on `AssetStatus`.
- [Client](client.md) — `Client(retries=0)` to disable connection retries.
- [Logging](logging.md) — `yoktez.search` logs a WARNING when the advisory banner is present but unparsable (sub-`ParseError` wire drift).
