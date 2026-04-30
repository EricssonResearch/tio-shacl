# syntax=docker/dockerfile:1.7
#
# tio-shacl demo image
# --------------------
#
# Multi-stage build that produces a runtime image containing the tio-shacl
# Python package plus the two Java validator jars (TopBraid + Jena) that the
# 'topbraid' and 'jena' backends drive.
#
# Build:
#     docker build -t tio-shacl:demo .
#
# Run (TIO ontology must be mounted — IPR prevents bundling it):
#     docker run --rm -v "$PWD/ontology":/opt/tio-shacl/ontology:ro tio-shacl:demo
#
# The default command is a demo script that exercises all three SHACL backends
# on a good case, a bad case, and the new -O multi-directory ontology feature.

# =============================================================================
# Stage 1: build the Java validator jars
# =============================================================================
FROM maven:3.9-eclipse-temurin-17 AS java-build

WORKDIR /build

# Copy just the Maven project files first so Docker can cache the dep download
# layer independently of source changes.
#
# We use the base image's 'mvn' rather than './mvnw' because the base image
# sets MAVEN_CONFIG=/root/.m2, which mvnw would forward to Maven as a
# positional argument (interpreted as a lifecycle phase → failure).
COPY java_wrappers/pom.xml ./pom.xml
COPY java_wrappers/topbraid-cli/pom.xml ./topbraid-cli/pom.xml
COPY java_wrappers/jena-cli/pom.xml ./jena-cli/pom.xml

# Warm the local Maven cache — this layer is reused as long as the POM files
# don't change.
RUN --mount=type=cache,target=/root/.m2 mvn -q -DskipTests dependency:go-offline || true

# Now copy sources and build the shaded jars.
COPY java_wrappers/topbraid-cli/src ./topbraid-cli/src
COPY java_wrappers/jena-cli/src ./jena-cli/src

RUN --mount=type=cache,target=/root/.m2 mvn -q -DskipTests package


# =============================================================================
# Stage 2: runtime image
# =============================================================================
FROM python:3.11-slim AS runtime

# JRE for the Java backends, plus the patch tool for setup_tio.sh and curl
# for the uv installer. Everything else is intentionally left out — no pytest,
# no mvn, no compiler toolchain.
#
# Note: the jars are compiled with maven.compiler.target=17 but run fine on
# JRE 21 (the Debian 13 / trixie default). Stick with 21 to avoid pulling in
# the Temurin repository dance just for a JRE.
RUN apt-get update -qq \
 && DEBIAN_FRONTEND=noninteractive apt-get install -qq -y --no-install-recommends \
        curl \
        ca-certificates \
        patch \
        openjdk-21-jre-headless \
 && rm -rf /var/lib/apt/lists/*

# Install uv (pinned release for reproducibility; bump as needed).
ENV UV_INSTALL_DIR=/usr/local/bin
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL=/usr/local/bin sh \
 && uv --version

WORKDIR /opt/tio-shacl

# Copy Python project metadata first so 'uv sync' is cached across source changes.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Copy the SHACL rules, extensions, test cases, patches, and scripts the
# runtime actually needs. Intentionally excluded: tests/, java_wrappers/src,
# Maven tooling, the sparql/ draft dir, docs/, etc.
COPY rdf ./rdf
COPY extensions ./extensions
COPY test-cases ./test-cases
COPY patches ./patches
COPY scripts ./scripts

# Pre-built jars from stage 1. Land them where jar_path() looks:
#   <repo>/java_wrappers/<jena|topbraid>-cli/target/<name>-shacl-cli.jar
COPY --from=java-build /build/jena-cli/target/jena-shacl-cli.jar \
     ./java_wrappers/jena-cli/target/jena-shacl-cli.jar
COPY --from=java-build /build/topbraid-cli/target/topbraid-shacl-cli.jar \
     ./java_wrappers/topbraid-cli/target/topbraid-shacl-cli.jar

# Install the Python package (runtime deps only — dev groups are skipped).
RUN uv sync --no-dev --frozen \
 && uv run tio-shacl --version

# Demo entry point — runs when the container starts. The TIO ontology must be
# mounted at /opt/tio-shacl/ontology (see the run command above).
COPY docker/demo.sh /usr/local/bin/demo.sh
RUN chmod +x /usr/local/bin/demo.sh

# Make 'tio-shacl' work as a direct command for ad-hoc runs
# (docker run --rm ... tio-shacl:demo tio-shacl validate my.ttl).
ENV PATH="/opt/tio-shacl/.venv/bin:${PATH}"

CMD ["/usr/local/bin/demo.sh"]
