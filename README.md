# tio-shacl

SHACL shapes and a Python validation framework for the **TM Forum Intent Ontology (TIO) v3.6.0**.

This repository contains:

- **SHACL shapes** (`rdf/shapes/`) that validate RDF intent documents against the TIO structural rules.
- **Ontology extensions** (`extensions/`) that cover gaps in the base TIO for real-world use.
- **Test cases** (`test-cases/`) — 133 good/bad examples across the 16 TIO modules.
- **A patch** (`patches/tio-3.6.0-fixes.patch`) that fixes known bugs in the upstream TIO 3.6.0.
- **A Python package** (`tio_shacl`) with a CLI, REST API, and MCP server for running validation.
- **Java CLI wrappers** (`java_wrappers/`) for running validation with TopBraid SHACL or Apache Jena as alternatives to pyshacl.

---

## Why this exists

TIO 3.6.0 defines intent semantics in OWL/RDFS but has no machine-checkable validation rules. `tio-shacl` fills that gap with SHACL shapes, a reference validator, and a shared test suite that both pyshacl and Jena/TopBraid pass.

The project also ships bugfixes for the TIO 3.6.0 release (missing class declarations, wrong domain types) as a patch that you apply to your local copy of the ontology.

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/earejma/tio-shacl.git
cd tio-shacl

# 2. Install Python deps (requires pyenv + uv)
make install

# 3. Download TIO 3.6.0 from TM Forum and place the .ttl files in ./ontology/
#    (see docs/setup.md for the download link and file list)

# 4. Apply our bugfix patch
make setup-tio

# 5. Run the test suite
make test
```

---

## Repository layout

```
tio-shacl/
├── rdf/shapes/            SHACL shapes for 16 TIO modules
├── rdf/lib/               Reusable SHACL constraints, functions, targets
├── extensions/            Ontology extensions (RequirementCapability, etc.)
├── test-cases/            133 good/bad intent TTLs for validation
├── patches/               Bugfix patch for TIO 3.6.0
├── sparql/                Ad-hoc SPARQL queries
├── java_wrappers/         Jena + TopBraid CLI wrappers
├── scripts/               Setup and utility scripts
├── src/tio_shacl/         Python package
├── tests/                 pytest suite
└── docs/                  Setup guide, architecture
```

---

## Documentation

- **[docs/setup.md](docs/setup.md)** — step-by-step setup including TIO download
- **[docs/architecture.md](docs/architecture.md)** — how the validator is put together
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — development workflow, test layout, PR process
- **[MIGRATION_PLAN.md](MIGRATION_PLAN.md)** — plan for the clean-room public rewrite

---

## IPR note

We do **not** redistribute the TIO ontology files. They are published by TM Forum under their own licensing terms. You must download them yourself from <https://www.tmforum.org/intent-ontology/> and let our `scripts/setup_tio.sh` apply the bugfix patch.

Everything else in this repo (SHACL shapes, extensions, test cases, Python code, Java wrappers) is original work under **Apache-2.0**.

---

## Status

This repository is in active migration from an internal Ericsson codebase. See [MIGRATION_PLAN.md](MIGRATION_PLAN.md) for the roadmap. Until it is complete, the Python package is not yet functional — only the static SHACL shapes and test cases are ready.

---

## License

[Apache-2.0](LICENSE)
