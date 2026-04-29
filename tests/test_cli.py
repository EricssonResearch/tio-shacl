"""Tests for the click-based CLI.

The CLI provides three primary subcommands:

- ``tio-shacl validate <file>`` — validate one RDF file
- ``tio-shacl test`` — run the full test suite
- ``tio-shacl report`` — generate a report from cached results
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.conftest import GOOD_CASES, BAD_CASES


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestCLIInvocation:
    def test_main_help(self, runner: CliRunner) -> None:
        from tio_shacl.cli import main

        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "validate" in result.output.lower()
        assert "test" in result.output.lower()
        assert "report" in result.output.lower()

    def test_version_flag(self, runner: CliRunner) -> None:
        from tio_shacl.cli import main

        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        # Output should mention the version
        assert any(c.isdigit() for c in result.output)


class TestValidateCommand:
    def test_validate_good_file_exits_zero(
        self, runner: CliRunner, tio_ontology_dir: Path
    ) -> None:
        from tio_shacl.cli import main

        assert GOOD_CASES, "no good cases available for test"
        result = runner.invoke(main, ["validate", str(GOOD_CASES[0].path)])
        assert result.exit_code == 0, result.output

    def test_validate_bad_file_exits_nonzero(
        self, runner: CliRunner, tio_ontology_dir: Path
    ) -> None:
        from tio_shacl.cli import main

        assert BAD_CASES, "no bad cases available for test"
        result = runner.invoke(main, ["validate", str(BAD_CASES[0].path)])
        assert result.exit_code != 0

    def test_validate_missing_file_errors(self, runner: CliRunner) -> None:
        from tio_shacl.cli import main

        result = runner.invoke(main, ["validate", "/nonexistent/path.ttl"])
        assert result.exit_code != 0


class TestTestCommand:
    def test_test_runs_full_suite(
        self, runner: CliRunner, tio_ontology_dir: Path
    ) -> None:
        from tio_shacl.cli import main

        result = runner.invoke(main, ["test"])
        # Exit code 0 means all suites passed; non-zero means some failed.
        # Either is acceptable here — we only care that the command runs.
        assert result.exit_code in (0, 1)

    def test_test_single_suite(
        self, runner: CliRunner, tio_ontology_dir: Path
    ) -> None:
        from tio_shacl.cli import main

        result = runner.invoke(main, ["test", "-s", "IntentCommonModel"])
        assert result.exit_code in (0, 1)
        assert "IntentCommonModel" in result.output


class TestReportCommand:
    def test_report_markdown(
        self, runner: CliRunner, tmp_path: Path, tio_ontology_dir: Path
    ) -> None:
        from tio_shacl.cli import main

        out_file = tmp_path / "report.md"
        # Run test first to populate cache, then report
        runner.invoke(main, ["test", "-s", "LogicalOperators"])
        result = runner.invoke(main, ["report", "-o", str(out_file)])
        assert result.exit_code == 0
        assert out_file.is_file()
        assert out_file.stat().st_size > 0

    def test_report_json(
        self, runner: CliRunner, tmp_path: Path, tio_ontology_dir: Path
    ) -> None:
        from tio_shacl.cli import main

        out_file = tmp_path / "report.json"
        runner.invoke(main, ["test", "-s", "LogicalOperators"])
        result = runner.invoke(
            main, ["report", "--format", "json", "-o", str(out_file)]
        )
        assert result.exit_code == 0
        assert out_file.is_file()

        import json

        data = json.loads(out_file.read_text())
        assert isinstance(data, (dict, list))
