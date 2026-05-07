# tio-shacl

SHACL shapes and a Python validation framework for the **TM Forum Intent Ontology (TIO) v3.6.0**.

TIO 3.6.0 defines intent semantics in OWL/RDFS but has no machine-checkable validation rules. `tio-shacl` fills that gap with SHACL shapes, a reference validator, and a shared test suite that pyshacl, TopBraid, and Apache Jena all pass.

## Features

- **SHACL shapes** (`rdf/shapes/`) that validate RDF intent documents against the TIO structural rules.
- **Ontology extensions** (`extensions/`) that cover gaps in the base TIO for real-world use.
- **Test cases** (`test-cases/`) — 133 good/bad examples across the 16 TIO modules.
- **A patch** (`patches/tio-3.6.0-fixes.patch`) that fixes known bugs in the upstream TIO 3.6.0.
- **A Python package** (`tio_shacl`) with a CLI for running validation through three interchangeable backends: **pyshacl** (default), **TopBraid SHACL**, and **Apache Jena**.
- **Java CLI wrappers** (`java_wrappers/`) that the TopBraid and Jena backends drive.

## Quick start

```bash
# Clone and install
git clone https://github.com/EricssonResearch/tio-shacl.git
cd tio-shacl
make install

# Download TIO 3.6.0 from TM Forum, place the 15 .ttl files in ./ontology/
# (free TM Forum account required — see docs/setup.md for details)

# Apply bugfix patch and run the test suite
make setup-tio
make test

# Validate an intent
uv run tio-shacl validate test-cases/IntentCommonModel/good/class-expectations.ttl
```

## Documentation

| Page | Description |
|------|-------------|
| [docs/setup.md](docs/setup.md) | Full installation guide (pyenv, uv, TIO download, Java backends) |
| [docs/quickstart.md](docs/quickstart.md) | Walkthrough: validate your first intent, custom ontologies |
| [docs/backends.md](docs/backends.md) | Switching backends, Jena SHACL-AF polyfill |
| [docs/layout.md](docs/layout.md) | Repository structure and key directories |
| [docs/architecture.md](docs/architecture.md) | Internal design of the validation pipeline |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow, test layout, PR process |

## IPR note

We do **not** redistribute the TIO ontology files. They are published by TM Forum under their own licensing terms. You must download them yourself from <https://projects.tmforum.org/wiki/pages/viewpageattachments.action?pageId=328567625> (free TM Forum account required) and let our `scripts/setup_tio.sh` apply the bugfix patch.

Everything else in this repo (SHACL shapes, extensions, test cases, Python code, Java wrappers) is original work by Ericsson Research under the **MIT License**.

## License

[MIT](LICENSE) — Copyright (c) 2025 Ericsson Research
