"""Apache Jena 5.2.0 backend — driven through ``jena-shacl-cli.jar``.

.. note::

   Jena's SHACL implementation requires every ``sh:SPARQLTargetType`` instance
   to fully bind each declared parameter. TIO's shapes use parameterised target
   types where some parameters are bound implicitly; pyshacl and TopBraid
   tolerate this, Jena does not. As a result, this backend errors out on most
   TIO shapes with ``Missing required parameter``. It is shipped for
   completeness and for benchmarking shapes that do not rely on parameterised
   targets.
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
