# Validator backends

The Python runner can drive three SHACL implementations through a single interface. Select one with the `TIO_VALIDATOR` environment variable or the `--backend` CLI flag.

---

## Available backends

| Backend | Value | Ships with | Notes |
|---------|-------|------------|-------|
| pyshacl | `pyshacl` *(default)* | Python package | No extra setup. |
| TopBraid SHACL 1.4.3 | `topbraid` | `java_wrappers/topbraid-cli.jar` | Requires Java 17+ and `make java-build`. |
| Apache Jena 5.2.0 | `jena` | `java_wrappers/jena-cli.jar` | Requires Java 17+. Ships with a generic SHACL-AF polyfill — see below. |

```bash
TIO_VALIDATOR=topbraid tio-shacl validate my_intent.ttl
TIO_VALIDATOR=jena     tio-shacl validate my_intent.ttl
TIO_VALIDATOR=pyshacl  tio-shacl validate my_intent.ttl    # default
```

All three backends must produce the same pass/fail verdict on every test case. This is enforced by the test suite when `TIO_VALIDATOR` cycles through each backend in CI.

---

## Building the Java backends

```bash
make java-build
```

This produces:

- `java_wrappers/topbraid-cli/target/topbraid-shacl-cli.jar` (TopBraid SHACL 1.4.3)
- `java_wrappers/jena-cli/target/jena-shacl-cli.jar` (Apache Jena 5.2.0)

---

## Jena SHACL-AF polyfill

Apache Jena's SHACL engine does not implement parameterised `sh:SPARQLTargetType`, which is part of the [SHACL Advanced Features](https://www.w3.org/TR/shacl-af/#SPARQLTargetType) specification. Our Jena CLI wrapper (`java_wrappers/jena-cli/`) includes a generic polyfill (`SparqlTargetTypePolyfill.java`) that rewrites every target-type instance into an inline `sh:SPARQLTarget` by substituting the bound parameters into the target type's `sh:select` template. This is a faithful application of SHACL-AF section 4.2 and is not TIO-specific — any third-party `sh:SPARQLTargetType` with a `sh:select` template and declared `sh:parameter`s will be handled.

The conversion is performed by the jar itself, not by the Python runner, so invoking the jar directly (outside of `tio-shacl`) also produces correct results on AF-tier shapes.

---

## Cross-backend comparison

Use the bundled script to run all test cases through every backend and compare verdicts:

```bash
uv run python scripts/run_full_suite.py
```

This will report any disagreements between backends.
