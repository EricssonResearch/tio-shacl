"""Shared helpers for jar-based backends (TopBraid, Jena)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from rdflib import Graph

import tio_shacl
from .base import BackendError
from ..runner import ValidationResult, Violation

# Default timeout for a single validation (subprocess can be slow)
_DEFAULT_TIMEOUT = 300.0


def require_java() -> str:
    """Return the path to ``java`` on the user's ``PATH``; raise otherwise."""
    java = shutil.which("java")
    if java is None:
        raise BackendError(
            "The Java runtime (java) was not found on PATH. Install JDK 17+ "
            "to use the TopBraid or Jena backends."
        )
    return java


def jar_path(relative: str) -> Path:
    """Return the absolute path to ``java_wrappers/<relative>.jar``.

    Looks under:

    1. ``<repo>/java_wrappers/<relative>`` (development layout)
    2. ``<package>/java_wrappers/<relative>`` (installed package)
    """
    candidates: list[Path] = []
    for root in _java_wrappers_roots():
        candidates.append(root / relative)

    for p in candidates:
        if p.is_file():
            return p

    raise BackendError(
        f"Java wrapper jar not found: {relative}. Run 'make java-build'. "
        f"Searched: {', '.join(str(c) for c in candidates)}"
    )


def _java_wrappers_roots() -> list[Path]:
    """Return every candidate directory that may contain ``java_wrappers/``."""
    pkg = Path(tio_shacl.__file__).resolve().parent
    out: list[Path] = []

    # Development layout: src/tio_shacl/__init__.py -> repo_root / java_wrappers/
    dev = pkg.parent.parent / "java_wrappers"
    if dev.is_dir():
        out.append(dev)

    # Installed wheel layout: <package>/java_wrappers/ (enabled via
    # hatch force-include — ship the jars with the distribution).
    installed = pkg / "java_wrappers"
    if installed.is_dir():
        out.append(installed)

    return out


def run_java_validator(
    jar: Path,
    data: Graph,
    shapes: Graph,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
) -> ValidationResult:
    """Serialize *data* and *shapes* to temp files, invoke *jar*, parse its JSON.

    The wrapper jars output JSON on stdout with the schema::

        {
            "conforms":       bool,
            "violations":     int,   // -1 on error
            "validation_ms":  float,
            "report":         "...",  // Turtle, optional
            "error":          "...",  // only on failure
        }
    """
    java = require_java()

    with tempfile.TemporaryDirectory(prefix="tio-shacl-java-") as tmp:
        tmp_path = Path(tmp)
        data_file = tmp_path / "data.ttl"
        shapes_file = tmp_path / "shapes.ttl"
        data_file.write_bytes(data.serialize(format="turtle").encode("utf-8"))
        shapes_file.write_bytes(shapes.serialize(format="turtle").encode("utf-8"))

        proc = subprocess.run(
            [java, "-jar", str(jar), str(data_file), str(shapes_file)],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "LANG": "C.UTF-8"},
        )

    # Parse the last non-empty line of stdout as JSON. The jars sometimes emit
    # logging noise before the payload on stderr; stdout is the single JSON line.
    payload = _parse_json_output(proc.stdout)
    if payload is None:
        raise BackendError(
            f"Java validator {jar.name} produced non-JSON output.\n"
            f"--- stdout ---\n{proc.stdout[:500]}\n"
            f"--- stderr ---\n{proc.stderr[:500]}"
        )

    if "error" in payload:
        # Build a ValidationResult that reflects the failure but still keeps
        # the error visible. Callers that want strict propagation can re-check.
        return ValidationResult(
            conforms=False,
            violations=[
                Violation(
                    message=f"{jar.name}: {payload['error']}",
                    severity="http://www.w3.org/ns/shacl#Violation",
                )
            ],
            report_text=payload.get("report", "") or f"ERROR: {payload['error']}",
        )

    conforms = bool(payload.get("conforms", False))
    violation_count = int(payload.get("violations", 0) or 0)
    report_text = payload.get("report", "") or ""

    # Minimal violation list: we don't re-parse the Turtle report. If richer
    # extraction is needed, callers can parse ``report_text`` themselves.
    violations = [
        Violation(message=f"{jar.name} reported violation #{i+1}")
        for i in range(violation_count)
    ]

    return ValidationResult(
        conforms=conforms,
        violations=violations,
        report_text=report_text,
    )


def _parse_json_output(stdout: str) -> dict | None:
    """Return the last valid JSON object emitted by the jar, or ``None``."""
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None
