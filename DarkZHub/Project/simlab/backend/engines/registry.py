"""Engine registry -- the single integration point for SimLab engines.

The registry maps an engine's ``name`` to its class; ``get_engine``
returns a ready-to-use instance.  The API list endpoint, Celery tasks and
CLI tools all dispatch through this module, so adding an engine never
touches them.

To add a new engine:

1. Create ``engines/<my_engine>.py`` with a subclass of ``Engine``.
2. Decorate the class with ``@register``.
3. Import the module in ``engines/__init__.py`` so registration runs.

Nothing else in SimLab needs to change.
"""

from __future__ import annotations

from typing import Type

from .base import Engine

# {engine_name: EngineClass}
_REGISTRY: dict[str, Type[Engine]] = {}


def register(engine_cls: Type[Engine]) -> Type[Engine]:
    """Register an engine class.  Usable directly or as a class decorator."""
    if not getattr(engine_cls, "name", None):
        raise ValueError(f"{engine_cls.__name__} must define a non-empty 'name'")
    if engine_cls.name in _REGISTRY:
        raise ValueError(f"Engine '{engine_cls.name}' is already registered")
    _REGISTRY[engine_cls.name] = engine_cls
    return engine_cls


def get_engine(name: str) -> Engine:
    """Return a new instance of the engine registered under ``name``.

    Raises ``KeyError`` with a helpful message for unknown names.
    """
    try:
        return _REGISTRY[name]()
    except KeyError:
        available = ", ".join(sorted(_REGISTRY)) or "<none>"
        raise KeyError(
            f"Unknown engine '{name}'. Available engines: {available}"
        ) from None


def list_engines() -> list[dict]:
    """Return descriptors for every registered engine (API list endpoint)."""
    descriptors: list[dict] = []
    for name in sorted(_REGISTRY):
        cls = _REGISTRY[name]
        descriptors.append(
            {"name": cls.name, "version": cls.version, "param_schema": cls.param_schema}
        )
    return descriptors
