# -*- coding: utf-8 -*-

import re

from marshmallow.compat import iterkeys
from .exceptions import APISpecError, PluginError

VALID_METHODS = [
    'get',
    'post',
    'put',
    'patch',
    'delete',
    'head',
]

SWAGGER_VERSION = '2.0'


def clean_operations(operations):
    """Ensure that all parameters with "in" equal to "path" are also required
    as required by the Swagger specification.

    See https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#parameterObject.

    :param dict operations: Dict mapping status codes to operations
    """
    for operation in (operations or {}).values():
        for parameter in operation.get('parameters', []):
            if parameter['in'] == 'path':
                parameter['required'] = True


class Path(dict):
    """Represents a Swagger Path object.

    https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#pathsObject

    :param str path: The path template, e.g. ``"/pet/{petId}"``
    :param str method: The HTTP method.
    :param dict operation: The operation object, as a `dict`. See
        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operationObject
    """

    def __init__(self, path=None, operations=None, **kwargs):
        self.path = path
        operations = operations or {}
        clean_operations(operations)
        invalid = set(iterkeys(operations)) - set(VALID_METHODS)
        if invalid:
            raise APISpecError(
                'One or more HTTP methods are invalid: {0}'.format(", ".join(invalid))
            )
        self.operations = operations
        kwargs.update(self.operations)
        super(Path, self).__init__(**kwargs)

    def to_dict(self):
        if not self.path:
            raise APISpecError('Path template is not specified')
        return {
            self.path: self.operations
        }

    def update(self, path, **kwargs):
        if path.path:
            self.path = path.path
        self.operations.update(path.operations)
        super(Path, self).update(path.operations)


class APISpec(object):
    """Stores metadata that describes a RESTful API using the Swagger 2.0 specification.

    :param str title: API title
    :param str version: API version
    :param tuple plugins: Paths to plugin modules
    :param dict info: Optional dict to add to `info`
        See https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#infoObject
    :param **dict options: Optional top-level keys
        See https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#swagger-object
    """

    def __init__(self, title, version, plugins=(), info=None, **options):
        self.info = {
            'title': title,
            'version': version,
        }
        self.info.update(info or {})
        self.options = options
        # Metadata
        self._definitions = {}
        self._paths = {}
        # Plugin and helpers
        self.plugins = {}
        self._definition_helpers = []
        self._path_helpers = []
        # {'get': {200: [my_helper]}}
        self._response_helpers = {}

        for plugin_path in plugins:
            self.setup_plugin(plugin_path)

    def to_dict(self):
        ret = {
            'swagger': SWAGGER_VERSION,
            'info': self.info,
            'definitions': self._definitions,
            'paths': self._paths,
        }
        ret.update(self.options)
        return ret

    def add_path(self, path=None, operations=None, **kwargs):
        """Add a new path object to the spec.

        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#paths-object-
        """
        if path and 'basePath' in self.options:
            pattern = '^{0}'.format(re.escape(self.options['basePath']))
            path = re.sub(pattern, '', path)
        path = Path(path=path, operations=operations)
        # Execute plugins' helpers
        for func in self._path_helpers:
            ret = func(
                self, path=path, operations=operations, **kwargs
            )
            if isinstance(ret, Path):
                path.update(ret)

        if not path.path:
            raise APISpecError('Path template is not specified')

        # Process response helpers for any path operations defined.
        # Rule is that method + http status exist in both operations and helpers
        methods = set(iterkeys(path.operations)) & set(iterkeys(self._response_helpers))
        for method in methods:
            responses = path.operations[method]['responses']
            statuses = set(iterkeys(responses)) & set(iterkeys(self._response_helpers[method]))
            for status_code in statuses:
                for func in self._response_helpers[method][status_code]:
                    responses[status_code].update(
                        func(self, **kwargs)
                    )

        self._paths.setdefault(path.path, path).update(path)

    def definition(self, name, properties=None, enum=None, **kwargs):
        """Add a new definition to the spec.

        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#definitionsObject
        """
        ret = {}
        # Execute all helpers from plugins
        for func in self._definition_helpers:
            ret.update(func(self, name, **kwargs))
        if properties:
            ret['properties'] = properties
        if enum:
            ret['enum'] = enum
        self._definitions[name] = ret

    # PLUGIN INTERFACE

    # adapted from Sphinx
    def setup_plugin(self, path):
        """Import and setup a plugin. No-op if called twice
        for the same plugin.

        :param str name: Import path to the plugin.
        :raise: PluginError if the given plugin is invalid.
        """
        if path in self.plugins:
            return
        try:
            mod = __import__(
                path, globals=None, locals=None, fromlist=('setup', )
            )
        except ImportError as err:
            raise PluginError(
                'Could not import plugin "{0}"\n\n{1}'.format(path, err)
            )
        if not hasattr(mod, 'setup'):
            raise PluginError('Plugin "{0}" has no setup() function.')
        else:
            mod.setup(self)
        self.plugins[path] = {}
        return None

    def register_definition_helper(self, func):
        """Register a new definition helper. The helper **must** meet the following conditions:

        - Receive the `APISpec` instance as the first argument.
        - Receive the definition `name` as the second argument.
        - Include ``**kwargs`` in its signature.
        - Return a `dict` representation of the definition's Schema object.

        The helper may define any named arguments after the `name` argument.

        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#definitionsObject

        :param callable func: The definition helper function.
        """
        self._definition_helpers.append(func)

    def register_path_helper(self, func):
        """Register a new path helper. The helper **must** meet the following conditions:

        - Receive the `APISpec` instance as the first argument.
        - Include ``**kwargs`` in signature.
        - Return a `smore.apispec.core.Path` object.

        The helper may define any named arguments in its signature.
        """
        self._path_helpers.append(func)

    def register_response_helper(self, func, method, status_code):
        """Register a new response helper. The helper **must** meet the following conditions:

        - Receive the `APISpec` instance as the first argument.
        - Include ``**kwargs`` in signature.
        - Return a `dict` response object.

        The helper may define any named arguments in its signature.
        """
        method = method.lower()
        if method not in self._response_helpers:
            self._response_helpers[method] = {}
        self._response_helpers[method].setdefault(status_code, []).append(func)
