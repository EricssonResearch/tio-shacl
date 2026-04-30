"""Run the full 133-case suite with a single backend, write per-case results.

Usage:
    uv run python scripts/run_full_suite.py <backend>

Writes a JSON report to ./run_<backend>.json with per-case outcomes.
Designed for cross-backend comparison: run it three times (pyshacl,
topbraid, jena), then diff the resulting files.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import tio_shacl
from tio_shacl.validation import TestOrchestrator, ValidationRunner
from tio_shacl.validation.runner import ValidationResult


def run(backend: str, output: Path) -> int:
    runner = ValidationRunner(backend=backend)
    orch = TestOrchestrator()

    suites = orch.discover_test_suites()
    total_cases = sum(s.total for s in suites)
    print(f"Backend: {backend}")
    print(f"Suites:  {len(suites)}  ({total_cases} cases)")
    print(f"Output:  {output}")
    print()

    report: dict = {
        "backend": backend,
        "tio_shacl_version": tio_shacl.__version__,
        "tio_spec_version": tio_shacl.__tio_spec_version__,
        "suites": [],
        "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
        "elapsed_s": 0.0,
    }

    t0 = time.monotonic()

    for suite in suites:
        suite_t0 = time.monotonic()
        suite_report: dict = {
            "name": suite.name,
            "good": [],
            "bad": [],
            "passed": 0,
            "failed": 0,
            "errors": 0,
        }

        for polarity, expected, cases in (
            ("good", True, suite.good_cases),
            ("bad", False, suite.bad_cases),
        ):
            for path in cases:
                case_t0 = time.monotonic()
                err: str | None = None
                try:
                    result: ValidationResult = runner.validate_file(path)
                    conforms = result.conforms
                    violations = len(result.violations)
                except Exception as exc:  # noqa: BLE001
                    err = f"{type(exc).__name__}: {exc}"
                    conforms = None  # type: ignore[assignment]
                    violations = -1
                case_elapsed = time.monotonic() - case_t0

                passed = (err is None) and (conforms == expected)

                entry = {
                    "name": path.name,
                    "expected_conforms": expected,
                    "actual_conforms": conforms,
                    "violations": violations,
                    "error": err,
                    "passed": passed,
                    "time_s": round(case_elapsed, 3),
                }
                suite_report[polarity].append(entry)

                if err is not None:
                    suite_report["errors"] += 1
                elif passed:
                    suite_report["passed"] += 1
                else:
                    suite_report["failed"] += 1

        suite_report["time_s"] = round(time.monotonic() - suite_t0, 2)
        report["suites"].append(suite_report)
        print(
            f"  {suite.name:<36} "
            f"{suite_report['passed']:>3}/{suite.total:<3} passed  "
            f"({suite_report['failed']} failed, {suite_report['errors']} errors)  "
            f"{suite_report['time_s']}s"
        )

        report["summary"]["total"] += suite.total
        report["summary"]["passed"] += suite_report["passed"]
        report["summary"]["failed"] += suite_report["failed"]
        report["summary"]["errors"] += suite_report["errors"]

    report["elapsed_s"] = round(time.monotonic() - t0, 2)

    output.write_text(json.dumps(report, indent=2))
    s = report["summary"]
    print()
    print(
        f"Summary: {s['passed']}/{s['total']} passed  "
        f"({s['failed']} failed, {s['errors']} errors)  "
        f"in {report['elapsed_s']}s"
    )
    return 0 if s["failed"] == 0 and s["errors"] == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("backend", choices=["pyshacl", "topbraid", "jena"])
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: run_<backend>.json).",
    )
    args = parser.parse_args()
    output = args.output or Path(f"run_{args.backend}.json")
    sys.exit(run(args.backend, output))


if __name__ == "__main__":
    main()
