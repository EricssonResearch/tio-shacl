"""Validation runner + orchestrator for TIO SHACL."""

from .runner import ValidationResult, ValidationRunner, Violation

__all__ = [
    "ValidationResult",
    "ValidationRunner",
    "Violation",
]


def _reexport_orchestrator() -> None:
    """Re-export orchestrator types if the module is available.

    The orchestrator lives in a separate module so tests can import
    ``ValidationRunner`` without pulling in orchestration logic.
    """
    try:
        from .orchestrator import TestOrchestrator, TestSuite, SuiteReport  # noqa: F401
    except ImportError:
        pass


# Eager re-export for convenience (``from tio_shacl.validation import TestOrchestrator``).
try:
    from .orchestrator import SuiteReport, TestOrchestrator, TestSuite  # noqa: F401

    __all__.extend(["SuiteReport", "TestOrchestrator", "TestSuite"])
except ImportError:
    pass
