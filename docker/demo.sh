#!/usr/bin/env bash
# tio-shacl demo — exercises all three SHACL backends on a shipped good case,
# a shipped bad case, and the multi-directory -O flag. Assumes the TIO 3.6.0
# ontology has been mounted at /opt/tio-shacl/ontology.

set -euo pipefail

ONTOLOGY_DIR=/opt/tio-shacl/ontology
GOOD_CASE=test-cases/IntentCommonModel/good/class-expectations.ttl
BAD_CASE=test-cases/IntentCommonModel/bad/expectation-target-violation.ttl

cd /opt/tio-shacl

# -----------------------------------------------------------------------------
# Pre-flight
# -----------------------------------------------------------------------------

if [[ ! -d "$ONTOLOGY_DIR" ]] || [[ -z "$(ls "$ONTOLOGY_DIR"/*.ttl 2>/dev/null)" ]]; then
  cat >&2 <<EOF
ERROR: TIO ontology not mounted.

Mount your patched ./ontology directory into the container, e.g.:

  docker run --rm \\
    -v "\$PWD/ontology":/opt/tio-shacl/ontology:ro \\
    tio-shacl:demo

The ontology must contain the 15 TIO 3.6.0 .ttl files. See README.md for how
to obtain them and apply the bugfix patch on the host side before mounting.
EOF
  exit 2
fi

hr() { printf '=%.0s' {1..72}; echo; }
step() { echo; hr; echo "▸ $*"; hr; }

# -----------------------------------------------------------------------------
# 1. Environment summary
# -----------------------------------------------------------------------------

step "Environment"
echo "tio-shacl: $(tio-shacl --version)"
echo "Python:    $(python --version)"
echo "Java:      $(java -version 2>&1 | head -1)"
echo "Ontology:  $ONTOLOGY_DIR  ($(ls "$ONTOLOGY_DIR"/*.ttl | wc -l) files)"

# -----------------------------------------------------------------------------
# 2. pyshacl backend — default
# -----------------------------------------------------------------------------

step "Backend: pyshacl (default) — good case"
tio-shacl validate "$GOOD_CASE"

step "Backend: pyshacl (default) — bad case (expect non-zero exit)"
set +e
tio-shacl validate "$BAD_CASE"
echo "  [exit code: $? — expected 1]"
set -e

# -----------------------------------------------------------------------------
# 3. TopBraid backend
# -----------------------------------------------------------------------------

step "Backend: TopBraid SHACL 1.4.3 — good case"
TIO_VALIDATOR=topbraid tio-shacl validate "$GOOD_CASE"

step "Backend: TopBraid SHACL 1.4.3 — bad case"
set +e
TIO_VALIDATOR=topbraid tio-shacl validate "$BAD_CASE"
echo "  [exit code: $? — expected 1]"
set -e

# -----------------------------------------------------------------------------
# 4. Jena backend (ships SHACL-AF polyfill)
# -----------------------------------------------------------------------------

step "Backend: Apache Jena 5.2.0 — good case"
TIO_VALIDATOR=jena tio-shacl validate "$GOOD_CASE"

step "Backend: Apache Jena 5.2.0 — bad case"
set +e
TIO_VALIDATOR=jena tio-shacl validate "$BAD_CASE"
echo "  [exit code: $? — expected 1]"
set -e

# -----------------------------------------------------------------------------
# 5. Multi-directory ontology (the new -O / TIO_ONTOLOGY_DIR feature)
# -----------------------------------------------------------------------------

step "Multi-directory: -O flag with an extra catalogue"
mkdir -p /tmp/catalogue
cat > /tmp/catalogue/my_catalogue.ttl <<'EOF'
@prefix ex:   <http://example.org/catalogue/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:ExtraThing  a rdfs:Class ;
    rdfs:label "Demo class from a custom catalogue"@en .
EOF

tio-shacl validate \
    -O "$ONTOLOGY_DIR" \
    -O /tmp/catalogue \
    "$GOOD_CASE"

step "Multi-directory: TIO_ONTOLOGY_DIR with os.pathsep"
TIO_ONTOLOGY_DIR="$ONTOLOGY_DIR:/tmp/catalogue" tio-shacl validate "$GOOD_CASE"

echo
hr
echo "✓ demo complete — all three backends ran end-to-end."
hr
