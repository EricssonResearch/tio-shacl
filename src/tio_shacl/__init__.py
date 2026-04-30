"""TMF Intent Ontology (TIO) SHACL validation package.

Exposes path helpers for shipped RDF assets (shapes, extensions, test cases)
and for the user-provided TIO 3.6.0 ontology directory.

The TIO ontology itself is never bundled with this package; see
``docs/setup.md`` for how to obtain it.
"""

from __future__ import annotations

import os
from pathlib import Path

__version__ = "1.0.0"
__tio_spec_version__ = "3.6.0"

# Internal: directory that holds __init__.py
_PACKAGE_DIR = Path(__file__).resolve().parent

# Dev-mode root: src/tio_shacl/__init__.py -> repo root
# parents[0]=tio_shacl, parents[1]=src, parents[2]=repo root
_REPO_ROOT = _PACKAGE_DIR.parent.parent


def _first_existing(*candidates: Path) -> Path:
    """Return the first candidate path that exists, or the last one.

    The last candidate is used as a fallback for FileNotFoundError messages.
    """
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[-1]


# -----------------------------------------------------------------------------
# Shipped RDF assets
# -----------------------------------------------------------------------------


def get_rdf_dir() -> Path:
    """Directory containing ``shapes/`` and ``lib/`` SHACL assets.

    Resolution order:
        1. ``<package>/rdf`` — when installed as a wheel.
        2. ``<repo_root>/rdf`` — when running from a source checkout.
    """
    return _first_existing(
        _PACKAGE_DIR / "rdf",
        _REPO_ROOT / "rdf",
    )


def get_shapes_dir() -> Path:
    """SHACL shapes: ``<rdf>/shapes`` (one TTL per TIO module)."""
    return get_rdf_dir() / "shapes"


def get_lib_dir() -> Path:
    """Reusable SHACL library: ``<rdf>/lib``.

    Contains ``GlobalShapes.ttl``, ``TargetTypes.ttl``, ``MetaShapes.ttl`` and
    ``constraints/`` / ``functions/`` subdirectories.
    """
    return get_rdf_dir() / "lib"


def get_extensions_dir() -> Path:
    """Directory containing TIO ontology extensions (our original work)."""
    return _first_existing(
        _PACKAGE_DIR / "extensions",
        _REPO_ROOT / "extensions",
    )


def get_test_cases_dir() -> Path:
    """Directory with good/bad validation test cases."""
    return _first_existing(
        _PACKAGE_DIR / "test-cases",
        _REPO_ROOT / "test-cases",
    )


def get_sparql_dir() -> Path:
    """Directory with ad-hoc SPARQL queries."""
    return _first_existing(
        _PACKAGE_DIR / "sparql",
        _REPO_ROOT / "sparql",
    )


def get_patches_dir() -> Path:
    """Directory containing the TIO 3.6.0 bugfix patch."""
    return _first_existing(
        _PACKAGE_DIR / "patches",
        _REPO_ROOT / "patches",
    )


# -----------------------------------------------------------------------------
# User-provided TIO ontology
# -----------------------------------------------------------------------------


def get_ontologies_dir() -> Path:
    """Resolve the directory holding the (patched) TIO 3.6.0 ``.ttl`` files.

    Resolution order:
        1. ``TIO_ONTOLOGY_DIR`` environment variable
        2. ``<cwd>/ontology``

    Raises:
        FileNotFoundError: if neither candidate is a directory. The user
            must download TIO 3.6.0 from TM Forum and run
            ``scripts/setup_tio.sh`` to create this directory.
    """
    env = os.environ.get("TIO_ONTOLOGY_DIR")
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env))
    candidates.append(Path.cwd() / "ontology")

    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    raise FileNotFoundError(
        "TIO ontology directory not found. Download TIO 3.6.0 from "
        "https://www.tmforum.org/intent-ontology/ and either place it at "
        "./ontology or set the TIO_ONTOLOGY_DIR environment variable. "
        f"Checked: {', '.join(str(c) for c in candidates)}"
    )


__all__ = [
    "__version__",
    "__tio_spec_version__",
    "get_rdf_dir",
    "get_shapes_dir",
    "get_lib_dir",
    "get_extensions_dir",
    "get_test_cases_dir",
    "get_sparql_dir",
    "get_patches_dir",
    "get_ontologies_dir",
]
