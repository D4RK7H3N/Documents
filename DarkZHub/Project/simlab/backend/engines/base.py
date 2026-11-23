"""Base class and shared validation for all SimLab engines.

An *engine* is a self-contained simulation implementation.  It exposes:

* ``name``         -- unique registry key (e.g. ``"insect_evo"``)
* ``version``      -- version string recorded on experiment results
* ``param_schema`` -- JSON-schema-like description of its parameters, used
  both for validation and to auto-generate the frontend form
* ``validate()``   -- fills defaults and raises ``ValueError`` on bad input
* ``run()``        -- executes the simulation and returns
  ``{"generations": [...], "summary": {...}}``

The rest of SimLab (API, Celery tasks, CLI tools) only interacts with
engines through the registry, so adding a new engine never requires
changes anywhere else.
"""

from __future__ import annotations


class EngineValidationError(ValueError):
    """Raised when user-supplied parameters fail validation.

    Subclasses ``ValueError`` so callers may catch either type.
    """


class Engine:
    """Base class that every simulation engine must subclass."""

    name: str = "base"
    version: str = "0.0.0"

    # Schema shape: {param_name: {"type": "number"|"integer"|"boolean"|"string",
    #                             "default": ..., "min": ..., "max": ...}}
    # ``min``/``max`` are optional and ignored for booleans and strings.
    param_schema: dict = {}

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def validate(self, params: dict) -> dict:
        """Validate ``params`` against ``param_schema`` and fill defaults.

        Returns a complete parameter dict.  Raises ``EngineValidationError``
        (a ``ValueError``) when a parameter is unknown, of the wrong type,
        or outside its declared range.
        """
        params = dict(params or {})

        # Reject unknown parameters so typos fail loudly instead of being
        # silently ignored.
        unknown = sorted(set(params) - set(self.param_schema))
        if unknown:
            raise EngineValidationError(
                f"Unknown parameter(s): {', '.join(unknown)}"
            )

        validated: dict = {}
        for key, spec in self.param_schema.items():
            if key in params and params[key] is not None:
                value = params[key]
                self._check_type(key, value, spec)
                self._check_range(key, value, spec)
            else:
                value = spec["default"]
            validated[key] = value
        return validated

    def _check_type(self, key: str, value, spec: dict) -> None:
        """Raise unless ``value`` matches the declared parameter type.

        ``bool`` is a subclass of ``int`` in Python, so booleans are
        explicitly excluded from the numeric types.
        """
        expected = spec.get("type", "number")
        if expected == "number":
            ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected == "integer":
            ok = isinstance(value, int) and not isinstance(value, bool)
        elif expected == "boolean":
            ok = isinstance(value, bool)
        elif expected == "string":
            ok = isinstance(value, str)
        else:  # Undeclared type in the schema: accept as-is.
            ok = True
        if not ok:
            raise EngineValidationError(
                f"Parameter '{key}' must be of type '{expected}', "
                f"got {type(value).__name__}"
            )

    def _check_range(self, key: str, value, spec: dict) -> None:
        """Raise unless ``value`` lies within the declared [min, max]."""
        if isinstance(value, (bool, str)):
            return  # Ranges do not apply to booleans or strings.
        if "min" in spec and value < spec["min"]:
            raise EngineValidationError(
                f"Parameter '{key}' must be >= {spec['min']} (got {value})"
            )
        if "max" in spec and value > spec["max"]:
            raise EngineValidationError(
                f"Parameter '{key}' must be <= {spec['max']} (got {value})"
            )
