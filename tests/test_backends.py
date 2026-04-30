"""Tests for the three validator backends.

All three backends — pyshacl, TopBraid, Jena — must agree on the verdict for
every sample case (pass/fail on good/bad). Jena's SHACL-AF ``sh:SPARQLTargetType``
polyfill is tested implicitly by this agreement: without it Jena would error
out on almost every TIO case.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.conftest import GOOD_CASES, BAD_CASES


# A small curated sample of cases we expect backends to agree on.
# Keep this list small — each Java invocation is ~2 s JVM startup.
_SAMPLE_NAMES = [
    "LogicalOperators/good/function-logical.ttl",
    "LogicalOperators/bad/function-logical-violations.ttl",
    "QuantityOntology/good/function-comparison.ttl",
    "QuantityOntology/bad/quantity-value-datatype-violation.ttl",
    "IntentCommonModel/good/property-report-metadata.ttl",
    "IntentCommonModel/bad/observation-reporting-expectation-violation.ttl",
]


def _sample_cases():
    """Resolve the curated sample paths against the on-disk test-cases tree."""
    from tio_shacl import get_test_cases_dir

    root = get_test_cases_dir()
    resolved = []
    for name in _SAMPLE_NAMES:
        path = root / name
        expected_conforms = "/good/" in str(path)
        resolved.append((path, expected_conforms))
    return resolved


def _java_available() -> bool:
    return shutil.which("java") is not None


# -----------------------------------------------------------------------------
# Registry and selection
# -----------------------------------------------------------------------------


class TestBackendRegistry:
    def test_list_backends_returns_all_three(self) -> None:
        from tio_shacl.validation import list_backends

        assert set(list_backends()) == {"pyshacl", "topbraid", "jena"}

    def test_get_backend_by_name(self) -> None:
        from tio_shacl.validation import (
            JenaBackend,
            PyshaclBackend,
            TopbraidBackend,
            get_backend,
        )

        assert isinstance(get_backend("pyshacl"), PyshaclBackend)
        # The Java backends instantiate even without java on PATH; require_java
        # is only called at validate() time.
        if _java_available():
            assert isinstance(get_backend("topbraid"), TopbraidBackend)
            assert isinstance(get_backend("jena"), JenaBackend)

    def test_get_backend_unknown_raises(self) -> None:
        from tio_shacl.validation import BackendError, get_backend

        with pytest.raises(BackendError):
            get_backend("does-not-exist")

    def test_resolve_backend_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from tio_shacl.validation import PyshaclBackend, resolve_backend

        monkeypatch.setenv("TIO_VALIDATOR", "pyshacl")
        assert isinstance(resolve_backend(), PyshaclBackend)

    def test_resolve_backend_explicit_overrides_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from tio_shacl.validation import PyshaclBackend, resolve_backend

        monkeypatch.setenv("TIO_VALIDATOR", "jena")
        # Explicit argument must win over the env var.
        assert isinstance(resolve_backend("pyshacl"), PyshaclBackend)


# -----------------------------------------------------------------------------
# Behaviour: all three backends must agree on every sample case.
# -----------------------------------------------------------------------------


@pytest.mark.skipif(not _java_available(), reason="java runtime not on PATH")
@pytest.mark.parametrize(("path", "expected"), _sample_cases(), ids=_SAMPLE_NAMES)
class TestBackendAgreement:
    """All three backends must produce the same verdict on each sample case."""

    def test_pyshacl(self, path: Path, expected: bool, tio_ontology_dir: Path) -> None:
        from tio_shacl.validation import ValidationRunner

        runner = ValidationRunner(backend="pyshacl")
        result = runner.validate_file(path)
        assert result.conforms == expected, f"pyshacl disagreed on {path}"

    def test_topbraid(self, path: Path, expected: bool, tio_ontology_dir: Path) -> None:
        from tio_shacl.validation import ValidationRunner

        try:
            runner = ValidationRunner(backend="topbraid")
        except Exception as exc:
            pytest.skip(f"TopBraid backend unavailable: {exc}")
        result = runner.validate_file(path)
        assert result.conforms == expected, f"topbraid disagreed on {path}"

    def test_jena(self, path: Path, expected: bool, tio_ontology_dir: Path) -> None:
        """Jena must also agree — this exercises the ``SparqlTargetTypePolyfill``."""
        from tio_shacl.validation import ValidationRunner

        try:
            runner = ValidationRunner(backend="jena")
        except Exception as exc:
            pytest.skip(f"Jena backend unavailable: {exc}")
        result = runner.validate_file(path)
        assert result.conforms == expected, f"jena disagreed on {path}"


# -----------------------------------------------------------------------------
# Runner <-> backend wiring.
# -----------------------------------------------------------------------------


class TestRunnerBackendWiring:
    def test_runner_default_backend_is_pyshacl(self) -> None:
        from tio_shacl.validation import ValidationRunner

        runner = ValidationRunner()
        assert runner.backend_name == "pyshacl"

    def test_runner_accepts_string_backend(self) -> None:
        from tio_shacl.validation import ValidationRunner

        runner = ValidationRunner(backend="pyshacl")
        assert runner.backend_name == "pyshacl"

    def test_runner_accepts_instance_backend(self) -> None:
        from tio_shacl.validation import PyshaclBackend, ValidationRunner

        backend = PyshaclBackend()
        runner = ValidationRunner(backend=backend)
        assert runner._backend is backend

    def test_stats_exposes_backend_name(self) -> None:
        from tio_shacl.validation import ValidationRunner

        runner = ValidationRunner(backend="pyshacl")
        stats = runner.stats()
        assert stats["backend"] == "pyshacl"

    def test_runner_rejects_unknown_backend_name(self) -> None:
        from tio_shacl.validation import BackendError, ValidationRunner

        with pytest.raises(BackendError):
            ValidationRunner(backend="does-not-exist")
