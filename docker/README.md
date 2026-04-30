# Docker demo

This directory, together with the top-level `Dockerfile` and `.dockerignore`,
packages `tio-shacl` into a reproducible container that exercises all three
SHACL backends (pyshacl, TopBraid, Jena) end-to-end on the shipped test cases.

The image is deliberately a **demonstration**, not a production artefact — it
optimises for "one command to see everything work" rather than minimal size or
hardening. Treat it as a worked example you can fork into your own deployment.

---

## Quick start

```bash
# 1. Build (takes a few minutes the first time — Maven downloads + shade).
docker build -t tio-shacl:demo .

# 2. Run. The TIO 3.6.0 ontology must be mounted at /opt/tio-shacl/ontology.
docker run --rm \
    -v "$PWD/ontology":/opt/tio-shacl/ontology:ro \
    tio-shacl:demo
```

The default command is `docker/demo.sh`, which runs through:

1. Validate a shipped *good* case with **pyshacl**, **TopBraid**, **Jena**.
2. Validate a shipped *bad* case with all three, confirming every backend
   reports violations and exits non-zero.
3. Exercise the `-O` repeatable flag with a synthesised custom catalogue dir.
4. Exercise the same composition via `TIO_ONTOLOGY_DIR="dir1:dir2"`.

All three backends are expected to produce the **same pass/fail verdict and
the same violation count** on every case — this is the cross-backend
consistency invariant the project guarantees (see `docs/architecture.md`).

---

## Why the image is laid out this way

### Multi-stage build

Stage 1 (`java-build`, `maven:3.9-eclipse-temurin-17`) compiles the two
Java validator jars from sources. Stage 2 (`runtime`, `python:3.11-slim`)
copies *only* the finished jars across, so the runtime image does not carry
Maven, the JDK, or transitive Maven deps. Net: the Python+JRE runtime image
weighs ~560 MB; a single-stage variant that kept Maven around would roughly
double that.

### Separate `COPY` for POMs and `src/`

Inside `java-build` the POM files are copied *before* the Java sources, and
`mvn dependency:go-offline` runs in its own layer. That means source-only
edits reuse the cached Maven artefact download layer and don't retrigger the
multi-hundred-megabyte resolution step.

### `--mount=type=cache,target=/root/.m2`

Maven artefacts are mounted from a persistent build cache (BuildKit feature),
so a cold CI build pays the network cost once; local rebuilds after a
`pom.xml` change still reuse anything already fetched. Requires
`DOCKER_BUILDKIT=1` (the default on Docker 23+) and the `# syntax=…` directive
at the top of the Dockerfile.

### `mvn` instead of `./mvnw`

The `maven:3.9-eclipse-temurin-17` base image sets
`MAVEN_CONFIG=/root/.m2`. The Maven Wrapper (`mvnw`) forwards `MAVEN_CONFIG`
to Maven as a positional argument, and Maven reads it as a lifecycle phase —
which fails with `Unknown lifecycle phase "/root/.m2"`. Using the base
image's `mvn` directly avoids the quirk. Host-side builds still use `mvnw`
via `make java-build`, which is the supported path for developers without
Maven installed locally.

### JRE 21, not JRE 17

The jars are compiled with `maven.compiler.target=17` but run fine on JRE
21. Debian 13 (trixie, what `python:3.11-slim` is built on today) dropped
`openjdk-17-jre-headless` from its default repositories; pulling it back in
would require adding the Adoptium/Temurin apt repo. Running 17-targeted
bytecode on a 21 JRE is officially supported and is the cheapest path.

### `openjdk-21-jre-headless`, not full JRE

`-headless` excludes AWT/Swing dependencies. The validators do no GUI work,
so this saves ~60 MB of the image without changing behaviour.

### `uv sync --no-dev --frozen`

`--frozen` means "install exactly what's in `uv.lock`" — no resolver, no
network trips once the cache is warm. `--no-dev` skips the dev dependency
group (pytest, ruff, mypy, pre-commit) because the demo image is for running
the validator, not developing on it.

### `ENV PATH=/opt/tio-shacl/.venv/bin:…`

Adds the uv-managed virtualenv's `bin` directory to `PATH`, which means ad-
hoc invocations like `docker run --rm … tio-shacl:demo tio-shacl validate
my.ttl` work without having to prefix every command with `uv run`.

