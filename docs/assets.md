# Assets

`client.assets` resolves the per-thesis download keys and streams the bytes. The flow is two-step by design: a status fetch first, then an optional download.

## The three methods

```python
client.assets.get(thesis_or_keys) -> ThesisAssets
client.assets.download_pdf(key, dest, *, chunk_size=65536) -> None
client.assets.download_appendix(key, dest, *, chunk_size=65536) -> None
```

`get` is cheap (one GET, a small HTML fragment). `download_*` streams arbitrarily large bytes through the response.

## Why two steps

A single-call download would conflate four very different situations:

| State | Wire signal | Library state |
| --- | --- | --- |
| Full text available | `<a href='TezGoster?key=...'>` | `AssetStatus.AVAILABLE`, `pdf_key` populated |
| Under embargo | `<span class='pdf-info-msg'>...DD.MM.YYYY...</span>` | `AssetStatus.UNDER_EMBARGO`, `restricted_until` populated |
| No publishing permit | `<span class='pdf-info-msg'>...no date...</span>` | `AssetStatus.NO_PERMIT` |
| Still being prepared | `<div class='pdf-container'>...prose...</div>` | `AssetStatus.PREPARING` |

The two-step flow lets your code inspect status and embargo dates before committing to a stream, and matches the natural shape of the upstream UI ("see availability, click to download").

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

| Field | Populated when |
| --- | --- |
| `status` | Always. One of `AVAILABLE`, `UNDER_EMBARGO`, `NO_PERMIT`, `PREPARING`. |
| `pdf_key` | `status is AVAILABLE`. |
| `appendix_key` | `status is AVAILABLE` and an appendix exists alongside the PDF. |
| `restricted_until` | `status is UNDER_EMBARGO`. A `datetime.date`. |
| `info_message` | Any non-`AVAILABLE` state; `None` for `AVAILABLE`. The wire's user-facing reason text. |

## The canonical flow

```python
from yoktez import AssetStatus, Client

with Client() as client:
    thesis = client.search.simple("yapay zeka")[0]
    assets = client.assets.get(thesis)

    match assets.status:
        case AssetStatus.AVAILABLE:
            client.assets.download_pdf(assets.pdf_key, "thesis.pdf")
            if assets.appendix_key is not None:
                client.assets.download_appendix(assets.appendix_key, "thesis-ek.rar")
        case AssetStatus.UNDER_EMBARGO:
            print(f"Available after {assets.restricted_until}")
        case AssetStatus.NO_PERMIT | AssetStatus.PREPARING:
            print(assets.info_message)
```

The pyright-strict surface narrows `pdf_key` and `appendix_key` to `str` only inside the `AVAILABLE` branch, so static analysis catches the rest.

## Download targets

`dest` accepts three shapes:

| Type | Behavior |
| --- | --- |
| `pathlib.Path` | The library opens the file in `wb`, writes the stream, and closes it. |
| `str` | Coerced to `Path`. Same behavior. |
| `BinaryIO` (file-like) | The library writes into it but does **not** close it. Ownership stays with the caller. |

```python
# To disk
client.assets.download_pdf(key, "thesis.pdf")
client.assets.download_pdf(key, Path("/tmp/thesis.pdf"))

# To memory
import io
buf = io.BytesIO()
client.assets.download_pdf(key, buf)
pdf_bytes = buf.getvalue()

# To a custom sink
class S3Uploader:
    def write(self, chunk: bytes) -> None: ...

client.assets.download_pdf(key, S3Uploader())  # accepted; library never closes it
```

> [!NOTE]
> The `BinaryIO` branch is structural: the library only calls `.write(chunk: bytes)` on `dest`. Any object that supports that method works, regardless of inheritance.

## Streaming and `chunk_size`

The library uses `httpx.Client.stream("GET", url)` and iterates with `response.iter_bytes(chunk_size)`. The default chunk is 64 KiB (`2**16`).

```python
# Reduce memory use on a tight system, at the cost of more syscalls.
client.assets.download_pdf(key, "out.pdf", chunk_size=8192)

# Bigger chunks, fewer syscalls. Trades memory for throughput.
client.assets.download_pdf(key, "out.pdf", chunk_size=1024 * 1024)
```

Bytes are not held in memory across iterations — each chunk is written and discarded. A 500 MB PDF streams through with a working set on the order of `chunk_size` plus httpx's internal buffers.

## Errors

### `httpx.HTTPStatusError`

```python
client.assets.download_pdf("expired-key", "out.pdf")
# httpx.HTTPStatusError: 404 ... at https://tez.yok.gov.tr/UlusalTezMerkezi/TezGoster?key=expired-key
```

