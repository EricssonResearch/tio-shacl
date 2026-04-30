"""TopBraid SHACL 1.4.3 backend — driven through ``topbraid-shacl-cli.jar``."""

from __future__ import annotations

from rdflib import Graph

from ..runner import ValidationResult
from ._java import jar_path, run_java_validator


class TopbraidBackend:
    """Wraps the TopBraid SHACL command-line jar.

    Build the jar once with ``make java-build``. The backend then invokes it as
    a subprocess for each :meth:`validate` call. Compared to pyshacl, startup
    cost is higher (~1 s JVM warmup per call) but validation itself is fast.
    """

    name = "topbraid"

    def __init__(self) -> None:
        self._jar = jar_path("topbraid-cli/target/topbraid-shacl-cli.jar")

    def validate(self, data: Graph, shapes: Graph) -> ValidationResult:
        return run_java_validator(self._jar, data, shapes)
