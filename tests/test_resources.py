"""Path helpers exposed by ``tio_shacl``.

These tests pin down the public API for locating shipped RDF assets and the
user-provided TIO ontology directory. Every function must work in both
development mode (``rdf/`` at repo root) and installed-package mode
(``rdf/`` inside the package).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import tio_shacl


# -----------------------------------------------------------------------------
# Package metadata
# -----------------------------------------------------------------------------


class TestPackageMetadata:
    def test_version_is_semver(self) -> None:
        version = tio_shacl.__version__
        parts = version.split(".")
        assert len(parts) == 3, f"expected semver, got {version!r}"
        assert all(p.isdigit() for p in parts)

    def test_tio_spec_version(self) -> None:
        assert tio_shacl.__tio_spec_version__ == "3.6.0"


# -----------------------------------------------------------------------------
# Path resolvers
# -----------------------------------------------------------------------------


class TestPathResolvers:
    def test_get_rdf_dir_exists(self, shapes_dir: Path) -> None:
        rdf = tio_shacl.get_rdf_dir()
        assert rdf.is_dir()
        assert (rdf / "shapes").is_dir()
        assert (rdf / "lib").is_dir()

    def test_get_shapes_dir_contains_all_modules(self, shapes_dir: Path) -> None:
        result = tio_shacl.get_shapes_dir()
        assert result.is_dir()
        expected_modules = {
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
        found = {p.name for p in result.glob("*.ttl")}
        assert expected_modules <= found, f"missing: {expected_modules - found}"

    def test_get_lib_dir(self) -> None:
        lib = tio_shacl.get_lib_dir()
        assert lib.is_dir()
        # Must contain at minimum GlobalShapes, TargetTypes, MetaShapes
        names = {p.name for p in lib.glob("*.ttl")}
        assert {"GlobalShapes.ttl", "TargetTypes.ttl", "MetaShapes.ttl"} <= names

    def test_get_extensions_dir_has_all_extensions(self) -> None:
        ext = tio_shacl.get_extensions_dir()
        assert ext.is_dir()
        names = {p.name for p in ext.glob("*.ttl")}
        expected = {
            "ConstraintModelExtension.ttl",
            "ContainerTypedExtension.ttl",
            "EvaluableActionableExtensions.ttl",
            "IntentOperandExtension.ttl",
            "RequirementCapabilityExtension.ttl",
            "ValidityCandidateExtension.ttl",
        }
        assert expected <= names, f"missing extensions: {expected - names}"

    def test_get_test_cases_dir(self) -> None:
        tc = tio_shacl.get_test_cases_dir()
        assert tc.is_dir()
        # 16 TIO module sub-dirs
        sub = [p for p in tc.iterdir() if p.is_dir()]
        assert len(sub) >= 16

    def test_get_patches_dir(self) -> None:
        patches = tio_shacl.get_patches_dir()
        assert patches.is_dir()
        assert (patches / "tio-3.6.0-fixes.patch").is_file()

    def test_get_sparql_dir(self) -> None:
        sparql = tio_shacl.get_sparql_dir()
        assert sparql.is_dir()


# -----------------------------------------------------------------------------
# TIO ontology directory resolution
# -----------------------------------------------------------------------------


class TestGetOntologiesDir:
    def test_returns_path_when_ontology_dir_exists(self, tio_ontology_dir: Path) -> None:
        result = tio_shacl.get_ontologies_dir()
        assert result.is_dir()
        assert (result / "IntentCommonModel.ttl").is_file()

    def test_env_var_takes_precedence(
        self, tio_ontology_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Copy a minimal set to a new location and point TIO_ONTOLOGY_DIR there
        import shutil

        custom = tmp_path / "my-tio"
        shutil.copytree(tio_ontology_dir, custom)

        monkeypatch.setenv("TIO_ONTOLOGY_DIR", str(custom))
        result = tio_shacl.get_ontologies_dir()
        assert result == custom

    def test_raises_when_not_found(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("TIO_ONTOLOGY_DIR", str(tmp_path / "missing"))

        # Also hide any default ./ontology by running from tmp
        monkeypatch.chdir(tmp_path)

        with pytest.raises(FileNotFoundError):
            tio_shacl.get_ontologies_dir()
