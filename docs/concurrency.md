# Concurrency

`yoktez` is synchronous-only and single-threaded by design. There is no `async` surface, no internal threading, no helper pool primitives. The library expects the caller to choose a concurrency strategy and apply it externally.

## The core rule

**One `Client` per thread.** Never share a `Client` across threads.

## Why

`yoktez.Client` is not thread-safe:

- `LookupsService._cache` is a plain `dict` with no lock. Two threads memoizing the same lookup simultaneously can corrupt the dict or duplicate work.
- The lazy sub-service properties (`client.search`, `client.metadata`, …) read-modify-write `self._search` etc. without synchronization. Two threads accessing `client.search` for the first time can leak a `SearchService` instance and race the assignment.
- The internal `_closed` flag is not atomic. Two threads calling `close()` concurrently can both pass the `if self._closed: return` guard.

`httpx.Client` itself is thread-safe at the request level, but the wrapping `Client` is not. Putting a lock around every public method would solve the problem at the cost of serializing every call — pointless when one `Client` per thread is cheap.

## The canonical pattern

```python
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor

from yoktez import Client

_thread_local = threading.local()


def get_client() -> Client:
    client = getattr(_thread_local, "client", None)
    if client is None:
        client = Client()
        weakref.finalize(client, client.close)
        _thread_local.client = client
    return client


def work(task):
    client = get_client()
    # ... use `client` ...


with ThreadPoolExecutor(max_workers=4) as pool:
    pool.map(work, tasks)
```

This is the pattern in `examples/multithreaded_pool.py`. The `weakref.finalize` attaches a `close()` to the moment when `threading.local` releases the last strong reference to the `Client` — i.e., thread exit.

> [!IMPORTANT]
> Don't use `with Client() as client:` inside `work()`. That makes the `Client` per-task, not per-thread, defeating the connection-pool reuse benefit.

## Concurrency primitives

### Pure parallelism — `ThreadPoolExecutor`

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=8) as pool:
    futures = [pool.submit(download_one, k) for k in keys]
    for future in futures:
        result = future.result()
```

The standard library's `ThreadPoolExecutor` is the right primitive for I/O-bound parallel work like batch downloads. YOK NTC is reasonably tolerant of parallel requests, but **stay reasonable** — single-digit concurrent threads, not hundreds.

### Background fetch in a UI

```python
import threading

results_box = {}

def fetch_in_background():
    client = get_client()
    results_box["v"] = client.search.simple("...")

threading.Thread(target=fetch_in_background).start()
```

A separate thread per UI action works fine. Each thread spins up its own `Client` lazily.

### Async event loops

`yoktez` is sync-only. If you need to call it from `asyncio` code, use `asyncio.to_thread`:

```python
import asyncio
from yoktez import Client

async def fetch(client: Client, query: str):
    return await asyncio.to_thread(client.search.simple, query)

async def main():
    client = Client()
    try:
        results = await fetch(client, "yapay zeka")
    finally:
        await asyncio.to_thread(client.close)

asyncio.run(main())
```

This is acceptable for one-off calls. For high-throughput async pipelines you'd want a thread pool dedicated to `yoktez` work, with one `Client` per pool thread — wire it the same way as `threading.local`.

## What `Client` _is_ safe for across threads

- Inspecting `client.http_client` for read-only state. `httpx.Client` has its own threading story.
- Calling `close()` from a different thread than the one that constructed the `Client`, provided you guarantee no other thread is concurrently using the `Client` for requests.

That's about it.

## Multi-process

```python
from multiprocessing import Pool
from yoktez import Client


def work(query: str) -> int:
    # Each worker constructs its own Client; fork-safety isn't a concern.
    with Client() as client:
        return client.search.simple(query).total


if __name__ == "__main__":
    with Pool(processes=4) as pool:
        totals = pool.map(work, ["yapay zeka", "robotics", "edukasyon"])
```

`Client` constructors in subprocesses are independent. No special handling needed for `fork` vs `spawn`; `httpx.Client` does not survive a fork cleanly, so the construct-inside-the-worker pattern is what you want.

> [!CAUTION]
> Do not pickle or fork a `Client` that already has open connections. Construct it after the fork.

## Rate limiting

The library does not rate-limit. YOK NTC does not aggressively rate-limit anonymous scrapers in practice, but courteous use is expected. Recommendations:

- Single-digit concurrent threads for batch downloads. `examples/multithreaded_pool.py` uses 4.
- Avoid hammering search endpoints in tight loops; cache results in your own layer if you re-query frequently.
- Back off on `httpx.TimeoutException` and `httpx.HTTPStatusError` 5xx — these can indicate transient overload.

## Lookup cache and concurrency

The per-`Client` `LookupsService._cache` is _not_ shared across `Client`s. Each thread's `Client` pays the first-call cost independently.

If your workload calls `client.lookups.universities()` heavily from many threads, two strategies help:

1. **Pre-warm in the main thread**, then pass results to workers:

   ```python
   with Client() as main:
       unis = main.lookups.universities()
       institutes_by_uni = {u.id: main.lookups.institutes(u) for u in unis}
   pool.map(partial(work, institutes_by_uni=institutes_by_uni), tasks)
   ```

2. **Single fetch-and-cache layer above `yoktez`**: a module-level dict, populated once, shared read-only across threads.

## See also

- [Client](client.md) — `http_client=` injection if you need a shared, thread-safe connection pool across `Client` instances (use with care; one cookie jar across threads can still corrupt session state).
- [`examples/multithreaded_pool.py`](../examples/multithreaded_pool.py) — the canonical reference implementation.
