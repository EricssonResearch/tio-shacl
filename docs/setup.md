# Setup guide

This guide walks through every step to get a working `tio-shacl` development environment.

## Prerequisites

| Tool | Minimum | Install command |
|------|---------|-----------------|
| pyenv | 2.4 | <https://github.com/pyenv/pyenv#installation> |
| uv | 0.5 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git | 2.30 | OS package manager |
| Java | 17 (optional) | OS package manager |

---

## 1. Install Python 3.11

The repo pins Python 3.11 via `.python-version`. Install it once with pyenv:

```bash
pyenv install 3.11
pyenv versions   # confirm 3.11.x shows up
```

When you `cd` into the repo, pyenv switches to 3.11 automatically.

---

## 2. Clone the repository

```bash
git clone https://github.com/earejma/tio-shacl.git
cd tio-shacl
python --version   # should print Python 3.11.x
```

---

## 3. Install dependencies

`uv` reads `pyproject.toml`, creates a `.venv`, and installs the locked deps:

```bash
make install
# equivalent to: uv sync --all-extras --all-groups
```

This pulls in:

- `rdflib`, `pyshacl` — RDF and SHACL engines
- `click` — CLI framework
- `pytest`, `ruff`, `mypy`, `pre-commit` — dev tools

Verify:

```bash
uv run python -c "import tio_shacl; print(tio_shacl.__version__)"
```

---

## 4. Obtain the TIO 3.6.0 ontology

**We do not redistribute the TIO ontology files.** They are TM Forum assets under their own licensing terms. You must download them directly.

### Steps

1. Go to <https://www.tmforum.org/intent-ontology/>
2. Sign in (free TM Forum account required).
3. Download **TIO release 3.6.0**.
4. Extract the archive — you should see 15 `.ttl` files:

   ```
   FunctionOntology.ttl           IntentProbing.ttl              MetricsAndObservations.ttl
   IntentCommonModel.ttl          IntentSpecification.ttl        PreferenceOfHandlingOutcomes.ttl
   IntentGuaranteeOntology.ttl    IntentValidityOntology.ttl     ProposalBestIntent.ttl
   IntentManagementOntology.ttl   LogicalOperators.ttl           QuantityOntology.ttl
   MathFunctions.ttl              SetOperators.ttl               Utility.ttl
   ```

5. Create an `ontology/` directory in the repo root and place the 15 files there:

   ```bash
   mkdir -p ontology
   cp /path/to/downloaded/tio/*.ttl ontology/
   ```

The `ontology/` directory is git-ignored, so you will never accidentally commit TIO files.

---

## 5. Apply the bugfix patch

TIO 3.6.0 has a few known issues (wrong domain classes, a missing `rdfs:Class` declaration). We ship a patch that fixes them.

```bash
make setup-tio
```

The script:

1. Checks that all 15 TIO files are present in `ontology/`.
2. Detects whether the patch is already applied (idempotent).
3. Dry-runs the patch to ensure it applies cleanly.
4. Applies it, creating `.orig` backups of the originals.

After this, your `ontology/` directory is ready for validation.

### Custom ontology location

If you prefer to keep the ontology elsewhere:

```bash
bash scripts/setup_tio.sh /path/to/my/tio-3.6.0
```

Then set `TIO_ONTOLOGY_DIR=/path/to/my/tio-3.6.0` in a `.env` file or your shell.

---

## 6. Build the Java validators (optional)

Only needed if you plan to run validation with TopBraid SHACL or Apache Jena.

```bash
make java-build
```

This produces:

- `java_wrappers/topbraid-cli/target/topbraid-shacl-cli.jar` (TopBraid SHACL 1.4.3)
- `java_wrappers/jena-cli/target/jena-shacl-cli.jar` (Apache Jena 5.2.0)

Without these, the Python package uses `pyshacl` for all validation. To pick a specific backend, set `TIO_VALIDATOR`:

```bash
TIO_VALIDATOR=topbraid tio-shacl validate my_intent.ttl
TIO_VALIDATOR=jena     tio-shacl validate my_intent.ttl
TIO_VALIDATOR=pyshacl  tio-shacl validate my_intent.ttl    # default
```

---

## 7. Run the test suite

```bash
make test
```

This runs:

- Unit tests for the Python package
- Parametrized validation tests over all 133 test cases in `test-cases/`

On a clean install, all tests should pass. If any fail, see the [troubleshooting](#troubleshooting) section.

---

## 8. Dev loop

```bash
make test-fast    # parallel pytest
make lint         # ruff
make format       # ruff format + autofix
make type-check   # mypy
```

Pre-commit hooks (optional):

```bash
uv run pre-commit install
```

---

## Troubleshooting

### `setup_tio.sh` says "Missing required TIO files"

Double-check you copied all 15 files into `ontology/`. File names are case-sensitive.

### `setup_tio.sh` says "Patch does not apply cleanly"

You likely have a different TIO version. Confirm you downloaded exactly **3.6.0**, not 3.5 or a later prerelease.

### `make test` fails with `FileNotFoundError: TIO ontology directory not found`

You have not run `make setup-tio` yet, or `ontology/` is missing the TIO files.

### Java build fails with `Could not resolve dependencies`

TopBraid and Jena artifacts are on Maven Central. Check your network and any corporate proxy settings in `~/.m2/settings.xml`.

---

## Next steps

- Read [architecture.md](architecture.md) to understand the validation pipeline.
- Read [../CONTRIBUTING.md](../CONTRIBUTING.md) to learn the TDD workflow for adding shapes or code.
