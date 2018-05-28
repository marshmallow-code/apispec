# -*- coding: utf-8 -*-
"""Base class for Plugin classes."""

class BasePlugin(object):
    """Base class for APISpec plugin

    :param APISpec spec: APISpec object this plugin instance is attached to
    """
    def __init__(self, spec=None):
        if spec is not None:
            self.init_spec(spec)

    def init_spec(self, spec):
        """Initialize plugin with APISpec object

        :param APISpec spec: APISpec object this plugin instance is attached to
        """
        self.spec = spec

    def definition_helper(self, name, definition, **kwargs):
        raise NotImplementedError

    def path_helper(self, path, operations, **kwargs):
        raise NotImplementedError

    def operation_helper(self, path, operations, **kwargs):
        raise NotImplementedError

    def response_helper(self, method, status_code, **kwargs):
        raise NotImplementedError
