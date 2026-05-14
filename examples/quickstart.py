"""End-to-end yoktez quickstart: search -> metadata -> assets.

Demonstrates the typical three-call flow without writing files to disk.

Run with: `python examples/quickstart.py`
"""

from yoktez import AssetStatus, Client

_QUERY = "yapay zeka"


def main() -> None:
    with Client() as client:
        results = client.search.simple(_QUERY)
        print(f"{results.total} matches for {_QUERY!r}")

        thesis = results[0]
        print(f"  title:   {thesis.title}")
        print(f"  author:  {thesis.author}")
        print(f"  year:    {thesis.year}")
        print(f"  keys:    {thesis.registration_no} / {thesis.thesis_no}")

        metadata = client.metadata.get(thesis)
        print(f"  advisor: {metadata.supervisor}")
        if metadata.affiliation is not None:
            print(f"  uni:     {metadata.affiliation.university}")
        if metadata.keywords is not None:
            print(f"  tags:    {len(metadata.keywords)} keywords")

        assets = client.assets.get(thesis)
        print(f"  status:  {assets.status.name}")
        if assets.status is AssetStatus.AVAILABLE:
            print(f"  pdf_key: {assets.pdf_key}")


if __name__ == "__main__":
    main()
