#!/usr/bin/env bash
# setup_tio.sh — Apply the TIO 3.6.0 bugfix patch to a user-provided TIO ontology directory.
#
# Usage:
#   bash scripts/setup_tio.sh [ontology_dir]
#
# ontology_dir defaults to ./ontology
#
# The directory must contain the 15 TIO 3.6.0 .ttl files downloaded from:
#   https://www.tmforum.org/intent-ontology/
#
# We DO NOT redistribute TIO ontology files. You must download them yourself.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PATCH_FILE="$REPO_ROOT/patches/tio-3.6.0-fixes.patch"
ONTOLOGY_DIR="${1:-$REPO_ROOT/ontology}"

REQUIRED_FILES=(
  FunctionOntology.ttl
  IntentCommonModel.ttl
  IntentGuaranteeOntology.ttl
  IntentManagementOntology.ttl
  IntentProbing.ttl
  IntentSpecification.ttl
  IntentValidityOntology.ttl
  LogicalOperators.ttl
  MathFunctions.ttl
  MetricsAndObservations.ttl
  PreferenceOfHandlingOutcomes.ttl
  ProposalBestIntent.ttl
  QuantityOntology.ttl
  SetOperators.ttl
  Utility.ttl
)

log() { printf '\033[1;34m[setup_tio]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; }

if [[ ! -f "$PATCH_FILE" ]]; then
  err "Patch file not found: $PATCH_FILE"
  exit 1
fi

if [[ ! -d "$ONTOLOGY_DIR" ]]; then
  err "Ontology directory not found: $ONTOLOGY_DIR"
  err "Download TIO 3.6.0 from https://www.tmforum.org/intent-ontology/"
  err "and place the .ttl files there, then re-run this script."
  exit 1
fi

log "Ontology directory: $ONTOLOGY_DIR"

# Check required files
missing=()
for f in "${REQUIRED_FILES[@]}"; do
  if [[ ! -f "$ONTOLOGY_DIR/$f" ]]; then
    missing+=("$f")
  fi
done

if (( ${#missing[@]} > 0 )); then
  err "Missing required TIO files in $ONTOLOGY_DIR:"
  for f in "${missing[@]}"; do
    err "  - $f"
  done
  exit 1
fi

log "All 15 TIO files present."

# Detect if patch is already applied by checking for a known post-patch marker.
# The patch renames fun:function → fun:Function as rdfs:Class.
if grep -q '^fun:Function a rdfs:Class' "$ONTOLOGY_DIR/FunctionOntology.ttl"; then
  log "Patch appears to be already applied — skipping."
  exit 0
fi

# Verify patch applies cleanly (dry run)
log "Verifying patch applies cleanly..."
if ! patch -p1 -d "$ONTOLOGY_DIR" --dry-run --silent < "$PATCH_FILE"; then
  err "Patch does not apply cleanly. Ensure you have TIO v3.6.0 (not a different version)."
  exit 1
fi

# Apply for real
log "Applying patch..."
patch -p1 -d "$ONTOLOGY_DIR" --backup --suffix=.orig < "$PATCH_FILE"

log "Done. TIO 3.6.0 at $ONTOLOGY_DIR is now patched."
log "You can now run: make test"
