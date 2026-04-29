"""Tests for the FastAPI REST endpoints.

Endpoints:

- ``GET  /healthz``           — health check
- ``GET  /version``           — version info
- ``POST /validate``          — validate raw RDF content
- ``POST /validate/file``     — validate an uploaded file
- ``GET  /suites``            — list available test suites
- ``POST /suites/{name}/run`` — run a specific test suite
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import GOOD_CASES, BAD_CASES

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from tio_shacl.api import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


class TestHealth:
    def test_healthz(self, client) -> None:
        response = client.get("/healthz")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("status") == "ok"

    def test_version(self, client) -> None:
        response = client.get("/version")
        assert response.status_code == 200
        payload = response.json()
        assert "version" in payload
        assert payload.get("tio_spec_version") == "3.6.0"


class TestValidateEndpoint:
    def test_validate_good_ttl_content(self, client, tio_ontology_dir: Path) -> None:
        assert GOOD_CASES
        content = GOOD_CASES[0].path.read_text()
        response = client.post(
            "/validate",
            json={"content": content, "format": "turtle"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["conforms"] is True

    def test_validate_bad_ttl_content(self, client, tio_ontology_dir: Path) -> None:
        assert BAD_CASES
        content = BAD_CASES[0].path.read_text()
        response = client.post(
            "/validate",
            json={"content": content, "format": "turtle"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["conforms"] is False
        assert isinstance(payload["violations"], list)
        assert len(payload["violations"]) >= 1

    def test_validate_file_upload(self, client, tio_ontology_dir: Path) -> None:
        assert GOOD_CASES
        with GOOD_CASES[0].path.open("rb") as fh:
            response = client.post(
                "/validate/file",
                files={"file": (GOOD_CASES[0].path.name, fh, "text/turtle")},
            )
        assert response.status_code == 200
        assert response.json()["conforms"] is True

    def test_validate_malformed_input(self, client) -> None:
        response = client.post(
            "/validate",
            json={"content": "this is not valid turtle", "format": "turtle"},
        )
        # Implementation can choose 400 or 422
        assert response.status_code in (400, 422)


class TestSuitesEndpoint:
    def test_list_suites(self, client) -> None:
        response = client.get("/suites")
        assert response.status_code == 200
        payload = response.json()
        suites = payload.get("suites", payload)  # accept either wrapped or bare list
        assert isinstance(suites, list)
        names = [s["name"] if isinstance(s, dict) else s for s in suites]
        assert "IntentCommonModel" in names

    def test_run_single_suite(self, client, tio_ontology_dir: Path) -> None:
        response = client.post("/suites/LogicalOperators/run")
        assert response.status_code == 200
        payload = response.json()
        assert payload["suite_name"] == "LogicalOperators"
        assert "passed" in payload
        assert "failed" in payload
        assert "total" in payload

    def test_run_unknown_suite_404(self, client) -> None:
        response = client.post("/suites/DoesNotExist/run")
        assert response.status_code == 404
