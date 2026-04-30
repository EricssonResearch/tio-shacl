"""Backend protocol and shared helpers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rdflib import Graph

# Forward reference so we don't create a cycle with validation.runner
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import ValidationResult


class BackendError(RuntimeError):
    """Raised when a backend cannot be instantiated or invoked."""


@runtime_checkable
class Backend(Protocol):
    """A SHACL validation backend.

    All backends expose the same single method: take a (data, shapes) graph pair
    and return a :class:`ValidationResult`. Backends are responsible for
    serialising graphs to whatever format their engine expects (in-memory call,
    subprocess with temp files, HTTP, ...).
    """

    name: str

    def validate(self, data: Graph, shapes: Graph) -> "ValidationResult":
        """Return a :class:`ValidationResult` for validating *data* against *shapes*."""
        ...
