# Getting started

This page walks through installing `yoktez`, running a first script, and understanding what the library does and does not do.

## Install

```bash
pip install yoktez
```

`yoktez` requires Python 3.14 or newer. It depends on `httpx`, `beautifulsoup4`, and `lxml` — three transitive packages, all pure Python or with prebuilt wheels for every Tier-1 platform. There is no Rust core, no compiled extension built from source, no extras.

> [!NOTE]
> Python 3.14 is a hard requirement, not a recommendation. The codebase uses PEP 695 generics (`def _memoize[T](...)`), PEP 749 deferred annotations, and other 3.14-only features. On older interpreters the package won't even import.

## A minimal script

```python
from yoktez import Client

with Client() as client:
    results = client.search.simple("yapay zeka")
    print(f"{results.total} matches in the database")

    for thesis in results[:5]:
        print(f"{thesis.year}  {thesis.author}  {thesis.title}")
```

That is enough to verify the install, your network egress to `tez.yok.gov.tr`, and the upstream service health. Save it as `smoke.py` and run `python smoke.py` — you should see five thesis cards print in under a couple of seconds.

## What you just did

Three things happened in order:

1. The `Client` constructor built an `httpx.Client` with browser-style headers, a 30-second timeout, and three connection-level retries. It did _not_ make a network call.
2. `client.search.simple(...)` POSTed a form-encoded query to `https://tez.yok.gov.tr/UlusalTezMerkezi/SearchTez`, followed the resulting `302` to the JSP result page, and parsed the returned HTML.
3. The `with` block exited and called `client.close()`, releasing the underlying HTTP connection pool.

The return value (`results`) is a `SearchResults` — an immutable, sliceable wrapper around a tuple of `Thesis` records. Every `Thesis` is a frozen, slotted dataclass; field types are fully annotated.

## The three primary endpoints

Most user-facing code uses exactly three method namespaces, in this sequence:

```python
results = client.search.simple("term")          # 1. find candidates
metadata = client.metadata.get(results[0])      # 2. fetch detail
assets = client.assets.get(results[0])          # 3. resolve download key
```

Each of the three has its own documentation page: [search](search.md), [metadata](metadata.md), [assets](assets.md). The [`Client` page](client.md) covers the constructor.

## What `yoktez` does not do

Read the README's _Limitations_ section before relying on a feature you don't see here. The shortlist:

- No async API. Everything is synchronous. See [concurrency](concurrency.md) for thread-pool patterns.
- No login / e-Devlet integration. Public anonymous access only.
- No bypass of embargo or no-permit restrictions. The library reports the state and stops.
- No bundled database snapshot. Every call hits the wire.
- No CLI shipped with this package.

## Verifying the install programmatically

```python
import yoktez

print(yoktez.__version__)
```

The version is resolved from package metadata at import time via `importlib.metadata.version("yoktez")`. If the package is installed in editable mode but its `*.dist-info` directory is missing, `__version__` falls back to a sentinel like `"0.1.2+local"`.

## Where to go next

- For application code: [the `Client` class](client.md), then [search](search.md).
- For batch / pipeline code: [cookbook](cookbook.md), then [concurrency](concurrency.md).
- For debugging a flaky environment: [errors](errors.md), then [logging](logging.md).
