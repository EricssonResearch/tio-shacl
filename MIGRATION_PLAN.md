# tio-shacl Public Migration Plan

Migration of the internal Ericsson tio-shacl package to a public, IPR-safe repository using TDD.

## Principles

1. **No TIO ontology redistribution** — user obtains TIO 3.6.0 from TM Forum; we ship a patch
2. **No git history** — fresh repo, clean-room rewrite of Python code
3. **Test-driven** — tests land first (from our test-cases), code follows until green
4. **Modern tooling** — pyenv + uv, no poetry/pip/setuptools
5. **Professional docs** — README, CONTRIBUTING, architecture, setup guide

---

## Repository Structure

```
tio-shacl/
├── .python-version              # pyenv: 3.11.x
├── pyproject.toml               # uv-managed, hatchling build
├── uv.lock                      # pinned deps
├── Makefile                     # dev shortcuts
├── LICENSE                      # Apache-2.0
├── README.md                    # public-facing docs
├── CONTRIBUTING.md              # how to contribute
├── MIGRATION_PLAN.md            # this file
│
├── docs/
│   ├── setup.md                 # full setup guide (TIO download, patch, pyenv, uv)
│   ├── architecture.md          # system design
│   └── validation-report.md     # generated coverage report
│
├── patches/
│   └── tio-3.6.0-fixes.patch   # applied to user's TIO download
│
├── rdf/
│   ├── shapes/                  # SHACL shapes (16 modules + extensions/)
│   └── lib/                     # reusable constraints, functions, targets
│
├── extensions/                  # TIO ontology extensions (our work)
│   ├── ConstraintModelExtension.ttl
│   ├── ContainerTypedExtension.ttl
│   ├── EvaluableActionableExtensions.ttl
│   ├── IntentOperandExtension.ttl
│   ├── RequirementCapabilityExtension.ttl
│   └── ValidityCandidateExtension.ttl
│
├── test-cases/                  # validation test cases (good/bad TTL)
│   ├── CompleteIntents/
│   ├── IntentCommonModel/
│   ├── ... (16 modules)
│   └── PreferenceOfHandlingOutcomes/
│
├── java_wrappers/               # Jena + TopBraid CLI (Apache-licensed)
│   ├── pom.xml
│   ├── mvnw / .mvn/
│   ├── jena-cli/
│   └── topbraid-cli/
│
├── sparql/                      # SPARQL queries
│
├── scripts/
│   └── setup_tio.sh             # download TIO 3.6.0 + apply patch
│
├── src/tio_shacl/               # Python package (clean rewrite)
│   ├── __init__.py
│   ├── cli.py                   # click CLI
│   ├── api.py                   # FastAPI (optional dep)
│   ├── mcp_server/              # MCP server (optional dep)
│   ├── core/                    # graph loading, path resolution
│   └── validation/              # runner, orchestrator, backends
│
└── tests/                       # pytest suite
    ├── conftest.py
    ├── test_validation.py       # parametrized over test-cases/
    ├── test_cli.py
    ├── test_api.py
    └── test_resources.py
```

---

## IPR Strategy

| Asset | Source | Ship? | Rationale |
|-------|--------|-------|-----------|
| TIO ontology .ttl files | TM Forum | ❌ | IPR — user downloads from TMF |
| tio-3.6.0-fixes.patch | Our work | ✅ | Bugfixes we authored |
| SHACL shapes (rdf/) | Our work | ✅ | Original validation rules |
| Extensions (extensions/) | Our work | ✅ | Original ontology extensions |
| Test cases (test-cases/) | Our work | ✅ | Original test data |
| Java wrappers | Our code + Apache deps | ✅ | Apache-2.0 licensed |
| Python source | Our work | ✅ | Clean rewrite, no history |

### TIO Ontology Setup (for users)

```bash
# 1. Download TIO 3.6.0 from TM Forum (requires free account)
#    Place files in ./ontology/ (gitignored)

# 2. Apply our bugfix patch
cd ontology/
patch -p1 < ../patches/tio-3.6.0-fixes.patch
```

We provide `scripts/setup_tio.sh` to automate step 2 (user still downloads manually).

---

## TDD Migration Phases

