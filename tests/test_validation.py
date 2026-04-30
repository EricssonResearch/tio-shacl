"""Parametrized validation tests over every shipped test case.

Each ``.ttl`` under ``test-cases/<Module>/good/`` must conform to the TIO SHACL
shapes; each ``.ttl`` under ``test-cases/<Module>/bad/`` must violate at least
one shape.

The tests are parametrized so a single failure points to an exact file, making
regressions easy to triage.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import ALL_CASES, BAD_CASES, GOOD_CASES, ValidationCase

pytestmark = pytest.mark.integration


# -----------------------------------------------------------------------------
# ValidationResult contract
# -----------------------------------------------------------------------------


class TestValidationResultContract:
    """``tio_shacl.validation.ValidationResult`` is the public return type."""

    def test_result_has_conforms_field(self) -> None:
        from tio_shacl.validation import ValidationResult

        result = ValidationResult(conforms=True, violations=[], report_text="")
        assert result.conforms is True

    def test_result_has_violations_list(self) -> None:
        from tio_shacl.validation import ValidationResult

        result = ValidationResult(conforms=False, violations=[], report_text="")
        assert isinstance(result.violations, list)

    def test_result_has_report_text(self) -> None:
        from tio_shacl.validation import ValidationResult

        result = ValidationResult(conforms=True, violations=[], report_text="hello")
        assert result.report_text == "hello"


# -----------------------------------------------------------------------------
# ValidationRunner — single-file validation
# -----------------------------------------------------------------------------


class TestValidationRunner:
    """The ``ValidationRunner`` class is the low-level single-file API."""

    def test_runner_instantiable(self, tio_ontology_dir: Path) -> None:
        from tio_shacl.validation import ValidationRunner

        runner = ValidationRunner()
        assert runner is not None

    def test_runner_validates_file(self, tio_ontology_dir: Path) -> None:
        from tio_shacl.validation import ValidationRunner

        runner = ValidationRunner()
        good_file = next((ALL_CASES[i].path for i in range(len(ALL_CASES)) if ALL_CASES[i].expected_conforms), None)
        assert good_file is not None, "no good cases to test with"
        result = runner.validate_file(good_file)
        assert result.conforms is True

    def test_runner_accepts_custom_ontology_dir(
        self, tio_ontology_dir: Path, tmp_path: Path
    ) -> None:
        from tio_shacl.validation import ValidationRunner

        runner = ValidationRunner(ontology_dir=tio_ontology_dir)
        assert runner.ontology_dir == tio_ontology_dir

    def test_runner_accepts_multiple_ontology_dirs(
        self, tio_ontology_dir: Path, tmp_path: Path
    ) -> None:
        """``ontology_dirs`` composes TIO with one or more catalogues."""
        from tio_shacl.validation import ValidationRunner

        catalogue = tmp_path / "catalogue"
        catalogue.mkdir()
        (catalogue / "catalogue.ttl").write_text(
            "@prefix ex: <http://example.org/catalogue/> .\n"
            "ex:Foo a <http://www.w3.org/2000/01/rdf-schema#Class> .\n"
        )

        runner = ValidationRunner(ontology_dirs=[tio_ontology_dir, catalogue])
        assert runner.ontology_dirs == (tio_ontology_dir, catalogue)

        good_file = next(
            (c.path for c in ALL_CASES if c.expected_conforms), None
        )
        assert good_file is not None
        result = runner.validate_file(good_file)
        assert result.conforms is True

    def test_runner_rejects_conflicting_ontology_args(
        self, tio_ontology_dir: Path
    ) -> None:
        from tio_shacl.validation import ValidationRunner

        with pytest.raises(ValueError):
            ValidationRunner(
                ontology_dir=tio_ontology_dir,
                ontology_dirs=[tio_ontology_dir],
            )


# -----------------------------------------------------------------------------
# Parametrized: every good case must conform
# -----------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.parametrize("case", GOOD_CASES, ids=lambda c: c.id)
def test_good_case_conforms(case: ValidationCase, tio_ontology_dir: Path) -> None:
    """Every ``good/`` test case must pass SHACL validation."""
    from tio_shacl.validation import ValidationRunner

    runner = ValidationRunner()
    result = runner.validate_file(case.path)
    assert result.conforms, (
        f"Expected {case.id} to CONFORM but it did not.\n"
        f"Report:\n{result.report_text}"
    )


# -----------------------------------------------------------------------------
# Parametrized: every bad case must violate
# -----------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.parametrize("case", BAD_CASES, ids=lambda c: c.id)
def test_bad_case_violates(case: ValidationCase, tio_ontology_dir: Path) -> None:
    """Every ``bad/`` test case must fail SHACL validation with at least one violation."""
    from tio_shacl.validation import ValidationRunner

    runner = ValidationRunner()
    result = runner.validate_file(case.path)
    assert not result.conforms, (
        f"Expected {case.id} to have violations but it conformed.\n"
        f"Report:\n{result.report_text}"
    )
    assert len(result.violations) >= 1, "bad case must produce at least one violation"


# -----------------------------------------------------------------------------
# Coverage sanity
# -----------------------------------------------------------------------------


class TestCaseCoverage:
    """Sanity checks on the discovered test-case inventory."""

    def test_expected_case_count(self) -> None:
        # Regression: if someone deletes test cases without noticing
        assert len(ALL_CASES) >= 133, f"expected >=133 cases, found {len(ALL_CASES)}"

    def test_every_module_has_both_polarities(self) -> None:
        modules_with_good = {c.module for c in GOOD_CASES}
        modules_with_bad = {c.module for c in BAD_CASES}
        both = modules_with_good & modules_with_bad
        # At time of writing, every module has both good and bad cases.
        assert len(both) >= 15, f"modules with both polarities: {both}"

    def test_case_paths_are_unique(self) -> None:
        paths = [c.path for c in ALL_CASES]
        assert len(paths) == len(set(paths))
