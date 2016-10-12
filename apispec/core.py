# -*- coding: utf-8 -*-
"""Core apispec classes and functions."""
import re
from collections import OrderedDict

from apispec.compat import iterkeys
from .exceptions import APISpecError, PluginError

VALID_METHODS = [
    'get',
    'post',
    'put',
    'patch',
    'delete',
    'head',
]

OPENAPI_VERSION = SWAGGER_VERSION = '2.0'


def clean_operations(operations):
    """Ensure that all parameters with "in" equal to "path" are also required
    as required by the OpenAPI specification, as well as normalizing any
    references to global parameters.

    See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#parameterObject.

    :param dict operations: Dict mapping status codes to operations
    """
    def get_ref(x):
        return x if isinstance(x, dict) else {'$ref': '#/parameters/' + x}

    for operation in (operations or {}).values():
        if 'parameters' in operation:
            parameters = operation.get('parameters')
            for parameter in parameters:
                if (isinstance(parameter, dict) and
                        'in' in parameter and parameter['in'] == 'path'):
                    parameter['required'] = True
            operation['parameters'] = [get_ref(p) for p in parameters]


class Path(dict):
    """Represents an OpenAPI Path object.

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#pathsObject

    :param str path: The path template, e.g. ``"/pet/{petId}"``
    :param str method: The HTTP method.
    :param dict operation: The operation object, as a `dict`. See
        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#operationObject
    """

    def __init__(self, path=None, operations=None, **kwargs):
        self.path = path
        operations = operations or {}
        clean_operations(operations)
        invalid = {key for key in
                   set(iterkeys(operations)) - set(VALID_METHODS)
                   if not key.startswith('x-')}
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
    """Stores metadata that describes a RESTful API using the OpenAPI specification.

    :param str title: API title
    :param str version: API version
    :param tuple plugins: Import paths to plugins.
    :param dict info: Optional dict to add to `info`
        See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#infoObject
    :param **dict options: Optional top-level keys
        See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#swagger-object
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
        self._parameters = {}
        self._tags = []
        self._paths = OrderedDict()
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
            'swagger': OPENAPI_VERSION,
            'info': self.info,
            'definitions': self._definitions,
            'parameters': self._parameters,
            'paths': self._paths,
            'tags': self._tags
        }
        ret.update(self.options)
        return ret

    def add_parameter(self, param_id, location, **kwargs):
        """ Add a parameter which can be referenced.

        :param str param_id: identifier by which parameter may be referenced.
        :param str location: location of the parameter.
        :param dict kwargs: parameter fields.
        """
        if 'name' not in kwargs:
            kwargs['name'] = param_id
        kwargs['in'] = location
        self._parameters[param_id] = kwargs

    def add_tag(self, tag):
        """ Store information about a tag.

        :param dict tag: the dictionary storing information about the tag.
        """
        self._tags.append(tag)

    def add_path(self, path=None, operations=None, **kwargs):
        """Add a new path object to the spec.

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#pathsObject

        :param str|Path|None path: URL Path component or Path instance
        :param dict|None operations: describes the http methods and options for `path`
        :param dict kwargs: parameters used by any path helpers see :meth:`register_path_helper`
        """
        def normalize_path(path):
            if path and 'basePath' in self.options:
                pattern = '^{0}'.format(re.escape(self.options['basePath']))
                path = re.sub(pattern, '', path)

            return path

        p = path
        if isinstance(path, Path):
            p = path.path

        p = normalize_path(p)

        if isinstance(path, Path):
            path.path = p
        else:
            path = Path(path=p, operations=operations)
        # Execute plugins' helpers
        for func in self._path_helpers:
            try:
                ret = func(
                    self, path=path, operations=operations, **kwargs
                )
            except TypeError:
                continue
            if isinstance(ret, Path):
                ret.path = normalize_path(ret.path)
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

    def definition(self, name, properties=None, enum=None, description=None, **kwargs):
        """Add a new definition to the spec.

        .. note::

            If you are using `apispec.ext.marshmallow`, you can pass fields' metadata as
            additional keyword arguments.

            For example, to add ``enum`` to your field: ::

                status = fields.String(required=True, enum=['open', 'closed'])

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#definitionsObject
        """
        ret = {}
        # Execute all helpers from plugins
        for func in self._definition_helpers:
            try:
                ret.update(func(self, name, **kwargs))
            except TypeError:
                continue
        if properties:
            ret['properties'] = properties
        if enum:
            ret['enum'] = enum
        if description:
            ret['description'] = description
        self._definitions[name] = ret

    # PLUGIN INTERFACE

    # adapted from Sphinx
    def setup_plugin(self, path):
        """Import and setup a plugin. No-op if called twice
        for the same plugin.

        :param str path: Import path to the plugin.
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
            raise PluginError('Plugin "{0}" has no setup(spec) function'.format(path))
        else:
            mod.setup(self)
        # Each plugin gets a dict to store arbitrary data
        self.plugins[path] = {}
        return None

    def register_definition_helper(self, func):
        """Register a new definition helper. The helper **must** meet the following conditions:

        - Receive the `APISpec` instance as the first argument.
        - Receive the definition `name` as the second argument.
        - Include ``**kwargs`` in its signature.
        - Return a `dict` representation of the definition's Schema object.

        The helper may define any named arguments after the `name` argument.

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#definitionsObject

        :param callable func: The definition helper function.
        """
        self._definition_helpers.append(func)

    def register_path_helper(self, func):
        """Register a new path helper. The helper **must** meet the following conditions:

        - Receive the `APISpec` instance as the first argument.
        - Include ``**kwargs`` in signature.
        - Return a `apispec.core.Path` object.

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
