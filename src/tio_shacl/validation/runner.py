"""Single-file SHACL validation delegating to a swappable backend.

By default the runner uses the :mod:`tio_shacl.validation.backends.pyshacl_backend`
backend. Callers can pick a different backend explicitly::

    runner = ValidationRunner(backend="topbraid")
    runner = ValidationRunner(backend=MyCustomBackend())

or implicitly via the ``TIO_VALIDATOR`` environment variable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rdflib import Graph

from ..core.loader import GraphSet, load_graphs


# -----------------------------------------------------------------------------
# Result types (backends produce these)
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    """A single SHACL validation violation.

    Fields mirror standard SHACL result properties (see
    https://www.w3.org/TR/shacl/#results-validation-result).
    """

    focus_node: str | None = None
    result_path: str | None = None
    source_shape: str | None = None
    source_constraint_component: str | None = None
    severity: str | None = None
    value: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating a single data graph against the TIO shapes."""

    conforms: bool
    violations: list[Violation] = field(default_factory=list)
    report_text: str = ""


# -----------------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------------


class ValidationRunner:
    """Validate one RDF file (or in-memory graph) against the TIO SHACL shapes.

    Args:
        ontology_dir: Override for TIO ontology directory.
        shapes_dir: Override for SHACL shapes directory.
        lib_dir: Override for reusable SHACL library.
        extensions_dir: Override for ontology extensions.
        include_extensions: Include extension shapes/ontologies in the load
            (default ``True``).
        backend: Either a backend name (``"pyshacl"``, ``"topbraid"``, ``"jena"``),
            a ready-to-use backend instance, or ``None`` to read the
            ``TIO_VALIDATOR`` env var.
    """

    def __init__(
        self,
        ontology_dir: Path | None = None,
        shapes_dir: Path | None = None,
        lib_dir: Path | None = None,
        extensions_dir: Path | None = None,
        *,
        include_extensions: bool = True,
        backend: "str | Any | None" = None,
    ) -> None:
        self.ontology_dir = ontology_dir
        self.shapes_dir = shapes_dir
        self.lib_dir = lib_dir
        self.extensions_dir = extensions_dir
        self.include_extensions = include_extensions
        self._backend = self._resolve_backend(backend)

    @staticmethod
    def _resolve_backend(explicit: "str | Any | None"):
        """Import the registry lazily to avoid circular imports at package init."""
        # Local import to break the circular dependency with backends/base.py
        from .backends import get_backend, resolve_backend

        if explicit is None or isinstance(explicit, str):
            return resolve_backend(explicit)
        # Assume the caller passed a ready-made backend instance.
        return explicit

    # ------------------------------------------------------------------
    # Graph access (lazy)
    # ------------------------------------------------------------------

    def graphs(self) -> GraphSet:
        return load_graphs(
            ontology_dir=self.ontology_dir,
            shapes_dir=self.shapes_dir,
            lib_dir=self.lib_dir,
            extensions_dir=self.extensions_dir,
            include_extensions=self.include_extensions,
        )

    @property
    def backend_name(self) -> str:
        return getattr(self._backend, "name", type(self._backend).__name__)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_file(self, path: Path) -> ValidationResult:
        if not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")

        data = Graph()
        data.parse(path, format="turtle")
        return self.validate_graph(data)

    def validate_content(self, content: str, rdf_format: str = "turtle") -> ValidationResult:
        data = Graph()
        data.parse(data=content, format=rdf_format)
        return self.validate_graph(data)

    def validate_graph(self, data: Graph) -> ValidationResult:
        """Validate a pre-built data graph.

        Merges the TIO ontology into ``data`` before dispatching to the
        backend, so that subclass and domain/range relationships are visible
        to the SHACL engine.
        """
        graphs = self.graphs()

        full_data = Graph()
        full_data += data
        full_data += graphs.ontology

        return self._backend.validate(full_data, graphs.shapes)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        g = self.graphs()
        return {
            "shapes_triples": len(g.shapes),
            "ontology_triples": len(g.ontology),
            "backend": self.backend_name,
        }
