# The `Client` class

`yoktez.Client` is the single public entry point. It owns an `httpx.Client`, exposes four lazily-instantiated sub-services (`search`, `metadata`, `assets`, `lookups`), and is a context manager.

## Construction

```python
from yoktez import Client

with Client() as client:
    ...
```

All keyword arguments are optional. The defaults are tuned for the YOK NTC service.

### Signature

```python
Client(
    *,
    timeout: float = 30.0,
    retries: int = 3,
    user_agent: str = DEFAULT_USER_AGENT,
    extra_headers: Mapping[str, str] | None = None,
    http_client: httpx.Client | None = None,
)
```

| Parameter | Default | Effect |
| --- | --- | --- |
| `timeout` | `30.0` seconds | Per-operation `httpx.Client` timeout. Applies to connect, read, write, and pool acquisition. |
| `retries` | `3` | Connection-level retries on `ConnectError` / `ConnectTimeout`. **Not** status-code retries. |
| `user_agent` | Chrome 134 UA | Browser-style UA. YOK NTC returns different responses to obvious scrapers; the default is what production traffic uses. |
| `extra_headers` | `None` | Extra headers merged on top of the defaults. Keys here win on conflict. |
| `http_client` | `None` | Inject a fully built `httpx.Client`. The constructor uses it as-is; the four other parameters above are ignored. |

> [!IMPORTANT]
> All parameters are keyword-only. There are no positional arguments.

## Usage patterns

### As a context manager (the recommended path)

```python
with Client() as client:
    results = client.search.simple("yapay zeka")
    # do work; client.close() runs on block exit
```

This is the canonical pattern. The `httpx.Client`'s connection pool is released deterministically when the `with` block exits, regardless of how the block exited (normal return, exception, `break`, …).

### Manual lifecycle

```python
client = Client()
try:
    client.search.simple("yapay zeka")
finally:
    client.close()
```

Use this when the `Client`'s scope doesn't map cleanly to a single `with` block — e.g., when it is stored on a long-lived service object that has its own teardown.

`client.close()` is idempotent: calling it multiple times is safe and a no-op after the first.

### Injecting an `httpx.Client`

```python
import httpx
from yoktez import Client

http = httpx.Client(timeout=60.0, follow_redirects=True, proxy="http://proxy:8080")
try:
    with Client(http_client=http) as client:
        client.search.simple("yapay zeka")
finally:
    http.close()
```

When you pass `http_client=`, ownership of the underlying client stays with you. `Client.close()` and `__exit__` become no-ops for the HTTP layer; you are responsible for `http.close()`.

> [!CAUTION]
> The injected `httpx.Client` must have `follow_redirects=True`. YOK NTC issues a `302` from `SearchTez` to `tezSorguSonucYeni.jsp`; without redirect following, every search returns an empty body.

Use injection when you need:

- A specific proxy or mounts configuration.
- Custom event hooks beyond what `yoktez` installs.
- Shared connection pooling across libraries.
- A `MockTransport` for tests (this is what the library's own test suite does).

## Sub-services

Four sub-services hang off `Client`. Each is lazily constructed on first attribute access and memoized for the `Client`'s lifetime.

| Attribute | Type | Documentation |
| --- | --- | --- |
| `client.search` | `SearchService` | [search](search.md) |
| `client.metadata` | `MetadataService` | [metadata](metadata.md) |
| `client.assets` | `AssetsService` | [assets](assets.md) |
| `client.lookups` | `LookupsService` | [lookups](lookups.md) |

Lazy construction means importing `yoktez` and instantiating `Client` does not pay the cost of building services you never use. The first `client.search` access constructs `SearchService(self)`; subsequent accesses return the same instance.

## Public attributes

- `client.http_client: httpx.Client` — the underlying HTTP client, owned or injected. Exposed for advanced introspection (e.g., reading cookies, inspecting the connection pool). Don't close it directly; let the `Client` handle that unless you injected it.
- `client.search`, `client.metadata`, `client.assets`, `client.lookups` — the four sub-services.

## Internal state to leave alone

- `client._search`, `client._metadata`, `client._assets`, `client._lookups` — lazy caches.
- `client._owns_http` — flips the close behavior.
- `client._closed` — guards `close()` from running twice.

These attributes are not part of the public API and will change without notice. Inspect them in a debugger; don't read or write them from production code.

## Configuration cookbook

### Slow network, want a longer timeout

```python
with Client(timeout=120.0) as client:
    ...
```

### Behind a corporate proxy that strips the default UA

```python
with Client(user_agent="curl/8.0") as client:
    ...
```

> [!NOTE]
> Some HTTP middleboxes match on UA. Switching to a generic UA can either fix or break the request, depending on the middlebox.

### Adding a `Referer` header

```python
with Client(extra_headers={"referer": "https://example.org"}) as client:
    ...
```

`extra_headers` keys win over the defaults. Sending `extra_headers={"user-agent": "..."}` overrides the `user_agent` argument.

### Disabling retries entirely

```python
with Client(retries=0) as client:
    ...
```

A flake-prone network might prefer fewer retries plus an external retry loop with smarter behavior than `httpx.HTTPTransport`.

### Passing a `retries=-1` (don't)

```python
Client(retries=-1)  # raises ValueError("Retries must be >= 0")
```

The constructor delegates to `build_http_client`, which validates `retries`. This is checked at construction, before any network I/O.

## Common mistakes

### Sharing a `Client` across threads

```python
client = Client()
# Thread A and Thread B both call client.search.simple(...)  # bad
```

`Client` is _not_ thread-safe. The underlying `httpx.Client` has its own thread-safety story, but `LookupsService` holds a non-locked memoization dict, and the lazy sub-service properties race. Use one `Client` per thread — see [concurrency](concurrency.md) for the canonical pattern.

### Forgetting `with`

```python
client = Client()
client.search.simple("yapay zeka")
# script ends; connection pool held until GC eventually frees the httpx client
```

The pool leaks until garbage collection runs the `httpx.Client.__del__` finalizer. On short-lived scripts this is harmless; on long-lived services it accumulates file descriptors. Always use `with` or call `close()` explicitly.

### Calling sub-service methods after `close()`

```python
client = Client()
client.close()
client.search.simple("...")  # raises httpx.RuntimeError("Cannot send a request, as the client has been closed.")
```

The `Client` doesn't intercept this; `httpx.Client` does. The error is clear, but the call site might be far from the `close()`.

## See also

- [Concurrency](concurrency.md) — when and how to share, pool, or recycle `Client` instances.
- [Logging](logging.md) — the `yoktez.http` logger emits one DEBUG record per request.
- [Errors](errors.md) — what gets raised when the network or the parser fails.
