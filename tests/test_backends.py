"""Tests for the three validator backends.

The pyshacl and TopBraid backends must agree on the verdict for every sample
case (pass/fail on good/bad). The Jena backend is tested separately — it is
expected to error out on shapes that use parameterised SPARQL target types,
which covers most of the TIO suite. We keep one smoke test to make sure the
backend can be instantiated and returns a :class:`ValidationResult` (even if
that result indicates an error).
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
# Behaviour: pyshacl and TopBraid should agree on every sample case.
# -----------------------------------------------------------------------------


@pytest.mark.skipif(not _java_available(), reason="java runtime not on PATH")
@pytest.mark.parametrize(("path", "expected"), _sample_cases(), ids=_SAMPLE_NAMES)
class TestPyshaclVsTopbraidAgreement:
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


# -----------------------------------------------------------------------------
# Jena backend smoke test (known-limited — see module docstring).
# -----------------------------------------------------------------------------


class TestJenaBackendSmoke:
    @pytest.mark.skipif(not _java_available(), reason="java runtime not on PATH")
    def test_jena_backend_returns_result(self, tio_ontology_dir: Path) -> None:
        """Jena returns a :class:`ValidationResult`, even when it errors.

        TIO's shapes use parameterised ``sh:SPARQLTargetType`` instances that
        Jena cannot fully resolve (see ``docs/architecture.md`` and the README).
        We accept any outcome — conforms true or false — so long as the backend
        produces a structured result and does not raise.
        """
        from tio_shacl.validation import ValidationResult, ValidationRunner

        try:
            runner = ValidationRunner(backend="jena")
        except Exception as exc:
            pytest.skip(f"Jena backend unavailable: {exc}")

        sample = _sample_cases()[0][0]  # LogicalOperators/good/function-logical.ttl
        result = runner.validate_file(sample)
        assert isinstance(result, ValidationResult)
        # We do not assert conforms — Jena's behaviour on TIO is an open item.


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
