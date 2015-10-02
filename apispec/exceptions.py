# -*- coding: utf-8 -*-
"""Exception classes."""

class APISpecError(Exception):
    """Base class for all apispec-related errors."""
    pass

class PluginError(APISpecError):
    """Raised when a plugin cannot be found or is invalid."""
    pass