### Phase 0: Scaffold (no code yet)

- [x] Create repo structure
- [ ] `pyproject.toml` with deps, build config, tool config
- [ ] `.python-version` → `3.11`
- [ ] `Makefile` with install/test/lint/format targets
- [ ] `.gitignore` (ontology/, .venv/, __pycache__/, etc.)
- [ ] Copy static assets: `rdf/`, `extensions/`, `test-cases/`, `java_wrappers/`, `sparql/`, `patches/`
- [ ] Write `scripts/setup_tio.sh`
- [ ] Write `README.md`, `CONTRIBUTING.md`, `docs/setup.md`

### Phase 1: Test Infrastructure (RED)

Write tests that exercise the validation framework against test-cases/. All tests fail because no Python code exists yet.

```python
# tests/test_validation.py — parametrized
@pytest.mark.parametrize("case", discover_good_cases())
def test_good_case_conforms(case):
    """Good TTL files must pass SHACL validation."""
    result = validate(case)
    assert result.conforms

@pytest.mark.parametrize("case", discover_bad_cases())
def test_bad_case_violates(case):
    """Bad TTL files must fail SHACL validation."""
    result = validate(case)
    assert not result.conforms
```

Tests to write:
- `test_validation.py` — all 133+ test cases (good/bad) parametrized
- `test_resources.py` — path resolution (shapes, lib, extensions, ontology)
- `test_cli.py` — CLI commands (test, validate, report)
- `test_api.py` — REST API endpoints

### Phase 2: Core Implementation (GREEN)

Port code module by module until tests pass:

1. **`__init__.py`** — path resolution (get_shapes_dir, get_ontologies_dir, etc.)
2. **`core/`** — graph loading, ontology + shapes union graph
3. **`validation/runner.py`** — single-file validation (pyshacl backend)
4. **`validation/orchestrator.py`** — test suite discovery + parallel execution
5. **`cli.py`** — click commands wrapping the above

Order is driven by test dependencies: resource tests → validation tests → CLI tests.

### Phase 3: Extended Features

- API server (FastAPI)
- MCP server
- Java validator backends (TopBraid, Jena)
- HTML/JUnit report generation
- Coverage report script

### Phase 4: Documentation & Polish

- `docs/architecture.md` — design decisions, data flow
- `docs/setup.md` — complete setup walkthrough
- CI configuration (GitHub Actions)
- Badge in README (tests passing, Python version)

---

## Tooling Configuration

### pyenv

```
# .python-version
3.11
```

### uv (pyproject.toml)

```toml
[project]
name = "tio-shacl"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "rdflib>=7.1.4",
    "pyshacl>=0.30.1",
    "psutil>=6.1.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "click>=8.0.0",
]

[project.optional-dependencies]
api = ["fastapi>=0.115.0", "uvicorn>=0.32.0"]
mcp = ["fastmcp>=0.2.0"]

[dependency-groups]
dev = ["pytest>=8.0.0", "ruff>=0.12.0", "mypy>=1.12.0", "pre-commit>=4.1.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Makefile

```makefile
.PHONY: install test lint format type-check clean setup-tio

install:
	uv sync --all-extras --all-groups

test:
	uv run pytest

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

type-check:
	uv run mypy src/tio_shacl/

setup-tio:
	bash scripts/setup_tio.sh

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
```

---

## Key Differences from Internal Version

| Aspect | Internal | Public |
|--------|----------|--------|
| TIO ontology | Sibling repo, always available | User downloads + patches |
| Python version mgmt | implicit | pyenv `.python-version` |
| Package manager | uv (no lock committed) | uv with `uv.lock` committed |
| Test cases | in-package symlink | shipped directly in repo |
| Git history | full | none (fresh start) |
| CI | GitLab CI | GitHub Actions |
| Docs | minimal README | full markdown docs |
| License | Apache-2.0 | Apache-2.0 |

---

## Migration Checklist

- [ ] Phase 0: scaffold complete, static assets copied
- [ ] Phase 1: all tests written (RED — failing)
- [ ] Phase 2: core validation passing (GREEN)
- [ ] Phase 3: CLI, API, MCP working
- [ ] Phase 4: docs complete, CI green
- [ ] Tag v1.0.0
