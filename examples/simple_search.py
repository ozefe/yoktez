"""Print the first 10 simple-search results for 'yapay zeka'.

Run with: `python examples/simple_search.py`
"""

from yoktez import Client

_QUERY = "yapay zeka"
_LIMIT = 10


def main() -> None:
    with Client() as client:
        results = client.search.simple(_QUERY)
        print(f"{len(results)} results returned ({results.total} matches in database)")

        for thesis in results[:_LIMIT]:
            print(f"  {thesis.year} {thesis.author} -- {thesis.title}")


if __name__ == "__main__":
    main()
