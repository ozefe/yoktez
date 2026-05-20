# Cookbook

Copy-paste recipes for the most common `yoktez` tasks. Every recipe is self-contained.

## Recipes

- [List the most recent 25 theses](#list-the-most-recent-25-theses)
- [Search and print the top 10](#search-and-print-the-top-10)
- [Filter by year range and degree level](#filter-by-year-range-and-degree-level)
- [Search within one university](#search-within-one-university)
- [Download a single thesis to disk](#download-a-single-thesis-to-disk)
- [Stream a thesis into memory](#stream-a-thesis-into-memory)
- [Batch-download N theses sequentially](#batch-download-n-theses-sequentially)
- [Batch-download in parallel](#batch-download-in-parallel)
- [Resume an interrupted batch](#resume-an-interrupted-batch)
- [Aggregate metadata into a JSON file](#aggregate-metadata-into-a-json-file)
- [Track embargo expirations](#track-embargo-expirations)
- [Build a typed `University` from a YOKSIS ID](#build-a-typed-university-from-a-yoksis-id)
- [Pre-warm the lookup cache in the main thread](#pre-warm-the-lookup-cache-in-the-main-thread)
- [Persist `(registration_no, thesis_no)` keys to a CSV](#persist-registration_no-thesis_no-keys-to-a-csv)

## List the most recent 25 theses

```python
from yoktez import Client

with Client() as client:
    results = client.search.recent()
    for thesis in results[:25]:
        print(f"{thesis.year}  {thesis.author}  {thesis.title}")
```

`recent()` returns theses added in the last 15 days; the window is server-fixed.

## Search and print the top 10

```python
from yoktez import Client

with Client() as client:
    results = client.search.simple("yapay zeka")
    print(f"{len(results)} returned of {results.total} total")
    for t in results[:10]:
        print(f"  {t.year}  {t.title}")
```

`results.total` is the database-wide match count. `len(results)` is what fit on this page (max 2,000).

## Filter by year range and degree level

```python
from yoktez import Client, ThesisType

with Client() as client:
    results = client.search.detail(
        title="yapay zeka",
        year_min=2020,
        year_max=2025,
        degree_type=ThesisType.DOCTORATE,
    )
```

`detail()` accepts all filters as keyword arguments. Year bounds are inclusive.

## Search within one university

```python
from yoktez import Client

with Client() as client:
    unis = client.lookups.universities()
    bogazici = next(u for u in unis if "BOĞAZİÇİ" in u.display_name)

    results = client.search.detail(university=bogazici, year_min=2020)
    print(f"{results.total} theses from {bogazici.display_name} since 2020")
```

A `University` carries its display name, IDs, and source — `detail()` uses all of them.

## Download a single thesis to disk

```python
from yoktez import AssetStatus, Client

with Client() as client:
    thesis = client.search.simple("yapay zeka")[0]
    assets = client.assets.get(thesis)

    if assets.status is AssetStatus.AVAILABLE:
        client.assets.download_pdf(assets.pdf_key, "thesis.pdf")
        if assets.appendix_key is not None:
            client.assets.download_appendix(assets.appendix_key, "appendix.rar")
    else:
        print(f"{assets.status.name}: {assets.info_message}")
```

## Stream a thesis into memory

```python
import io
from yoktez import AssetStatus, Client

with Client() as client:
    thesis = client.search.simple("yapay zeka")[0]
    assets = client.assets.get(thesis)

    if assets.status is AssetStatus.AVAILABLE:
        buf = io.BytesIO()
        client.assets.download_pdf(assets.pdf_key, buf)
        pdf_bytes = buf.getvalue()
        print(f"got {len(pdf_bytes)} bytes")
```

`BytesIO` is a `BinaryIO`; the library writes into it but never closes it.

## Batch-download N theses sequentially

```python
from pathlib import Path
from yoktez import AssetStatus, Client

OUT = Path("./downloads")
OUT.mkdir(exist_ok=True)
LIMIT = 10

with Client() as client:
    results = client.search.simple("yapay zeka")

    downloaded = 0
    for thesis in results:
        if downloaded >= LIMIT:
            break
        if thesis.thesis_no is None:
            continue

        assets = client.assets.get(thesis)
        if assets.status is not AssetStatus.AVAILABLE:
            continue

        dest = OUT / f"{thesis.display_no}.pdf"
        client.assets.download_pdf(assets.pdf_key, dest)
        downloaded += 1

print(f"saved {downloaded} files to {OUT}")
```

## Batch-download in parallel

```python
import threading, weakref
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from yoktez import AssetStatus, Client

_thread_local = threading.local()


def get_client() -> Client:
    client = getattr(_thread_local, "client", None)
    if client is None:
        client = Client()
        weakref.finalize(client, client.close)
        _thread_local.client = client
    return client


def download_one(keys: tuple[str, str], *, out: Path) -> str:
    registration_no, thesis_no = keys
    client = get_client()
    assets = client.assets.get(keys)
    if assets.status is AssetStatus.AVAILABLE and assets.pdf_key:
        dest = out / f"{registration_no}.pdf"
        client.assets.download_pdf(assets.pdf_key, dest)
        return f"saved {dest.name}"
    return f"skipped {registration_no} ({assets.status.name})"


def main() -> None:
    out = Path("./downloads"); out.mkdir(exist_ok=True)
    with Client() as main_client:
        targets = [
            (t.registration_no, t.thesis_no)
            for t in main_client.search.simple("yapay zeka")[:20]
            if t.thesis_no is not None
        ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for msg in pool.map(partial(download_one, out=out), targets):
            print(msg)


if __name__ == "__main__":
    main()
```

The canonical pattern. See [concurrency](concurrency.md). Use single-digit `max_workers`; YOK NTC is tolerant but not unlimited.

## Resume an interrupted batch

```python
import json
from pathlib import Path
from yoktez import AssetStatus, Client

STATE = Path("batch-state.json")
OUT = Path("./downloads"); OUT.mkdir(exist_ok=True)

state = json.loads(STATE.read_text()) if STATE.exists() else {"done": []}
done = set(state["done"])

with Client() as client:
    results = client.search.simple("yapay zeka")
    for thesis in results:
        if thesis.registration_no in done or thesis.thesis_no is None:
            continue

        assets = client.assets.get(thesis)
        if assets.status is AssetStatus.AVAILABLE:
            client.assets.download_pdf(assets.pdf_key, OUT / f"{thesis.display_no}.pdf")

        done.add(thesis.registration_no)
        STATE.write_text(json.dumps({"done": list(done)}))
```

Persist completed `registration_no`s after each thesis; re-run is idempotent.

## Aggregate metadata into a JSON file

```python
import dataclasses, datetime as dt, json
from pathlib import Path
from yoktez import Client


def _default(obj):
    if isinstance(obj, dt.date):
        return obj.isoformat()
    raise TypeError


with Client() as client:
    results = client.search.simple("yapay zeka")[:50]
    records = []
    for thesis in results:
        if thesis.thesis_no is None:
            continue
        meta = client.metadata.get(thesis)
        records.append({
            "registration_no": thesis.registration_no,
            "thesis_no": thesis.thesis_no,
            "display_no": thesis.display_no,
            "title": thesis.title,
            "year": thesis.year,
            "author": thesis.author,
            "supervisor": meta.supervisor,
            "affiliation": dataclasses.asdict(meta.affiliation) if meta.affiliation else None,
            "keywords_tr": [k.tr for k in (meta.keywords or [])],
            "keywords_en": [k.en for k in (meta.keywords or []) if k.en],
        })

Path("aggregated.json").write_text(
    json.dumps(records, default=_default, ensure_ascii=False, indent=2)
)
```

`ensure_ascii=False` preserves Turkish characters readably. The `default` callable handles `datetime.date`.

## Track embargo expirations

```python
import datetime as dt
from yoktez import AssetStatus, Client

today = dt.date.today()

with Client() as client:
    results = client.search.detail(
        access="UNAUTHORIZED",  # narrows the candidate set
        year_min=2020,
        year_max=2025,
    )

    expiring_soon = []
    for thesis in results[:200]:
        if thesis.thesis_no is None:
            continue
        assets = client.assets.get(thesis)
        if assets.status is AssetStatus.UNDER_EMBARGO:
            days_left = (assets.restricted_until - today).days
            if 0 < days_left <= 30:
                expiring_soon.append((thesis, days_left))

    for thesis, days in sorted(expiring_soon, key=lambda x: x[1]):
        print(f"{days:>3}d  {thesis.title}")
```

## Build a typed `University` from a YOKSIS ID

```python
from yoktez import Client, UniversitySource

KNOWN_YOKSIS_ID = "ZDJv5lAIQDOnVGpRdJBQxA"

with Client() as client:
    # Search by raw YOKSIS ID — no lookup call needed
    results = client.search.detail(university=KNOWN_YOKSIS_ID)

    # To inflate to a typed University, find the record in the catalog
    unis = client.lookups.universities(UniversitySource.TR)
    uni = next((u for u in unis if u.yoksis_id == KNOWN_YOKSIS_ID), None)
    if uni is not None:
        print(uni.display_name)
```

YOK NTC rotates YOKSIS IDs occasionally; the old IDs continue working but lookups won't surface them via current catalogs.

## Pre-warm the lookup cache in the main thread

```python
import threading, weakref
from concurrent.futures import ThreadPoolExecutor
from yoktez import Client

_thread_local = threading.local()


def get_client():
    client = getattr(_thread_local, "client", None)
    if client is None:
        client = Client()
        weakref.finalize(client, client.close)
        _thread_local.client = client
    return client


def search_by_university(university):
    return get_client().search.detail(university=university).total


def main():
    with Client() as main_client:
        unis = main_client.lookups.universities()[:20]

    with ThreadPoolExecutor(max_workers=4) as pool:
        for u, total in zip(unis, pool.map(search_by_university, unis)):
            print(f"{u.display_name}: {total}")


if __name__ == "__main__":
    main()
```

Fetch the universities list once in the main thread; pass them by value into workers. Each worker `Client` builds its own cache, but the universities themselves don't need re-fetching.

## Persist `(registration_no, thesis_no)` keys to a CSV

```python
import csv
from pathlib import Path
from yoktez import Client

OUT = Path("keys.csv")

with Client() as client, OUT.open("w", newline="", encoding="utf-8") as fh:
    writer = csv.writer(fh)
    writer.writerow(["registration_no", "thesis_no", "year", "title"])

    results = client.search.simple("yapay zeka")
    for t in results[:500]:
        if t.thesis_no is None:
            continue
        writer.writerow([t.registration_no, t.thesis_no, t.year, t.title])
```

To re-hydrate later:

```python
import csv
from yoktez import Client

with Client() as client, open("keys.csv", newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        meta = client.metadata.get((row["registration_no"], row["thesis_no"]))
        ...
```

The `(registration_no, thesis_no)` tuple is the stable key. Cards and full metadata can be re-fetched on demand; keys persist.

## See also

- [Search](search.md), [Metadata](metadata.md), [Assets](assets.md) — reference for each API surface.
- [Concurrency](concurrency.md) — depth on the threading patterns shown above.
- [`examples/`](../examples) — fully runnable scripts with `main()` wrappers.
