"""SHACL validator backends.

Three implementations ship with the package, all satisfying the same
:class:`Backend` protocol:

- :class:`PyshaclBackend`  — calls the :pypi:`pyshacl` Python library directly
- :class:`TopbraidBackend` — drives ``java_wrappers/topbraid-shacl-cli.jar``
- :class:`JenaBackend`     — drives ``java_wrappers/jena-shacl-cli.jar``

Select one by name via :func:`get_backend` or the ``TIO_VALIDATOR`` environment
variable (read from :func:`resolve_backend`).
"""

from __future__ import annotations

import os

from .base import Backend, BackendError
from .jena import JenaBackend
from .pyshacl_backend import PyshaclBackend
from .topbraid import TopbraidBackend

_REGISTRY: dict[str, type[Backend]] = {
    "pyshacl": PyshaclBackend,
    "topbraid": TopbraidBackend,
    "jena": JenaBackend,
}


def list_backends() -> list[str]:
    """Return the list of registered backend names."""
    return sorted(_REGISTRY)


def get_backend(name: str) -> Backend:
    """Instantiate a backend by name.

    Raises:
        BackendError: if *name* is not registered.
    """
    try:
        cls = _REGISTRY[name.lower()]
    except KeyError as exc:
        raise BackendError(
            f"Unknown backend {name!r}. Available: {', '.join(list_backends())}"
        ) from exc
    return cls()


def resolve_backend(explicit: str | None = None) -> Backend:
    """Pick a backend from, in order: *explicit* argument, ``TIO_VALIDATOR`` env, default ``pyshacl``."""
    name = explicit or os.environ.get("TIO_VALIDATOR") or "pyshacl"
    return get_backend(name)


__all__ = [
    "Backend",
    "BackendError",
    "JenaBackend",
    "PyshaclBackend",
    "TopbraidBackend",
    "get_backend",
    "list_backends",
    "resolve_backend",
]
