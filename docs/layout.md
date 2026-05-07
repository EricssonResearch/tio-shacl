# Repository layout

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

## Key directories

### `rdf/shapes/`

One `.ttl` file per TIO module (16 total). Each file contains the SHACL `NodeShape` and `PropertyShape` declarations that enforce the structural rules for that module.

### `rdf/lib/`

Shared building blocks used across multiple shape files:

- `GlobalShapes.ttl` — cross-cutting shapes (e.g. every node must have `rdf:type`)
- `TargetTypes.ttl` — reusable `sh:SPARQLTargetType` definitions
- `MetaShapes.ttl` — shapes that validate other shapes (meta-validation)
- `constraints/` — reusable constraint components
- `functions/` — reusable SHACL-SPARQL functions

### `extensions/`

Non-normative shapes that cover intent patterns not fully captured by TIO 3.6.0:

| File | Purpose |
|------|---------|
| `ConstraintModelExtension.ttl` | Richer constraint expressions |
| `ContainerTypedExtension.ttl` | Typed container semantics |
| `EvaluableActionableExtensions.ttl` | Evaluable and actionable conditions |
| `IntentOperandExtension.ttl` | Operand typing for complex expressions |
| `RequirementCapabilityExtension.ttl` | Requirement/capability alignment |
| `ValidityCandidateExtension.ttl` | Validity candidate selection |

### `test-cases/`

```
test-cases/<ModuleName>/
├── good/   # must pass validation
│   └── *.ttl
└── bad/    # must fail validation
    ├── *.ttl
    └── *.expected.json   # optional: expected focus nodes / constraint IDs
```

The test orchestrator discovers every `*.ttl` under `test-cases/`, validates it, and checks the outcome against the `good/` or `bad/` directory convention.

### `java_wrappers/`

Maven projects that build standalone CLI jars for the TopBraid and Jena backends. Each jar accepts a data graph and shapes graph on the command line and produces a SHACL validation report on stdout.

### `src/tio_shacl/`

The Python package. See [architecture.md](architecture.md) for module responsibilities.
