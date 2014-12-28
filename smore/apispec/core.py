# -*- coding: utf-8 -*-

from .exceptions import PluginError

class APISpec(object):
    """Stores metadata that describes a RESTful API using the Swagger 2.0 specification.
    """

    DEFAULT_CONTENT_TYPES = ['application/json']

    def __init__(self, plugins=(), default_content_types=None, *args, **kwargs):
        # Metadata
        self._definitions = {}
        self._paths = {}
        self.default_content_types = default_content_types or self.DEFAULT_CONTENT_TYPES
        # Plugin and helpers
        self._plugins = {}
        self._definition_helpers = []
        self._path_helpers = []

        for plugin_path in plugins:
            self.setup_plugin(plugin_path)

    def to_dict(self):
        return {
            'definitions': self._definitions,
            'paths': self._paths,
        }

    # NOTE: path and method are required, but they have defaults because
    # they may be added by a plugin
    def add_path(self, path=None, method=None, parameters=(), responses=(),
            produces=(), operation_id=None, summary=None, description=None, tags=()):
        """Add a new path object to the spec.

        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#paths-object-
        """
        method_key = method.lower() if method is not None else None
        ret = {
            path: {
                method_key: dict(
                    parameters=parameters,
                    responses=responses,
                    produces=produces or self.default_content_types,
                    operationId=operation_id,
                    summary=summary,
                    description=description,
                    tags=tags
                )
            }
        }

        # Execute plugins' helpers
        for func in self._path_helpers:
            ret.update(func(
                path=path, method=method, parameters=parameters(), responses=responses,
                produced=produces, operation_id=operation_id, summary=summary,
                description=description, tags=tags
            ))

        path_tpl = list(ret.keys())[0]
        if not path_tpl:  # Path template not specified
            raise ValueError('Must specify path template')
        self._paths.update(ret)

    def definition(self, name, properties=None, enum=None, **kwargs):
        """Add a new definition to the spec.

        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#definitionsObject
        """
        ret = {}
        if properties:
            ret['properties'] = properties
        if enum:
            ret['enum'] = enum
        # Execute all helpers from plugins
        for func in self._definition_helpers:
            ret.update(func(name, **kwargs))
        self._definitions[name] = ret

    # PLUGIN INTERFACE

    # adapted from Sphinx
    def setup_plugin(self, path):
        """Import and setup a plugin. No-op if called twice
        for the same plugin.

        :param str name: Import path to the plugin.
        :raise: PluginError if the given plugin is invalid.
        """
        if path in self._plugins:
            return
        try:
            mod = __import__(
                path, globals=None, locals=None, fromlist=('setup', )
            )
        except ImportError:
            raise PluginError(
                'Could not import plugin "{0}"'.format(path)
            )
        if not hasattr(mod, 'setup'):
            raise PluginError('Plugin "{0}" has no setup() function.')
        else:
            mod.setup(self)
        self._plugins[path] = mod
        return None

    def register_definition_helper(self, func):
        """Register a new definition helper. The helper **must** meet the following conditions:

        - Receive the definition `name` as the first argument.
        - Receive **kwargs.
        - Return a `dict` representation of the definition's Schema object.

        The helper may define any named arguments after the `name` argument.

        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#definitionsObject

        :param callable func: The definition helper function.
        """
        self._definition_helpers.append(func)

    def register_path_helper(self, func):
        self._path_helpers.append(func)
