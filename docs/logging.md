# Logging

`yoktez` emits structured log records via the standard `logging` module, organized in a hierarchy under the `yoktez` namespace. No handlers are attached by default — the application configures them.

## Logger names

| Logger | Records emitted |
| --- | --- |
| `yoktez` | Parent of all sub-loggers; never emits directly. |
| `yoktez.http` | One DEBUG per HTTP request via an httpx response hook: `"GET /UlusalTezMerkezi/... -> 200"`. |
| `yoktez.search` | WARNING when the advisory banner is present but the total regex doesn't match (suspected wire drift). |
| `yoktez.lookups` | WARNING when a radio-input row drops `ad` or `kod` attributes. |
| `yoktez.assets` | DEBUG when a download completes, including the byte count. |

The hierarchical naming lets you tune each channel independently. Silence the high-volume `yoktez.http` DEBUG without muting the rarer parser WARNINGs:

```python
import logging
logging.getLogger("yoktez.http").setLevel(logging.WARNING)
```

Or catch every child with a single setting:

```python
logging.getLogger("yoktez").setLevel(logging.DEBUG)
```

Python's parent propagation handles the cascade.

## Default behavior

The library attaches **no handlers**. Without configuration, log records are emitted but go to the default `logging` last-resort handler, which writes WARNING and above to stderr.

```python
import logging
from yoktez import Client

logging.basicConfig(level=logging.DEBUG)

with Client() as client:
    client.search.simple("yapay zeka")
# DEBUG    yoktez.http    POST https://tez.yok.gov.tr/UlusalTezMerkezi/SearchTez -> 302
# DEBUG    yoktez.http    GET  https://tez.yok.gov.tr/UlusalTezMerkezi/tezSorguSonucYeni.jsp -> 200
```

## What each channel emits

### `yoktez.http`

```text
DEBUG yoktez.http GET https://tez.yok.gov.tr/UlusalTezMerkezi/SearchTez -> 200
DEBUG yoktez.http POST https://tez.yok.gov.tr/UlusalTezMerkezi/SearchTez -> 302
```

One record per response. Fired from an httpx response hook on the underlying `httpx.Client`. The hook runs before the body is read, so the body is not in scope.

> [!NOTE]
> Connection-level retries (`HTTPTransport(retries=3)`) happen inside the transport and do not surface as separate log records. You see one record per "logical request" regardless of how many TCP attempts httpx made to satisfy it.

### `yoktez.search`

```text
WARNING yoktez.search result-total advisory block present but regex did not match; wire shape may have changed
```

Fired when the parser sees the `.warning-text` advisory marker but can't extract the numeric total. Distinguishes wire drift from legitimate empty pages (which omit the block entirely and don't log anything).

### `yoktez.lookups`

```text
WARNING yoktez.lookups skipping radio input with missing ad/kod for name_attr='selected_institute'
```

Fired when a radio input drops the `ad` or `kod` attribute. A wire-shape drift that silently shrinks the result list — operators see the WARNING and can investigate.

### `yoktez.assets`

```text
DEBUG yoktez.assets streamed 524288 bytes to /tmp/thesis.pdf
DEBUG yoktez.assets streamed 524288 bytes to <BytesIO>
```

Fired after each successful download. Reports byte count and destination. The destination is the file path (string) when `dest` was a `Path | str`, or the type name in angle brackets for a file-like.

## Wiring patterns

### Production: log to a file at INFO

```python
import logging
import logging.handlers

handler = logging.handlers.RotatingFileHandler(
    "/var/log/myapp/yoktez.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
)
handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))

yt_logger = logging.getLogger("yoktez")
yt_logger.addHandler(handler)
yt_logger.setLevel(logging.INFO)
```

INFO + WARNING captures parser-drift warnings without the per-request DEBUG noise.

### Debugging a single batch run

```python
import logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(name)s %(message)s")
```

Full DEBUG output. Useful to see every request firing in order.

### Silencing httpx itself

httpx has its own DEBUG channel under `httpx` and `httpcore`. They are noisy.

```python
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
```

`yoktez.http` is independent of these and stays at whatever you configure it to.

### Structured logs

The standard `logging.Formatter` produces text records. For JSON / structured output, use a library like `structlog` or write a simple JSON formatter:

```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        })

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.getLogger("yoktez").addHandler(handler)
```

## Format strings use `%`-style lazy formatting

The library uses `%`-style formatting for log records:

```python
_logger.debug("%s %s -> %d", request.method, request.url, response.status_code)
```

This is the documented pattern — arguments are only formatted when the record is actually emitted. Don't fret about `%s` vs f-strings in log calls; the library follows the stdlib convention.

## What the library does **not** log

- **Request bodies** — form-encoded search bodies are not logged. They can be long and may contain PII (author / supervisor names if you used those filters).
- **Response bodies** — never logged. They can be megabytes.
- **Download keys** — appear only on the URL path component, which is logged for the request. If this concerns you, set `yoktez.http` to WARNING.
- **Connection retries inside the transport** — httpx does not expose a clean hook for these. See the [decision log entry](design.md#retry-breadcrumbs-omitted-from-http-debug-logging).

## See also

- [Errors](errors.md) — error reporting is independent of logging; library exceptions propagate as exceptions, not log records.
- [Design notes](design.md) — why logging is _not_ a tested surface.
