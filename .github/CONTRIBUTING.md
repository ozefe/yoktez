# Contributing

Thanks for your interest in improving `yoktez`. This is a small library with a narrow scope; please skim the README's _Limitations_ section before opening anything that adds a feature.

## Setup

Requires Python 3.14+.

```bash
git clone https://github.com/ozefe/yoktez
cd yoktez
python -m venv .venv
source .venv/bin/activate
pip install -e . --group dev
```

The `dev` dependency group bundles `pytest`, `pytest-cov`, `ruff`, and `pyright`. Smaller groups (`test`, `lint`, `typing`) are available when you only need a subset.

## Workflow

1. Open an issue first for any change larger than a single-file fix or doc tweak — saves wasted work when a proposal is out of scope.
2. Branch off `main`; one logical change per pull request.
3. Follow TDD: write a failing test, make it pass, refactor. Run `pytest` after every change.
4. Commit with [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, etc.) in imperative mood, subject under 72 characters.
5. Open the pull request linking the issue. Describe _why_, not _what_ — the diff already shows what.

## Code style

- Python 3.14+
- `ruff check --fix` for lint and format; the configuration in `pyproject.toml` uses `select = ["ALL"]` and every per-file ignore is paired with an inline comment explaining why.
- `pyright` runs in `strict` mode against `src/` and `tests/`.
- Public APIs ship with Google-style docstrings including `Args` / `Returns` / `Raises`. Private members get a docstring only when behavior is non-obvious.
- Frozen, slotted dataclasses (`@dataclass(frozen=True, slots=True)`) for every value object. Standard library only — no Pydantic, `attrs`, or Rust-backed deps.

## Tests

`pytest` defaults deselect network tests. Run them explicitly when you need live coverage:

```bash
pytest                                              # offline suite (default)
pytest -m live                                      # live YOK NTC requests
pytest --cov=yoktez --cov-report=term-missing       # coverage report
```

Wire-shape fixtures live under `tests/fixtures/<sub-package>/`. Capture a fresh fixture when adding a parser case for a previously-unseen response variant.

## Scope

The README's _Limitations_ section enumerates what `yoktez` will not do. Proposals touching those areas will be closed with a pointer to that section.

## Conduct

By participating you agree to the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
