# Architecture

High-level design of `tio-shacl`.

---

## What the project does

Given an RDF document describing a TM Forum intent, decide whether it conforms to the TIO 3.6.0 structural rules, and report any violations.

Two implementations exist in the ecosystem — `tio-shacl` (SHACL, Python) and `tio-reasoner` (Datalog, Go). This repository covers the SHACL side.

---

## Data flow

```
┌───────────────────────┐        ┌──────────────────────┐
│  User intent .ttl     │        │  TIO 3.6.0 ontology  │
│  (input)              │        │  (patched)           │
└──────────┬────────────┘        └──────────┬───────────┘
           │                                │
           │       ┌────────────────────────┤
           │       │                        │
           ▼       ▼                        ▼
     ┌────────────────────┐         ┌──────────────────┐
     │  union data graph  │         │  union shapes    │
     │  (input + TIO)     │         │  graph           │
     │                    │         │  - rdf/shapes/   │
     │                    │         │  - rdf/lib/      │
     │                    │         │  - extensions/   │
     └─────────┬──────────┘         └────────┬─────────┘
               │                             │
               └──────────┬──────────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ SHACL validator │
                 │ (pyshacl /      │
                 │  Jena /         │
                 │  TopBraid)      │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ ValidationReport│
                 │ - conforms: bool│
                 │ - violations: [] │
                 └─────────────────┘
```

---

## Module layout

```
src/tio_shacl/
├── __init__.py          Path helpers (get_shapes_dir, get_ontologies_dir, …)
├── cli.py               click-based CLI entry point
├── core/                Graph loading, path resolution
│   └── loader.py        Build union data / shapes graphs from disk
└── validation/
    ├── runner.py        Validate a single TTL file
    ├── orchestrator.py  Discover and run full test suites in parallel
    └── backends/
        ├── pyshacl.py   Default backend
        ├── jena.py      Wraps java_wrappers/jena-cli
        └── topbraid.py  Wraps java_wrappers/topbraid-cli
```

### Responsibilities

- **`__init__.py`** — Resolve paths for installed-package and dev-mode layouts. Single source of truth for where RDF assets live.
- **`core/loader.py`** — Pure function: `load_graphs(...) -> GraphSet`. Caches the parsed graphs so repeated validations do not re-parse.
- **`validation/runner.py`** — Thin wrapper: pick a backend via `TIO_VALIDATOR`, call it, return a typed `ValidationResult`.
- **`validation/orchestrator.py`** — Walk `test-cases/`, fan out to a pool of workers, aggregate results.
- **`validation/backends/`** — Each backend exports a single `validate(data_graph, shapes_graph) -> ValidationResult`. The Java backends serialise the graphs to temp files and invoke the CLI jar; the pyshacl backend calls the library directly.

---

## Shapes layout

Our SHACL shapes mirror the TIO module structure so reviewers can pair each shape file to the ontology module it validates.

```
rdf/
├── shapes/
│   ├── FunctionOntology.ttl              Function, argument types
│   ├── IntentCommonModel.ttl             Intent, Expectation, Target
│   ├── IntentGuaranteeOntology.ttl       Guarantees
│   ├── … (16 total, one per TIO module)
│   └── extensions/
│       └── RequirementCapabilityExtension.ttl
└── lib/
    ├── GlobalShapes.ttl                  Cross-cutting shapes
    ├── TargetTypes.ttl                   sh:target helpers
    ├── MetaShapes.ttl                    Shapes that validate shapes
    ├── constraints/                       Reusable constraint blocks
    └── functions/                         Reusable SHACL-SPARQL functions
```

---

## Extensions

`extensions/` contains non-normative shapes that cover intent patterns not fully captured by TIO 3.6.0:

| File | Purpose |
|------|---------|
| `ConstraintModelExtension.ttl` | Richer constraint expressions |
| `ContainerTypedExtension.ttl` | Typed container semantics |
| `EvaluableActionableExtensions.ttl` | Evaluable and actionable conditions |
| `IntentOperandExtension.ttl` | Operand typing for complex expressions |
| `RequirementCapabilityExtension.ttl` | Requirement/capability alignment |
| `ValidityCandidateExtension.ttl` | Validity candidate selection |

These are loaded alongside the base shapes by default; users can opt out by passing `--no-extensions` to the CLI.

---

## Test case layout

```
test-cases/<ModuleName>/
├── good/   # must pass validation
│   └── *.ttl
└── bad/    # must fail validation
    ├── *.ttl
    └── *.expected.json   # optional: expected focus nodes / constraint IDs
```

The orchestrator discovers every `*.ttl` under `test-cases/`, validates it, and checks the outcome against the `good/` or `bad/` directory convention.

---

## Validator backends

| Backend | How invoked | When to use |
|---------|-------------|-------------|
| `pyshacl` | Python library call | Default; no extra setup |
| `topbraid` | `java -jar topbraid-shacl-cli.jar …` | Reference implementation; passes all TIO test cases |
| `jena` | `java -jar jena-shacl-cli.jar …` | Benchmarking; errors on TIO's parameterised SPARQL targets (see README) |

The pyshacl and TopBraid backends must produce the same pass/fail verdict on every test case. The Jena backend is best-effort. This is enforced by the test suite when `TIO_VALIDATOR` cycles through each backend in CI.

---

## Configuration

`tio-shacl` reads configuration from (in order of precedence):

1. CLI flags
2. Environment variables
3. `.env` file in repo root (via `python-dotenv`)

| Variable | Default | Meaning |
|----------|---------|---------|
| `TIO_VALIDATOR` | `pyshacl` | Backend: `pyshacl`, `topbraid`, `jena` |
| `TIO_ONTOLOGY_DIR` | `./ontology` | Where TIO 3.6.0 .ttl files live |
| `TIO_SHAPES_DIR` | packaged | Override for custom shape sets |

---

## Non-goals

- **No REST API or MCP server bundled.** Early prototypes shipped a FastAPI app and a Model Context Protocol server. Both were removed — users who need an HTTP/MCP interface can wrap :class:`ValidationRunner` in their own service, which is 20 lines of code.
- **Not a TIO reasoner.** Validation produces a yes/no + violation list. Entailment, derivation, and intent composition are out of scope.
- **Not a runtime intent engine.** Evaluating whether live telemetry meets an intent is `tio-reasoner`'s job.
- **Not a TIO editor.** Authoring tools live in separate projects.
