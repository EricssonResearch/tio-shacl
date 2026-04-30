# tio-shacl

SHACL shapes and a Python validation framework for the **TM Forum Intent Ontology (TIO) v3.6.0**.

This repository contains:

- **SHACL shapes** (`rdf/shapes/`) that validate RDF intent documents against the TIO structural rules.
- **Ontology extensions** (`extensions/`) that cover gaps in the base TIO for real-world use.
- **Test cases** (`test-cases/`) — 133 good/bad examples across the 16 TIO modules.
- **A patch** (`patches/tio-3.6.0-fixes.patch`) that fixes known bugs in the upstream TIO 3.6.0.
- **A Python package** (`tio_shacl`) with a CLI for running validation through three interchangeable backends: **pyshacl** (default), **TopBraid SHACL**, and **Apache Jena**.
- **Java CLI wrappers** (`java_wrappers/`) that the TopBraid and Jena backends drive.

---

## Why this exists

TIO 3.6.0 defines intent semantics in OWL/RDFS but has no machine-checkable validation rules. `tio-shacl` fills that gap with SHACL shapes, a reference validator, and a shared test suite that both pyshacl and Jena/TopBraid pass.

The project also ships bugfixes for the TIO 3.6.0 release (missing class declarations, wrong domain types) as a patch that you apply to your local copy of the ontology.

---

## Quick start

### What you need to provide

`tio-shacl` combines three kinds of RDF graphs at validation time. Two of them
ship with the repo; the third is yours. Knowing which is which is usually the
thing that trips people up:

| Graph | Who provides it | Where it lives | Purpose |
|-------|-----------------|----------------|---------|
| **SHACL shapes** | *ships with this repo* | `rdf/shapes/`, `rdf/lib/`, `extensions/` | The validation rules. You do not edit these to validate your intents. |
| **TIO 3.6.0 ontology** | *you download from TM Forum* | `./ontology/` (git-ignored) | The class/property definitions your intents reference. Required. |
| **Intent document** *(your input)* | *you write* | anywhere — pass the path to the CLI | The RDF file describing the intent you want to check. |

Optionally, you can also add:

- **Custom ontology extensions / catalogues** (e.g. your own service model or
  vocabulary) — point `TIO_ONTOLOGY_DIR` at a directory containing both the TIO
  files and your extra `.ttl` files. Everything in that directory is loaded
  into the data graph at validation time.
- **Custom SHACL shapes** — drop additional `.ttl` files into `rdf/shapes/` or
  `extensions/` (or point `TIO_SHAPES_DIR` at your own directory). The runner
  loads every `.ttl` under the shapes directory.

You do **not** need to understand or modify the SHACL shapes to validate an
intent — treat them as a library. You only author the intent document.

### Install and set up

```bash
# 1. Clone
git clone https://github.com/earejma/tio-shacl.git
cd tio-shacl

# 2. Install Python deps (requires pyenv + uv — see docs/setup.md)
make install

# 3. Download TIO 3.6.0 from TM Forum and place the 15 .ttl files in ./ontology/
#    Requires a free TM Forum account. See docs/setup.md for the download URL
#    and the exact file list.

# 4. Apply the TIO 3.6.0 bugfix patch (idempotent; safe to re-run)
make setup-tio

# 5. Smoke-test: run the bundled 133 good/bad cases
make test
```

### Walkthrough: validate your first intent

Once setup is complete, the CLI has three subcommands:

```bash
tio-shacl --help
#   validate   Validate a single RDF file.
#   test       Run validation test suites.
#   report     Emit a report from the most recent 'test' run.
```

**1. Validate a known-good intent from the bundled test cases.**

This confirms the toolchain works end-to-end before you point it at your own
file:

```bash
uv run tio-shacl validate test-cases/IntentCommonModel/good/class-expectations.ttl
# ✓ test-cases/IntentCommonModel/good/class-expectations.ttl: conforms
```

**2. Validate a known-bad intent to see what a violation looks like.**

```bash
uv run tio-shacl validate test-cases/IntentCommonModel/bad/expectation-target-violation.ttl
# ✗ test-cases/IntentCommonModel/bad/expectation-target-violation.ttl: 1 violation(s)
#   [1] http://example.org/bad_expectation — Value does not have class icm:Target
```

Add `-v` / `--verbose` to see the full SHACL report (focus node, source shape,
constraint component, severity) for each violation.

**3. Validate your own intent.**

Write an intent that references TIO classes via their IRIs. A minimal
well-formed intent looks like this:

```turtle
# my_intent.ttl
@prefix ex:  <http://example.org/> .
@prefix icm: <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix log: <http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:my_target      a icm:Target .

ex:my_expectation a icm:DeliveryExpectation ;
    icm:target ex:my_target .

ex:my_intent      a icm:Intent ;
    rdfs:label "Example intent"@en ;
    log:allOf ( ex:my_expectation ) .
```

