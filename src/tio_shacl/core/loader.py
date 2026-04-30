"""Load TIO SHACL shapes and ontology graphs from disk.

The public API is :func:`load_graphs`, which returns a :class:`GraphSet`
containing a merged *shapes graph* and a merged *ontology graph*. The ontology
graph must be unioned with user data before calling the SHACL validator; the
shapes graph is passed as the ``shacl_graph`` argument.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rdflib import Graph

import tio_shacl


@dataclass(frozen=True)
class GraphSet:
    """Bundle of the two graphs needed for SHACL validation.

    Attributes:
        shapes: Merged SHACL shapes graph (shapes, lib/GlobalShapes,
            lib/TargetTypes, lib/constraints/*, lib/functions/*). Excludes
            ``lib/MetaShapes.ttl`` which is intended only for validating shapes
            themselves.
        ontology: Merged TIO ontology + in-repo extensions. This graph must be
            unioned with user data before validation so that pyshacl can
            resolve ``rdfs:domain`` / ``rdfs:range`` and type hierarchies.
    """

    shapes: Graph
    ontology: Graph


def _parse_ttl_files(paths: list[Path]) -> Graph:
    """Parse a list of ``.ttl`` files into a single union graph."""
    g = Graph()
    for p in paths:
        g.parse(p, format="turtle")
    return g


def _collect_shape_files(
    shapes_dir: Path,
    lib_dir: Path,
    include_extensions: bool = True,
) -> list[Path]:
    """Enumerate every TTL that belongs in the SHACL shapes graph.

    Order (irrelevant to semantics but stable for debugging):

    1. per-module shapes: ``rdf/shapes/*.ttl``
    2. shape extensions:  ``rdf/shapes/extensions/*.ttl`` (when enabled)
    3. global shapes:     ``rdf/lib/GlobalShapes.ttl``
    4. reusable targets:  ``rdf/lib/TargetTypes.ttl``
    5. constraint lib:    ``rdf/lib/constraints/*.ttl``
    6. function lib:      ``rdf/lib/functions/*.ttl``

    ``rdf/lib/MetaShapes.ttl`` is *deliberately excluded* — it validates shapes,
    not instance data.
    """
    files: list[Path] = sorted(shapes_dir.glob("*.ttl"))

    if include_extensions:
        files.extend(sorted((shapes_dir / "extensions").glob("*.ttl")))

    for reusable in ("GlobalShapes.ttl", "TargetTypes.ttl"):
        path = lib_dir / reusable
        if path.is_file():
            files.append(path)

    for subdir in ("constraints", "functions"):
        sub = lib_dir / subdir
        if sub.is_dir():
            files.extend(sorted(sub.glob("*.ttl")))

    return files


def _collect_ontology_files(
    ontology_dir: Path,
    extensions_dir: Path | None,
) -> list[Path]:
    """Enumerate every TTL that belongs in the ontology graph.

    Includes the 15 TIO files plus any local ontology extensions (which add
    vocabulary, not validation rules).
    """
    files: list[Path] = sorted(ontology_dir.glob("*.ttl"))
    if extensions_dir is not None and extensions_dir.is_dir():
        files.extend(sorted(extensions_dir.glob("*.ttl")))
    return files


@lru_cache(maxsize=4)
def _cached_graphset(
    shapes_dir: Path,
    lib_dir: Path,
    ontology_dir: Path,
    extensions_dir: Path | None,
    include_extensions: bool,
) -> GraphSet:
    """Cache the parsed graphs so repeated validations don't re-parse."""
    shape_files = _collect_shape_files(shapes_dir, lib_dir, include_extensions)
    ontology_files = _collect_ontology_files(ontology_dir, extensions_dir)

    shapes = _parse_ttl_files(shape_files)
    ontology = _parse_ttl_files(ontology_files)
    return GraphSet(shapes=shapes, ontology=ontology)


def load_graphs(
    ontology_dir: Path | None = None,
    shapes_dir: Path | None = None,
    lib_dir: Path | None = None,
    extensions_dir: Path | None = None,
    *,
    include_extensions: bool = True,
) -> GraphSet:
    """Load and merge all graphs required for SHACL validation.

    Any ``None`` argument is resolved via the corresponding ``tio_shacl.get_*``
    helper. Results are memoised per argument tuple so the caller can invoke
    :func:`load_graphs` many times cheaply.

    Args:
        ontology_dir: Directory containing the (patched) TIO 3.6.0 ``.ttl``
            files. Defaults to :func:`tio_shacl.get_ontologies_dir`.
        shapes_dir: Directory containing per-module SHACL shapes. Defaults to
            :func:`tio_shacl.get_shapes_dir`.
        lib_dir: Reusable SHACL library. Defaults to
            :func:`tio_shacl.get_lib_dir`.
        extensions_dir: TIO ontology extensions. Defaults to
            :func:`tio_shacl.get_extensions_dir`.
        include_extensions: If ``False``, skip ``rdf/shapes/extensions/`` and
            the ``extensions/`` ontology add-ons.
    """
    resolved_shapes = shapes_dir or tio_shacl.get_shapes_dir()
    resolved_lib = lib_dir or tio_shacl.get_lib_dir()
    resolved_ontology = ontology_dir or tio_shacl.get_ontologies_dir()
    resolved_extensions = (
        extensions_dir
        if extensions_dir is not None
        else (tio_shacl.get_extensions_dir() if include_extensions else None)
    )

    return _cached_graphset(
        shapes_dir=resolved_shapes,
        lib_dir=resolved_lib,
        ontology_dir=resolved_ontology,
        extensions_dir=resolved_extensions,
        include_extensions=include_extensions,
    )
