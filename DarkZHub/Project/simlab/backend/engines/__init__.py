"""SimLab engines package.

Importing this package registers every built-in engine with the registry.
To add a new engine:

1. Create ``engines/<my_engine>.py`` with a subclass of
   ``engines.base.Engine`` decorated with ``@register``.
2. Import that module below so its registration runs at import time.

The API and task layers discover engines exclusively through
``engines.registry``, so no further changes are needed.
"""

from .base import Engine, EngineValidationError
from .registry import get_engine, list_engines, register

# Built-in engines: importing each module runs its @register decorator.
from . import insect_evo  # noqa: F401  (imported for registration side effect)

__all__ = [
    "Engine",
    "EngineValidationError",
    "get_engine",
    "list_engines",
    "register",
]