Validate it:

```bash
uv run tio-shacl validate my_intent.ttl
# ✓ my_intent.ttl: conforms
```

For a richer example that exercises multiple TIO modules (validity, guarantees,
quantities), see
[`test-cases/CompleteIntents/good/scenario-intent-validity-guarantee.ttl`](test-cases/CompleteIntents/good/scenario-intent-validity-guarantee.ttl).

### Using a custom ontology or catalogue

If your intent references concepts from your own service catalogue or a
domain-specific ontology, the runner needs to see those definitions at the
same time as TIO — otherwise SHACL cannot resolve class membership or
`rdfs:domain` / `rdfs:range` against your vocabulary.

Point the CLI at both directories — TIO and your catalogue — with the
repeatable `-O` / `--ontology-dir` flag:

```bash
uv run tio-shacl validate \
    -O ./ontology \
    -O ~/tio-src/tio-catalog \
    my_intent.ttl
```

You can pass `-O` as many times as you need (one per directory). Every `.ttl`
found in each directory is unioned into the ontology graph. No copying or
symlinking required.

The same composition also works via the environment, using `os.pathsep`
(`:` on Unix, `;` on Windows) to separate directories:

```bash
export TIO_ONTOLOGY_DIR="$PWD/ontology:$HOME/tio-src/tio-catalog"
uv run tio-shacl validate my_intent.ttl
```

From Python:

```python
from tio_shacl.validation import ValidationRunner

runner = ValidationRunner(ontology_dirs=[
    "ontology",
    "/home/me/tio-src/tio-catalog",
])
result = runner.validate_file("my_intent.ttl")
```

`owl:imports` inside your intent is still not followed automatically — the
catalogue has to be reachable through one of the ontology directories you
pass.

### Switching SHACL backends

By default validation runs through `pyshacl`. To cross-check with another
engine:

```bash
TIO_VALIDATOR=topbraid uv run tio-shacl validate my_intent.ttl
TIO_VALIDATOR=jena     uv run tio-shacl validate my_intent.ttl
```

`topbraid` and `jena` require Java 17+ and `make java-build` once. All three
backends are expected to produce the same verdict on every intent — if they
don't, please open an issue.

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

## Validator backends

The Python runner can drive three SHACL implementations through a single interface. Select one with the `TIO_VALIDATOR` environment variable:

| Backend | Value | Ships with | Notes |
|---------|-------|------------|-------|
| pyshacl | `pyshacl` *(default)* | Python package | No extra setup. |
| TopBraid SHACL 1.4.3 | `topbraid` | `java_wrappers/topbraid-cli.jar` | Requires Java 17+ and `make java-build`. |
| Apache Jena 5.2.0 | `jena` | `java_wrappers/jena-cli.jar` | Requires Java 17+. Ships with a generic SHACL-AF polyfill — see below. |

```bash
TIO_VALIDATOR=topbraid tio-shacl validate my_intent.ttl
```

### Jena SHACL-AF polyfill

Apache Jena's SHACL engine does not implement parameterised `sh:SPARQLTargetType`, which is part of the [SHACL Advanced Features](https://www.w3.org/TR/shacl-af/#SPARQLTargetType) specification. Our Jena CLI wrapper (`java_wrappers/jena-cli/`) includes a generic polyfill (`SparqlTargetTypePolyfill.java`) that rewrites every target-type instance into an inline `sh:SPARQLTarget` by substituting the bound parameters into the target type's `sh:select` template. This is a faithful application of SHACL-AF §4.2 and is not TIO-specific — any third-party `sh:SPARQLTargetType` with a `sh:select` template and declared `sh:parameter`s will be handled.

The conversion is performed by the jar itself, not by the Python runner, so invoking the jar directly (outside of `tio-shacl`) also produces correct results on AF-tier shapes.

---

## IPR note

We do **not** redistribute the TIO ontology files. They are published by TM Forum under their own licensing terms. You must download them yourself from <https://projects.tmforum.org/wiki/pages/viewpageattachments.action?pageId=328567625> (free TM Forum account required) and let our `scripts/setup_tio.sh` apply the bugfix patch.

Everything else in this repo (SHACL shapes, extensions, test cases, Python code, Java wrappers) is original work by Ericsson Research under the **MIT License**.

---

## Status

This repository is in active migration from an internal Ericsson codebase. See [MIGRATION_PLAN.md](MIGRATION_PLAN.md) for the roadmap. Until it is complete, the Python package is not yet functional — only the static SHACL shapes and test cases are ready.

---

## License

[MIT](LICENSE) — Copyright (c) 2025 Ericsson Research
