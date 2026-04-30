"""Test-suite discovery and batch execution.

The orchestrator walks ``test-cases/<Module>/{good,bad}/*.ttl``, validates each
case against the TIO SHACL shapes, and aggregates the results per module.

Workers share nothing by default (each subprocess re-parses the graphs), but
serial mode keeps the :class:`ValidationRunner` alive so the ``lru_cache`` on
:func:`tio_shacl.core.loader.load_graphs` parses the TIO ontology exactly once.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import tio_shacl
from .runner import ValidationResult, ValidationRunner


# -----------------------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class TestSuite:
    """A discovered test suite — one per TIO module directory."""

    name: str
    good_cases: tuple[Path, ...]
    bad_cases: tuple[Path, ...]

    @property
    def total(self) -> int:
        return len(self.good_cases) + len(self.bad_cases)


@dataclass(frozen=True)
class CaseOutcome:
    """Per-case verdict returned by the orchestrator."""

    path: Path
    expected_conforms: bool
    actual_conforms: bool
    violations: int

    @property
    def passed(self) -> bool:
        return self.expected_conforms == self.actual_conforms


@dataclass
class SuiteReport:
    """Aggregated result of running a single test suite."""

    suite_name: str
    outcomes: list[CaseOutcome] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def passed(self) -> int:
        return sum(1 for o in self.outcomes if o.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed


# -----------------------------------------------------------------------------
# Worker function (module-level so it can be pickled)
# -----------------------------------------------------------------------------


def _validate_case(case: tuple[Path, bool]) -> CaseOutcome:
    """Run a single case in-process. Returns a :class:`CaseOutcome`.

    A fresh :class:`ValidationRunner` is created each call; when run inside a
    subprocess that is the intended cold start. When run serially, the caller
    should bypass this helper and re-use one runner directly (see
    :meth:`TestOrchestrator._run_serial`).
    """
    path, expected_conforms = case
    runner = ValidationRunner()
    result: ValidationResult = runner.validate_file(path)
    return CaseOutcome(
        path=path,
        expected_conforms=expected_conforms,
        actual_conforms=result.conforms,
        violations=len(result.violations),
    )


# -----------------------------------------------------------------------------
# Orchestrator
# -----------------------------------------------------------------------------


class TestOrchestrator:
    """Discover test suites and run them serially or in parallel."""

    def __init__(
        self,
        test_cases_dir: Path | None = None,
        *,
        workers: int = 1,
    ) -> None:
        self.test_cases_dir = test_cases_dir or tio_shacl.get_test_cases_dir()
        self.workers = max(1, workers)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_test_suites(self) -> list[TestSuite]:
        """Return one :class:`TestSuite` per sub-directory of ``test-cases/``."""
        suites: list[TestSuite] = []
        if not self.test_cases_dir.is_dir():
            return suites

        for module_dir in sorted(self.test_cases_dir.iterdir()):
            if not module_dir.is_dir():
                continue
            good = tuple(sorted((module_dir / "good").glob("*.ttl")))
            bad = tuple(sorted((module_dir / "bad").glob("*.ttl")))
            if not good and not bad:
                continue
            suites.append(
                TestSuite(
                    name=module_dir.name,
                    good_cases=good,
                    bad_cases=bad,
                )
            )
        return suites

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run_test_suite(self, suite: TestSuite) -> SuiteReport:
        """Validate every case in *suite* and return an aggregated report."""
        cases: list[tuple[Path, bool]] = [(p, True) for p in suite.good_cases]
        cases += [(p, False) for p in suite.bad_cases]

        outcomes = self._run_cases(cases)
        return SuiteReport(suite_name=suite.name, outcomes=outcomes)

    def run_all(self) -> list[SuiteReport]:
        """Validate every discovered suite."""
        return [self.run_test_suite(suite) for suite in self.discover_test_suites()]

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _run_cases(self, cases: list[tuple[Path, bool]]) -> list[CaseOutcome]:
        if self.workers == 1:
            return self._run_serial(cases)
        return self._run_parallel(cases)

    def _run_serial(self, cases: list[tuple[Path, bool]]) -> list[CaseOutcome]:
        """Serial execution that re-uses one :class:`ValidationRunner` (cache hot)."""
        runner = ValidationRunner()
        outcomes: list[CaseOutcome] = []
        for path, expected in cases:
            result = runner.validate_file(path)
            outcomes.append(
                CaseOutcome(
                    path=path,
                    expected_conforms=expected,
                    actual_conforms=result.conforms,
                    violations=len(result.violations),
                )
            )
        return outcomes

    def _run_parallel(self, cases: list[tuple[Path, bool]]) -> list[CaseOutcome]:
        """Parallel execution via a process pool.

        Each worker pays the ontology-parsing cost once; beyond ~4 workers the
        marginal speed-up falls off on a 133-case run.
        """
        outcomes: list[CaseOutcome] = [None] * len(cases)  # type: ignore[list-item]
        with ProcessPoolExecutor(max_workers=self.workers) as pool:
            futures = {
                pool.submit(_validate_case, case): idx for idx, case in enumerate(cases)
            }
            for fut in as_completed(futures):
                outcomes[futures[fut]] = fut.result()
        return outcomes
