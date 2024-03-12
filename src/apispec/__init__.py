"""Contains main apispec classes: `APISpec` and `BasePlugin`"""

import typing

from .core import APISpec
from .plugin import BasePlugin

__all__ = ["APISpec", "BasePlugin"]


def __getattr__(name: str) -> typing.Any:
    if name == "__version__":
        import importlib.metadata
        import warnings

        warnings.warn(
            "The '__version__' attribute is deprecated and will be removed in"
            " in a future version. Use feature detection or"
            " 'importlib.metadata.version(\"apispec\")' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return importlib.metadata.version("apispec")

    raise AttributeError(name)
