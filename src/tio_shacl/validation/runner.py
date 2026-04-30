"""Single-file SHACL validation using pyshacl."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pyshacl
from rdflib import Graph, Namespace

from ..core.loader import GraphSet, load_graphs

# SHACL vocabulary
SH = Namespace("http://www.w3.org/ns/shacl#")


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


def _extract_violations(report_graph: Graph | None) -> list[Violation]:
    """Pull :class:`Violation` records out of a pyshacl report graph."""
    if report_graph is None:
        return []

    violations: list[Violation] = []
    for report in report_graph.subjects(SH.conforms, None):
        for v in report_graph.objects(report, SH.result):
            focus = report_graph.value(v, SH.focusNode)
            path = report_graph.value(v, SH.resultPath)
            shape = report_graph.value(v, SH.sourceShape)
            comp = report_graph.value(v, SH.sourceConstraintComponent)
            sev = report_graph.value(v, SH.resultSeverity)
            val = report_graph.value(v, SH.value)
            msg = report_graph.value(v, SH.resultMessage)
            violations.append(
                Violation(
                    focus_node=str(focus) if focus else None,
                    result_path=str(path) if path else None,
                    source_shape=str(shape) if shape else None,
                    source_constraint_component=str(comp) if comp else None,
                    severity=str(sev) if sev else None,
                    value=str(val) if val else None,
                    message=str(msg) if msg else None,
                )
            )
    return violations


class ValidationRunner:
    """Validate one RDF file (or in-memory graph) against the TIO SHACL shapes.

    Example:
        >>> runner = ValidationRunner()
        >>> result = runner.validate_file(Path("my_intent.ttl"))
        >>> result.conforms
        True
    """

    def __init__(
        self,
        ontology_dir: Path | None = None,
        shapes_dir: Path | None = None,
        lib_dir: Path | None = None,
        extensions_dir: Path | None = None,
        *,
        include_extensions: bool = True,
    ) -> None:
        self.ontology_dir = ontology_dir
        self.shapes_dir = shapes_dir
        self.lib_dir = lib_dir
        self.extensions_dir = extensions_dir
        self.include_extensions = include_extensions

    # ------------------------------------------------------------------
    # Graph access (lazy: we only load TIO on first validation)
    # ------------------------------------------------------------------

    def graphs(self) -> GraphSet:
        """Return the cached (shapes, ontology) graph pair."""
        return load_graphs(
            ontology_dir=self.ontology_dir,
            shapes_dir=self.shapes_dir,
            lib_dir=self.lib_dir,
            extensions_dir=self.extensions_dir,
            include_extensions=self.include_extensions,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_file(self, path: Path) -> ValidationResult:
        """Validate a single ``.ttl`` file. Raises ``FileNotFoundError`` if absent."""
        if not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")

        data = Graph()
        data.parse(path, format="turtle")
        return self.validate_graph(data)

    def validate_content(self, content: str, rdf_format: str = "turtle") -> ValidationResult:
        """Validate raw RDF content (e.g. from an HTTP request)."""
        data = Graph()
        data.parse(data=content, format=rdf_format)
        return self.validate_graph(data)

    def validate_graph(self, data: Graph) -> ValidationResult:
        """Validate a pre-built data graph.

        Merges the TIO ontology into ``data`` before calling pyshacl, so that
        subclass and domain/range relationships are available to the validator.
        """
        graphs = self.graphs()

        # Union ontology into data (pyshacl does not do this automatically)
        full_data = Graph()
        full_data += data
        full_data += graphs.ontology

        conforms, report_graph, report_text = pyshacl.validate(
            data_graph=full_data,
            shacl_graph=graphs.shapes,
            advanced=True,
            inference=None,
            meta_shacl=False,
            debug=False,
        )

        violations = _extract_violations(report_graph)
        return ValidationResult(
            conforms=bool(conforms),
            violations=violations,
            report_text=report_text or "",
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return basic stats about the loaded graphs (for debugging)."""
        g = self.graphs()
        return {
            "shapes_triples": len(g.shapes),
            "ontology_triples": len(g.ontology),
        }
