# -*- coding: utf-8 -*-
"""Exception classes."""


class APISpecError(Exception):
    """Base class for all apispec-related errors."""


class PluginMethodNotImplementedError(APISpecError, NotImplementedError):
    """Raised when calling an unimplemented helper method in a plugin"""


class DuplicateComponentNameError(APISpecError):
    """Raised when registering two components with the same name"""


class OpenAPIError(APISpecError):
    """Raised when a OpenAPI spec validation fails."""
