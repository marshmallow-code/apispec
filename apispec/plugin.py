# -*- coding: utf-8 -*-
"""Base class for Plugin classes."""


from .exceptions import PluginMethodNotImplementedError


class BasePlugin(object):
    """Base class for APISpec plugin classes."""

    def init_spec(self, spec):
        """Initialize plugin with APISpec object

        :param APISpec spec: APISpec object this plugin instance is attached to
        """

    def schema_helper(self, name, definition, **kwargs):
        """May return definition as a dict."""
        raise PluginMethodNotImplementedError

    def parameter_helper(self, parameter, **kwargs):
        """May return parameter component description as a dict."""
        raise PluginMethodNotImplementedError

    def response_helper(self, response, **kwargs):
        """May return response component description as a dict."""
        raise PluginMethodNotImplementedError

    def path_helper(self, path=None, operations=None, **kwargs):
        """May return a path as string and mutate operations dict.

        :param str path: Path to the resource
        :param dict operations: A `dict` mapping HTTP methods to operation object. See
            https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#operationObject

        Return value should be a string or None. If a string is returned, it
        is set as the path.

        The last path helper returning a string sets the path value. Therefore,
        the order of plugin registration matters. However, generally, registering
        several plugins that return a path does not make sense.
        """
        raise PluginMethodNotImplementedError

    def operation_helper(self, path=None, operations=None, **kwargs):
        """May mutate operations.

        :param str path: Path to the resource
        :param dict operations: A `dict` mapping HTTP methods to operation object. See
        """
        raise PluginMethodNotImplementedError
