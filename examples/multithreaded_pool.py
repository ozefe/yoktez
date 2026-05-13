"""Download PDFs in parallel using one Client per thread.

Demonstrates the canonical concurrency pattern for `yoktez`: each worker thread owns its
own `Client`.

`weakref.finalize(client, client.close)` registers an explicit `close()` against the
Client's lifecycle: when the thread exits, the `threading.local` storage releases its
strong reference and the finalizer runs.

Run with: `python examples/multithreaded_pool.py`
"""

import tempfile
import threading
import time
import weakref
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

from yoktez import AssetStatus, Client

_QUERY = "yapay zeka"
_LIMIT = 8
_MAX_WORKERS = 4

_thread_local = threading.local()


def get_client() -> Client:
    client = getattr(_thread_local, "client", None)
    if client is None:
        client = Client()
        weakref.finalize(client, client.close)
        _thread_local.client = client

    return client


def download_one(keys: tuple[str, str], *, out_dir: Path) -> str:
    registration_no, thesis_no = keys
    client = get_client()
    assets = client.assets.get(keys)

    if assets.status is AssetStatus.AVAILABLE and assets.pdf_key:
        dest = out_dir / f"{registration_no}_{thesis_no}.pdf"
        client.assets.download_pdf(assets.pdf_key, dest)

        return f"saved {dest.name} ({dest.stat().st_size} bytes)"

    return f"skipped {registration_no} (status={assets.status.name})"


def main() -> None:
    out_dir = Path(tempfile.mkdtemp(prefix="yoktez-pool-"))
    print(f"Downloading to {out_dir} (max_workers={_MAX_WORKERS})")

    # Main-thread Client is local to the search phase; workers each spin up their own.
    with Client() as client:
        results = client.search.simple(_QUERY)
        targets: list[tuple[str, str]] = [
            (t.registration_no, t.thesis_no)
            for t in results[:_LIMIT]
            if t.thesis_no is not None
        ]

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        for message in pool.map(partial(download_one, out_dir=out_dir), targets):
            print(f"  {message}")
    elapsed = time.perf_counter() - start

    print(f"\nfinished {len(targets)} downloads in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
