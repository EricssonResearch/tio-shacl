"""FastAPI REST API for tio-shacl.

Run with::

    uv run tio-shacl-api
    # or
    uvicorn tio_shacl.api:app --reload

Endpoints:
    GET  /healthz               — health check
    GET  /version               — version info
    POST /validate              — validate raw RDF content
    POST /validate/file         — validate an uploaded file
    GET  /suites                — list available test suites
    POST /suites/{name}/run     — run a single test suite
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

import tio_shacl
from .validation import TestOrchestrator, ValidationRunner, ValidationResult


# -----------------------------------------------------------------------------
# Pydantic models
# -----------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class VersionResponse(BaseModel):
    version: str
    tio_spec_version: str


class ValidateRequest(BaseModel):
    content: str = Field(..., description="RDF content as a string.")
    format: Literal["turtle", "n3", "xml", "nt", "json-ld"] = Field(
        default="turtle",
        description="RDF serialisation format.",
    )


class ViolationModel(BaseModel):
    focus_node: str | None = None
    result_path: str | None = None
    source_shape: str | None = None
    source_constraint_component: str | None = None
    severity: str | None = None
    value: str | None = None
    message: str | None = None


class ValidateResponse(BaseModel):
    conforms: bool
    violations: list[ViolationModel]
    report_text: str


class SuiteSummary(BaseModel):
    name: str
    total: int


class SuitesResponse(BaseModel):
    suites: list[SuiteSummary]


class SuiteReportResponse(BaseModel):
    suite_name: str
    total: int
    passed: int
    failed: int


# -----------------------------------------------------------------------------
# Runners (lazy globals so imports are cheap)
# -----------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _runner() -> ValidationRunner:
    return ValidationRunner()


@lru_cache(maxsize=1)
def _orchestrator() -> TestOrchestrator:
    return TestOrchestrator()


# -----------------------------------------------------------------------------
# Response helpers
# -----------------------------------------------------------------------------


def _result_to_response(result: ValidationResult) -> ValidateResponse:
    return ValidateResponse(
        conforms=result.conforms,
        violations=[
            ViolationModel(
                focus_node=v.focus_node,
                result_path=v.result_path,
                source_shape=v.source_shape,
                source_constraint_component=v.source_constraint_component,
                severity=v.severity,
                value=v.value,
                message=v.message,
            )
            for v in result.violations
        ],
        report_text=result.report_text,
    )


# -----------------------------------------------------------------------------
# App factory
# -----------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="tio-shacl API",
        version=tio_shacl.__version__,
        description=(
            "REST API for validating RDF intents against the TM Forum Intent "
            "Ontology (TIO) SHACL shapes."
        ),
    )

    # --- health / version -----------------------------------------------

    @app.get("/healthz", response_model=HealthResponse)
    def healthz() -> HealthResponse:
        return HealthResponse()

    @app.get("/version", response_model=VersionResponse)
    def version() -> VersionResponse:
        return VersionResponse(
            version=tio_shacl.__version__,
            tio_spec_version=tio_shacl.__tio_spec_version__,
        )

    # --- validate -------------------------------------------------------

    @app.post("/validate", response_model=ValidateResponse)
    def validate_content(req: ValidateRequest) -> ValidateResponse:
        try:
            result = _runner().validate_content(req.content, rdf_format=req.format)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid RDF: {exc}") from exc
        return _result_to_response(result)

    @app.post("/validate/file", response_model=ValidateResponse)
    async def validate_file(file: UploadFile = File(...)) -> ValidateResponse:
        raw = await file.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid UTF-8: {exc}") from exc

        try:
            result = _runner().validate_content(content, rdf_format="turtle")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid RDF: {exc}") from exc
        return _result_to_response(result)

    # --- suites ---------------------------------------------------------

    @app.get("/suites", response_model=SuitesResponse)
    def list_suites() -> SuitesResponse:
        suites = _orchestrator().discover_test_suites()
        return SuitesResponse(
            suites=[SuiteSummary(name=s.name, total=s.total) for s in suites],
        )

    @app.post("/suites/{name}/run", response_model=SuiteReportResponse)
    def run_suite(name: str) -> SuiteReportResponse:
        orch = _orchestrator()
        suite = next((s for s in orch.discover_test_suites() if s.name == name), None)
        if suite is None:
            raise HTTPException(status_code=404, detail=f"Unknown suite: {name}")

        report = orch.run_test_suite(suite)
        return SuiteReportResponse(
            suite_name=report.suite_name,
            total=report.total,
            passed=report.passed,
            failed=report.failed,
        )

    return app


# Module-level app so `uvicorn tio_shacl.api:app` works
app = create_app()


def main() -> None:  # pragma: no cover
    """Entry point for the ``tio-shacl-api`` console script."""
    import uvicorn

    uvicorn.run("tio_shacl.api:app", host="127.0.0.1", port=8001, reload=False)


if __name__ == "__main__":  # pragma: no cover
    main()
