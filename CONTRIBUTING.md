# Contributing to tio-shacl

Thanks for your interest. This document describes the development workflow, conventions, and how to add or change shapes and tests.

---

## Prerequisites

- **pyenv** ≥ 2.4 — Python version management
- **uv** ≥ 0.5 — dependency management
- **Python 3.11** — install via `pyenv install 3.11` if missing
- **Java 17+** and **Maven wrapper** — only needed if building TopBraid/Jena CLIs
- A local copy of **TIO 3.6.0** — see [docs/setup.md](docs/setup.md)

---

## Dev setup

```bash
git clone https://github.com/earejma/tio-shacl.git
cd tio-shacl
make install       # uv sync --all-extras --all-groups
make setup-tio     # apply TIO bugfix patch (requires ontology/ populated)
make test
```

---

## Test-driven development

`tio-shacl` follows strict TDD. The rules:

1. Every new SHACL shape must ship with at least one *good* case and one *bad* case in `test-cases/<ModuleName>/`.
2. Every new Python feature must have a failing test before the implementation is written.
3. `make test` must be green on every PR.

### Adding a validation test case

```bash
# Good case (should pass SHACL validation)
# Place under test-cases/<Module>/good/<description>.ttl

# Bad case (should fail SHACL validation)
# Place under test-cases/<Module>/bad/<description>.ttl
# Bad cases may have a matching .expected.json listing focus nodes.
```

Then run:

```bash
make test
```

### Adding a new shape

1. Add the shape to `rdf/shapes/<Module>.ttl` or `extensions/<Name>.ttl`.
2. Add at least one good and one bad test case (see above).
3. Run `make test` and ensure the new bad case fails validation and the good case passes.
4. If the shape adds a canonical constraint ID, register it in `taxonomy.yaml` (when introduced).

---

## Code style

```bash
make format    # ruff format + autofix
make lint      # ruff check
make type-check  # mypy
```

All of the above must pass before opening a PR. Pre-commit hooks enforce formatting; install them with:

```bash
uv run pre-commit install
```

### Conventions

- Type hints required on all functions (mypy strict mode).
- Line length 110.
- Import order: stdlib, third-party, first-party, local — enforced by ruff/isort.
- Prefer small pure functions over classes when feasible.
- Log at `INFO` for user-visible events, `DEBUG` for internals.

---

## Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`.

Examples:

- `feat(shapes): add ProbingTarget constraint`
- `fix(validation): skip unreachable test-cases on missing ontology`
- `docs(setup): clarify TIO download step`

---

## Pull requests

1. Fork and branch from `main`: `git checkout -b feat/my-feature`
2. Make your changes with tests.
3. Run `make test lint type-check`.
4. Push and open a PR against `main`.
5. Fill in the PR description: what, why, testing evidence.
6. One approving review required; CI must be green.

Small PRs are easier to review — aim for <500 changed lines when possible.

---

## Reporting bugs / suggesting shapes

Open an issue at <https://github.com/earejma/tio-shacl/issues> with:

- The intent TTL that triggers the issue (minimal reproducer preferred)
- Expected vs actual validation outcome
- Which validator you used (`pyshacl`, `topbraid`, `jena`)
- Your TIO ontology version

---

## IPR

Please do not include TIO ontology .ttl content in issues, PRs, or test cases. Reference TIO concepts by name and URI only. See [docs/setup.md](docs/setup.md) for why.

---

## License

By contributing, you agree your contributions are licensed under [Apache-2.0](LICENSE).
