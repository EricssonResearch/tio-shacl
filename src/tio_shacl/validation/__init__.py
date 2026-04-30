"""Validation runner + orchestrator for TIO SHACL."""

from .backends import (
    Backend,
    BackendError,
    JenaBackend,
    PyshaclBackend,
    TopbraidBackend,
    get_backend,
    list_backends,
    resolve_backend,
)
from .runner import ValidationResult, ValidationRunner, Violation

__all__ = [
    "ValidationResult",
    "ValidationRunner",
    "Violation",
    # Backends
    "Backend",
    "BackendError",
    "PyshaclBackend",
    "TopbraidBackend",
    "JenaBackend",
    "get_backend",
    "list_backends",
    "resolve_backend",
]


# Eagerly expose orchestrator types for convenience.
try:
    from .orchestrator import SuiteReport, TestOrchestrator, TestSuite  # noqa: F401

    __all__.extend(["SuiteReport", "TestOrchestrator", "TestSuite"])
except ImportError:
    pass