### Ontology is mounted, never baked in

The TIO 3.6.0 `.ttl` files are TM Forum assets under their own licensing
terms. We **must not** redistribute them, so they are deliberately excluded
from the build context via `.dockerignore` and expected to be bind-mounted at
run time. The demo script detects a missing or empty mount and prints a
clear error before attempting anything else.

### `.dockerignore` excludes `tests/`

The image is for running the validator, not the test suite — pytest and its
plugins are dev-only deps and the 133-case suite is better run on the host
during development. Excluding `tests/` shaves ~500 KB of context and keeps
the image focused.

---

## Extending this for your own setup

The image is intentionally small-surface so you can fork it. Common tweaks:

### Mount your own catalogue alongside TIO

```bash
docker run --rm \
    -v "$PWD/ontology":/opt/tio-shacl/ontology:ro \
    -v "$PWD/my-catalogue":/opt/tio-shacl/catalogue:ro \
    -e TIO_ONTOLOGY_DIR=/opt/tio-shacl/ontology:/opt/tio-shacl/catalogue \
    tio-shacl:demo tio-shacl validate my_intent.ttl
```

No rebuild needed — `TIO_ONTOLOGY_DIR` is the supported extension point.

### Validate your own intent file

```bash
docker run --rm \
    -v "$PWD/ontology":/opt/tio-shacl/ontology:ro \
    -v "$PWD/intents":/intents:ro \
    tio-shacl:demo tio-shacl validate /intents/my_intent.ttl
```

Because `PATH` includes the virtualenv's `bin`, the `tio-shacl` command is
available directly as the container's argv.

### Pick a specific backend

```bash
docker run --rm \
    -v "$PWD/ontology":/opt/tio-shacl/ontology:ro \
    -e TIO_VALIDATOR=jena \
    tio-shacl:demo tio-shacl validate /path/to/intent.ttl
```

### Replace the demo script with your own entry point

```bash
docker run --rm \
    -v "$PWD/ontology":/opt/tio-shacl/ontology:ro \
    --entrypoint bash \
    tio-shacl:demo \
    -c "tio-shacl validate …"
```

Or, to bake a different default into your own fork, override the `CMD` in a
downstream Dockerfile:

```dockerfile
FROM tio-shacl:demo
COPY my-batch-validator.sh /usr/local/bin/
CMD ["/usr/local/bin/my-batch-validator.sh"]
```

### Build without the Java backends

If you only need pyshacl, drop the `java-build` stage and the JRE + jar
`COPY` lines. The image shrinks to roughly 250 MB and still exposes the
multi-directory ontology feature. You lose the ability to cross-check with
TopBraid/Jena — the invariant the demo is designed to showcase — so only do
this when size matters more than cross-engine confidence.

---

## What the image deliberately does *not* include

- **Test suite (`tests/`, pytest, pytest-xdist).** Run those on the host
  during development with `make test`.
- **Lint / type-check tools (ruff, mypy, pre-commit).** Dev-group only.
- **Maven / the JDK.** Stage-1 only; the runtime needs the JRE, not the
  compiler.
- **The TIO ontology.** IPR-restricted; must be mounted.
- **A web server / API layer.** Prior prototypes shipped FastAPI and an MCP
  server; both were removed as out of scope (see `docs/architecture.md`
  "Non-goals"). If you need an HTTP interface, wrap `ValidationRunner` in
  your own image.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ERROR: TIO ontology not mounted.` | Missing or empty mount at `/opt/tio-shacl/ontology`. | Mount your patched `./ontology` dir with `-v`. |
| Jena backend reports `0` violations on a known-bad case | The TIO ontology has not been patched (`make setup-tio` on the host). | Re-run `make setup-tio` on the host *before* mounting. |
| `tio-shacl: command not found` when overriding CMD with `bash -c …` | Shell rule: the command inherits the image's env only through subprocesses, and some shells reset `PATH`. | Use the explicit path: `/opt/tio-shacl/.venv/bin/tio-shacl`, or keep the default entry point. |
| Build fails at `mvn dependency:go-offline` with "Could not resolve dependencies" | Corporate proxy blocks Maven Central. | Configure `~/.m2/settings.xml` on the host and pass it into the build with `--secret` + a custom stage. |
