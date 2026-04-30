"""Apache Jena 5.2.0 backend — driven through ``jena-shacl-cli.jar``.

The bundled CLI jar includes a generic SHACL-AF ``sh:SPARQLTargetType``
polyfill (``SparqlTargetTypePolyfill.java``) that rewrites every target-type
instance into an inline ``sh:SPARQLTarget`` before Jena parses the shapes.
This makes the backend a full peer of the TopBraid and pyshacl backends on
TIO's shapes.
"""

from __future__ import annotations

from rdflib import Graph

from ..runner import ValidationResult
from ._java import jar_path, run_java_validator


class JenaBackend:
    """Wraps the Apache Jena SHACL command-line jar."""

    name = "jena"

    def __init__(self) -> None:
        self._jar = jar_path("jena-cli/target/jena-shacl-cli.jar")

    def validate(self, data: Graph, shapes: Graph) -> ValidationResult:
        return run_java_validator(self._jar, data, shapes)