The library calls `response.raise_for_status()` inside the stream context. Re-raised unwrapped. Catch `httpx.HTTPStatusError` if you need to handle download-key expiry separately from other failures.

> [!TIP]
> Download keys may expire after a session ends. If you persist a key and try to download later, expect a 4xx. Re-fetch via `client.assets.get(thesis)` to renew.

### `ValueError`

```python
client.assets.get(Thesis(registration_no="r", thesis_no=None, ...))
# ValueError: ... has thesis_no=None; pass an explicit (registration_no, thesis_no) tuple instead
```

Same shape as the metadata service: a `Thesis` with `thesis_no=None` cannot address the endpoint. Use the tuple form or skip the malformed card.

### `ParseError`

```python
# When the wire's HTML shape changes materially:
ParseError: Could not classify pdf-container shape
```

Raised by the assets parser when none of the four known regex shapes match. Indicates real upstream drift and should be reported.

## Embargo handling

```python
assets = client.assets.get(thesis)
if assets.status is AssetStatus.UNDER_EMBARGO:
    import datetime as dt
    if assets.restricted_until <= dt.date.today():
        # Embargo has technically passed — retry the call.
        assets = client.assets.get(thesis)
```

The wire's reported `restricted_until` date is the day after which the PDF becomes available. If you cache results, invalidate the entry on or after that date.

### Embargo info-message languages

YOK NTC emits the info message in either Turkish or English depending on the user's session. The classifier doesn't read the message language — it reads the date. Both these messages classify as `UNDER_EMBARGO`:

```text
27.09.2026 tarihine kadar kullanımı yazar tarafından kısıtlanmıştır.
At the request of the author, this thesis is under embargo until 27.09.2026
```

## No-permit handling

```python
assets = client.assets.get(thesis)
if assets.status is AssetStatus.NO_PERMIT:
    # The thesis is permanently unavailable from YOK NTC. Pursue printed copies
    # via the institutional library (TÜBESS).
    log.info("no-permit thesis: %s", assets.info_message)
```

There is no retry path. The library's `info_message` carries the upstream's recommendation text (point users at TÜBESS or institutional libraries).

## Preparing handling

```python
if assets.status is AssetStatus.PREPARING:
    # The thesis is in upload/processing limbo. Re-check periodically.
    pass
```

Like `UNDER_EMBARGO`, the state is transient — but the library has no way to predict when it will resolve. Re-check on a schedule appropriate for your use case (daily for a monitoring tool, never for one-off batch jobs).

## Appendix downloads

The appendix is optional and typically a RAR archive containing supplementary materials (data, figures, datasets).

```python
assets = client.assets.get(thesis)
if assets.status is AssetStatus.AVAILABLE and assets.appendix_key is not None:
    client.assets.download_appendix(assets.appendix_key, "appendix.rar")
```

YOK NTC does not guarantee the format. Inspect the response's `Content-Type` if your code branches on file format:

```python
# If you need the format, drop down to httpx:
with client.http_client.stream("GET", "https://tez.yok.gov.tr/UlusalTezMerkezi/EkGoster", params={"key": assets.appendix_key}) as response:
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    # do branching ...
    for chunk in response.iter_bytes():
        ...
```

## `ThesisUnavailable*Error` (related but not raised here)

The exception classes `ThesisUnderEmbargoError`, `ThesisNoPermitError`, and `ThesisPreparingError` exist in `yoktez.errors` for callers who prefer exception-driven control flow. The library does **not** currently raise them automatically — `client.assets.get` returns a `ThesisAssets` regardless of state, and your code branches on `.status`.

If you want the exception pattern, wrap the call yourself:

```python
from yoktez import AssetStatus, ThesisNoPermitError, ThesisPreparingError, ThesisUnderEmbargoError

def get_assets_or_raise(client, thesis):
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

## Gotchas

### Don't reuse keys across processes without re-fetching

Keys are session-scoped on the wire (cookie-bound). The library shares a `JSESSIONID` within a single `Client`, so a key obtained from a fresh `get()` will work within the same `Client` instance for some window. Persisting keys across processes is unsupported.

### Don't seek a stream you're streaming into

If `dest` is a `BinaryIO` that doesn't support `write` between seeks, the library will write linearly. `io.BytesIO` and standard files behave correctly; specialized streams (e.g., compressing writers) need to support the same.

### `chunk_size` does not affect correctness

Picking the wrong `chunk_size` can affect throughput, not bytes-on-disk. The total length and content are identical regardless of chunking.

## See also

- [Search](search.md) — find the thesis.
- [Errors](errors.md) — exception classes and httpx pass-through semantics.
- [Concurrency](concurrency.md) — running downloads in parallel safely.
- [Cookbook](cookbook.md) — copy-paste batch download recipes.
