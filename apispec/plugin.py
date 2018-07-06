# -*- coding: utf-8 -*-
"""Base class for Plugin classes."""


from .exceptions import PluginMethodNotImplementedError

class BasePlugin(object):
    """Base class for APISpec plugin classes."""
    def init_spec(self, spec):
        """Initialize plugin with APISpec object

        :param APISpec spec: APISpec object this plugin instance is attached to
        """

    def definition_helper(self, name, definition, **kwargs):
        """Must return definition as a dict."""
        raise PluginMethodNotImplementedError

    def path_helper(self, path=None, operations=None, **kwargs):
        """May return a path as string and mutate operations dict.

        :param str path: Path to the resource
        :param dict operations: A `dict` mapping HTTP methods to operation object. See
            https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#operationObject

        Return value should be a string or None. If a string is returned, it
        is set as the path.

        The last path helper returning a string sets the path value. Therefore,
        the order of plugin registration matters. However, generally, registering
        several plugins that return a path does not make sense.
        """
        raise PluginMethodNotImplementedError

    def operation_helper(self, path=None, operations=None, **kwargs):
        """Should mutate operations.

        :param str path: Path to the resource
        :param dict operations: A `dict` mapping HTTP methods to operation object. See
        """
        raise PluginMethodNotImplementedError

    def response_helper(self, method, status_code, **kwargs):
        """Should return a dict to update the response description.

        Returning None is equivalent to returning an empty dictionary.
        """
        raise PluginMethodNotImplementedError
