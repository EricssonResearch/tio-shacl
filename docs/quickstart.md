# Quickstart

This guide assumes you have completed [setup](setup.md) (Python deps installed, TIO ontology in `ontology/`, patch applied).

---

## Walkthrough: validate your first intent

The CLI has three subcommands:

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
[`test-cases/CompleteIntents/good/scenario-intent-validity-guarantee.ttl`](../test-cases/CompleteIntents/good/scenario-intent-validity-guarantee.ttl).

---

## Using a custom ontology or catalogue

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
