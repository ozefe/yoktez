"""Search 'yapay zeka' and stream the first 5 AVAILABLE PDFs to a temp directory.

Demonstrates the two-step download flow:
    `client.assets.get(thesis)` -> inspect status -> `client.assets.download_pdf(...)`.

Run with: `python examples/batch_download.py`
"""

import tempfile
import time
from pathlib import Path

from yoktez import AssetStatus, Client

_QUERY = "yapay zeka"
_LIMIT = 5


def main() -> None:
    out_dir = Path(tempfile.mkdtemp(prefix="yoktez-batch-"))
    print(f"Downloading to {out_dir}")

    downloaded = 0
    skipped = 0

    with Client() as client:
        results = client.search.simple(_QUERY)

        start = time.perf_counter()
        for thesis in results:
            if downloaded >= _LIMIT:
                break

            if thesis.thesis_no is None:
                print(f"  skipped {thesis.display_no} (malformed card)")
                skipped += 1
                continue

            assets = client.assets.get(thesis)
            if assets.status is AssetStatus.AVAILABLE and assets.pdf_key:
                dest = out_dir / f"{thesis.display_no}.pdf"
                client.assets.download_pdf(assets.pdf_key, dest)

                print(f"  saved {dest.name} ({dest.stat().st_size} bytes)")
                downloaded += 1
            else:
                print(f"  skipped {thesis.display_no} (status={assets.status.name})")
                skipped += 1
        elapsed = time.perf_counter() - start

    print(f"\n{downloaded} downloaded, {skipped} skipped in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
