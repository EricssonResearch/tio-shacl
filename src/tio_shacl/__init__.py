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
    """Resolve a single directory holding the (patched) TIO 3.6.0 ``.ttl`` files.

    Resolution order:
        1. First entry of ``TIO_ONTOLOGY_DIR`` (``os.pathsep``-separated)
        2. ``<cwd>/ontology``

    Raises:
        FileNotFoundError: if neither candidate is a directory. The user
            must download TIO 3.6.0 from TM Forum and run
            ``scripts/setup_tio.sh`` to create this directory.

    See also:
        :func:`get_ontologies_dirs` for the multi-directory form, which is what
        most callers in this package actually use.
    """
    dirs = get_ontologies_dirs()
    return dirs[0]


def get_ontologies_dirs() -> tuple[Path, ...]:
    """Resolve the list of directories holding TIO and optional catalogue TTLs.

    Resolution order:
        1. ``TIO_ONTOLOGY_DIR`` environment variable — may contain multiple
           directories separated by ``os.pathsep`` (``:`` on Unix, ``;`` on
           Windows). Every listed directory must exist.
        2. ``<cwd>/ontology``

    This supports the common case where TIO lives in one directory and a
    custom service catalogue lives in another, without copying or symlinking.

    Raises:
        FileNotFoundError: if no candidate resolves to an existing directory.
    """
    env = os.environ.get("TIO_ONTOLOGY_DIR")
    candidates: list[Path] = []
    if env:
        for part in env.split(os.pathsep):
            part = part.strip()
            if part:
                candidates.append(Path(part))
    else:
        candidates.append(Path.cwd() / "ontology")

    # Every explicit candidate from the env var must exist; fall back to
    # ``./ontology`` only when the env var is unset.
    existing = [c for c in candidates if c.is_dir()]
    if existing and len(existing) == len(candidates):
        return tuple(existing)

    # Partial existence via env var is treated as a configuration error so
    # users see the typo rather than silently dropping a directory.
    if env and existing != candidates:
        missing = [c for c in candidates if not c.is_dir()]
        raise FileNotFoundError(
            "TIO_ONTOLOGY_DIR references directories that do not exist: "
            f"{', '.join(str(m) for m in missing)}"
        )

    raise FileNotFoundError(
        "TIO ontology directory not found. Download TIO 3.6.0 from "
        "https://projects.tmforum.org/wiki/pages/viewpageattachments.action?pageId=328567625 "
        "(free TM Forum account required) and either place it at "
        "./ontology or set the TIO_ONTOLOGY_DIR environment variable "
        "(multiple directories may be separated by os.pathsep). "
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
    "get_patches_dir",
    "get_ontologies_dir",
    "get_ontologies_dirs",
]
