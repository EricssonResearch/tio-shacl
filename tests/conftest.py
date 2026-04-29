"""Shared pytest fixtures for tio-shacl tests.

Conventions:
- ``tio_ontology_dir`` resolves to the user-provided TIO 3.6.0 directory (patched).
  If it is missing, tests that depend on it are skipped.
- ``test_cases_dir`` points at the shipped ``test-cases/`` directory.
- ``good_cases`` / ``bad_cases`` discover all parametrized inputs at collection time.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_TIO_FILES = {
    "FunctionOntology.ttl",
    "IntentCommonModel.ttl",
    "IntentGuaranteeOntology.ttl",
    "IntentManagementOntology.ttl",
    "IntentProbing.ttl",
    "IntentSpecification.ttl",
    "IntentValidityOntology.ttl",
    "LogicalOperators.ttl",
    "MathFunctions.ttl",
    "MetricsAndObservations.ttl",
    "PreferenceOfHandlingOutcomes.ttl",
    "ProposalBestIntent.ttl",
    "QuantityOntology.ttl",
    "SetOperators.ttl",
    "Utility.ttl",
}


@dataclass(frozen=True)
class ValidationCase:
    """A single validation test case.

    Named ``ValidationCase`` (not ``TestCase``) so pytest does not try to
    collect the dataclass itself as a test class.
    """

    module: str
    path: Path
    expected_conforms: bool

    @property
    def id(self) -> str:
        return f"{self.module}/{'good' if self.expected_conforms else 'bad'}/{self.path.name}"


# -----------------------------------------------------------------------------
# Path fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def shapes_dir() -> Path:
    return REPO_ROOT / "rdf" / "shapes"


@pytest.fixture(scope="session")
def lib_dir() -> Path:
    return REPO_ROOT / "rdf" / "lib"


@pytest.fixture(scope="session")
def extensions_dir() -> Path:
    return REPO_ROOT / "extensions"


@pytest.fixture(scope="session")
def test_cases_dir() -> Path:
    return REPO_ROOT / "test-cases"


@pytest.fixture(scope="session")
def patches_dir() -> Path:
    return REPO_ROOT / "patches"


@pytest.fixture(scope="session")
def tio_ontology_dir() -> Path:
    """Resolve the TIO 3.6.0 ontology directory.

    Order of precedence:
        1. ``TIO_ONTOLOGY_DIR`` environment variable
        2. ``<repo>/ontology``

    If neither contains all 15 required TIO files, the test is skipped.
    """
    env = os.environ.get("TIO_ONTOLOGY_DIR")
    candidate = Path(env) if env else REPO_ROOT / "ontology"

    if not candidate.is_dir():
        pytest.skip(f"TIO ontology directory not found: {candidate}")

    missing = REQUIRED_TIO_FILES - {p.name for p in candidate.glob("*.ttl")}
    if missing:
        pytest.skip(f"TIO ontology directory missing files: {sorted(missing)}")

    return candidate


# -----------------------------------------------------------------------------
# Test-case discovery
# -----------------------------------------------------------------------------


def _discover_cases() -> list[ValidationCase]:
    """Walk ``test-cases/`` and build the full list of cases."""
    root = REPO_ROOT / "test-cases"
    cases: list[ValidationCase] = []
    if not root.is_dir():
        return cases

    for module_dir in sorted(root.iterdir()):
        if not module_dir.is_dir():
            continue
        for polarity, expected in (("good", True), ("bad", False)):
            pol_dir = module_dir / polarity
            if not pol_dir.is_dir():
                continue
            for ttl in sorted(pol_dir.glob("*.ttl")):
                cases.append(
                    ValidationCase(
                        module=module_dir.name,
                        path=ttl,
                        expected_conforms=expected,
                    )
                )
    return cases


ALL_CASES: list[ValidationCase] = _discover_cases()
GOOD_CASES: list[ValidationCase] = [c for c in ALL_CASES if c.expected_conforms]
BAD_CASES: list[ValidationCase] = [c for c in ALL_CASES if not c.expected_conforms]


def pytest_report_header(config: pytest.Config) -> str:
    good = len(GOOD_CASES)
    bad = len(BAD_CASES)
    return f"tio-shacl: {len(ALL_CASES)} test cases discovered ({good} good, {bad} bad)"


@pytest.fixture(scope="session")
def all_cases() -> list[ValidationCase]:
    return ALL_CASES


@pytest.fixture(scope="session")
def good_cases() -> list[ValidationCase]:
    return GOOD_CASES


@pytest.fixture(scope="session")
def bad_cases() -> list[ValidationCase]:
    return BAD_CASES


# -----------------------------------------------------------------------------
# Temp ontology dir (for tests that need an isolated TIO copy)
# -----------------------------------------------------------------------------


@pytest.fixture
def temp_ontology_dir(tio_ontology_dir: Path, tmp_path: Path) -> Iterator[Path]:
    """Copy the TIO ontology into a scratch directory for destructive tests."""
    import shutil

    dest = tmp_path / "ontology"
    shutil.copytree(tio_ontology_dir, dest)
    yield dest
