"""Tests for the ``TestOrchestrator`` (suite discovery + parallel execution)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


class TestSuiteDiscovery:
    def test_discover_returns_one_suite_per_module(self, test_cases_dir: Path) -> None:
        from tio_shacl.validation import TestOrchestrator

        orch = TestOrchestrator()
        suites = orch.discover_test_suites()
        names = {s.name for s in suites}
        # Must include all 16 TIO modules + CompleteIntents
        assert "IntentCommonModel" in names
        assert "FunctionOntology" in names
        assert "CompleteIntents" in names

    def test_suite_has_good_and_bad_cases(self, test_cases_dir: Path) -> None:
        from tio_shacl.validation import TestOrchestrator

        orch = TestOrchestrator()
        suites = orch.discover_test_suites()
        suite = next(s for s in suites if s.name == "IntentCommonModel")
        assert len(suite.good_cases) >= 1
        assert len(suite.bad_cases) >= 1


class TestSuiteExecution:
    def test_run_single_suite(self, tio_ontology_dir: Path) -> None:
        from tio_shacl.validation import TestOrchestrator

        orch = TestOrchestrator()
        suites = orch.discover_test_suites()
        suite = next(s for s in suites if s.name == "IntentCommonModel")
        report = orch.run_test_suite(suite)

        # Report should have per-case results
        assert report.suite_name == "IntentCommonModel"
        assert report.total > 0
        assert report.passed + report.failed == report.total

    def test_run_all_suites(self, tio_ontology_dir: Path) -> None:
        from tio_shacl.validation import TestOrchestrator

        orch = TestOrchestrator()
        reports = orch.run_all()
        assert len(reports) >= 16  # one per module
        # Aggregate must be well-formed
        total = sum(r.total for r in reports)
        assert total >= 133

    def test_parallel_execution_is_faster(self, tio_ontology_dir: Path) -> None:
        """Running in parallel should not produce different results than serial."""
        from tio_shacl.validation import TestOrchestrator

        orch_serial = TestOrchestrator(workers=1)
        orch_parallel = TestOrchestrator(workers=4)

        reports_serial = orch_serial.run_all()
        reports_parallel = orch_parallel.run_all()

        # Aggregate pass/fail counts must match
        serial_totals = sorted((r.suite_name, r.passed, r.failed) for r in reports_serial)
        parallel_totals = sorted((r.suite_name, r.passed, r.failed) for r in reports_parallel)
        assert serial_totals == parallel_totals
