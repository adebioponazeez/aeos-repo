# PUBLISHING — aeos to PyPI

*Status at v31.0.0: artifacts BUILD and PASS `twine check`. The name
`aeos` was FREE on PyPI at check time (2026-09-03) — short names do
not stay free. Everything below is ready; only the account step is
yours.*

## The artifacts (verified this session)

- `dist/aeos-31.0.0-py3-none-any.whl` — 62 files, LICENSE included
- `dist/aeos-31.0.0.tar.gz` — 107 members, LICENSE + tests included
- Both PASSED `twine check` (metadata, readme render)

## Path A — publish in 3 commands (your machine)

```bash
pip install build twine
python -m build            # from the repo root (artifacts land in dist/)
python -m twine upload dist/*   # asks for: __token__ + your PyPI API token
```

PyPI API token: pypi.org → Account settings → API tokens → add
(scope: entire account for first upload — the project is created by
the first upload itself).

## Path B — trusted publishing via CI (no tokens)

Add to `.github/workflows/ci.yml` a release job using
`pypa/gh-action-pypi-publish` with `permissions: id-token: write`,
after creating a "pending publisher" on PyPI pointing at this repo +
workflow + environment. This is the no-long-lived-credentials path.

## Rules already in place (nothing to decide at publish time)

- Zero runtime dependencies — the wheel installs nothing else (ADR-002)
- LICENSE ships in both artifacts and is asserted by CI
- Version is single-sourced in `pyproject.toml` + `__init__.py`
  (bump both, in the same commit, with the CHANGELOG entry)
- `pip install aeos && aeos selftest` is the post-publish smoke

## Post-publish checklist

- [ ] `pip install aeos` in a clean venv → `aeos selftest` → identity
- [ ] `pip download aeos --no-deps` → inspect: LICENSE present
- [ ] GitHub release for the tag carries the Codex PDFs (established
      at v29/v30/v31)
