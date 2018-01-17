# -*- coding: utf-8 -*-
"""Core apispec classes and functions."""
import re
from collections import OrderedDict
from distutils import version

import yaml

from apispec.auto_ref_strategy import default_schema_name_resolver
from apispec.auto_ref_strategy import default_schema_class_resolver
from apispec.compat import iterkeys, PY2, unicode
from apispec.lazy_dict import LazyDict
from .exceptions import APISpecError, PluginError

VALID_METHODS = [
    'get',
    'post',
    'put',
    'patch',
    'delete',
    'head',
    'options',
]


def clean_operations(operations, openapi_major_version):
    """Ensure that all parameters with "in" equal to "path" are also required
    as required by the OpenAPI specification, as well as normalizing any
    references to global parameters.

    See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#parameterObject.

    :param dict operations: Dict mapping status codes to operations
    :param int openapi_major_version: The major version of the OpenAPI standard
        to use. Supported values are 2 and 3.
    """
    def get_ref(x, openapi_major_version):
        if isinstance(x, dict):
            return x

        ref_paths = {
            2: 'parameters',
            3: 'components/parameters',
        }
        ref_path = ref_paths[openapi_major_version]
        return {'$ref': '#/{0}/{1}'.format(ref_path, x)}

    for operation in (operations or {}).values():
        if 'parameters' in operation:
            parameters = operation.get('parameters')
            for parameter in parameters:
                if (isinstance(parameter, dict) and
                        'in' in parameter and parameter['in'] == 'path'):
                    parameter['required'] = True
            operation['parameters'] = [get_ref(p, openapi_major_version)
                                       for p in parameters]


class Path(dict):
    """Represents an OpenAPI Path object.

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#pathsObject

    :param str path: The path template, e.g. ``"/pet/{petId}"``
    :param str method: The HTTP method.
    :param dict operation: The operation object, as a `dict`. See
        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#operationObject
    :param str openapi_version: The version of the OpenAPI standard to use.
        Should be in the form '2.x' or '3.x.x' to comply with the OpenAPI
        standard.
    """

    def __init__(self, path=None, operations=None, openapi_version='2.0', **kwargs):
        self.path = path
        operations = operations or {}
        openapi_version = validate_openapi_version(openapi_version)
        clean_operations(operations, openapi_version.version[0])
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
    :param boolean auto_referencing: Active or disable auto_referencing of
         nested class.
    :param callable schema_class_resolver: Callable to return the convenient
         class 'Schema' for definition. Receive the schema class/instance and
         return a 'Schema' class. Need auto_referencing on.
    :param callable schema_name_resolver: Callable to generate the
        schema definition name. Receives the `Schema` class and returns the name to be used in
        refs within the generated spec. Need auto_referencing on.

        Example: ::

            def schema_name_resolver(schema):
                return schema.__name__
    :param str openapi_version: The version of the OpenAPI standard to use.
        Should be in the form '2.x' or '3.x.x' to comply with the OpenAPI
        standard.
    :param \*\*dict options: Optional top-level keys
        See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#swagger-object
    """

    def __init__(
        self,
        title,
        version,
        plugins=(),
        info=None,
        openapi_version='2.0',
        auto_referencing=False,
        schema_name_resolver=default_schema_name_resolver,
        schema_class_resolver=default_schema_class_resolver,
        **options
    ):
        self.info = {
            'title': title,
            'version': version,
        }
        self.info.update(info or {})

        self.openapi_version = validate_openapi_version(openapi_version)

        self.options = options
        # auto_ref
        self.auto_referencing = auto_referencing
        self.schema_name_resolver = schema_name_resolver
        self.schema_class_resolver = schema_class_resolver
        self.auto_generated_schemas = {}
        # Metadata
        self._definitions = {}
        self._parameters = {}
        self._tags = []
        self._paths = OrderedDict()
        # Plugin and helpers
        self.plugins = {}
        self._definition_helpers = []
        self._path_helpers = []
        self._operation_helpers = []
        # {'get': {200: [my_helper]}}
        self._response_helpers = {}

        for plugin_path in plugins:
            self.setup_plugin(plugin_path)

    def to_dict(self):
        ret = {
            'info': self.info,
            'paths': self._paths,
            'tags': self._tags
        }

        if self.openapi_version.version[0] == 2:
            ret['swagger'] = self.openapi_version.vstring
            ret['definitions'] = self._definitions
            ret['parameters'] = self._parameters

        elif self.openapi_version.version[0] == 3:
            ret['openapi'] = self.openapi_version.vstring
            ret['components'] = {
                'schemas': self._definitions,
                'parameters': self._parameters,
            }

        ret.update(self.options)
        return ret

    def to_yaml(self):
        return yaml.dump(self.to_dict(), Dumper=YAMLDumper)

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
            path = Path(path=p,
                        operations=operations,
                        openapi_version=self.openapi_version.vstring)
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
                operations = ret.operations
        if operations:
            for func in self._operation_helpers:
                func(self, path=path, operations=operations, **kwargs)

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

    def definition(self, name, properties=None, enum=None, description=None, extra_fields=None,
                   **kwargs):
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
                ret.update(func(self, name, definition=ret, **kwargs))
            except TypeError:
                continue
        if properties:
            ret['properties'] = properties
        if enum:
            ret['enum'] = enum
        if description:
            ret['description'] = description
        if extra_fields:
            ret.update(extra_fields)
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
            # Each plugin gets a dict to store arbitrary data
            self.plugins[path] = {}
            mod.setup(self)
        return None

    def register_definition_helper(self, func):
        """Register a new definition helper. The helper **must** meet the following conditions:

        - Receive the `APISpec` instance as the first argument.
        - Receive the definition `name` as the second argument.
        - Include ``**kwargs`` in its signature.
        - Return a `dict` representation of the definition's Schema object.

        The helper may define any named arguments after the `name` argument.
        ``kwargs`` will include (among other things):
        - definition (dict): current state of the definition

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

    def register_operation_helper(self, func):
        """Register a new operation helper. The helper **must** meet the following conditions:

        - Receive the `APISpec` instance as the first argument.
        - Receive ``operations`` as a keyword argument.
        - Include ``**kwargs`` in signature.

        The helper may define any named arguments in its signature.
        """
        self._operation_helpers.append(func)

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

def validate_openapi_version(openapi_version_str):
    """Function to validate the version of the OpenAPI passed into APISpec

    :param str openapi_version_str: the string version of the desired OpenAPI
        version used in the output
    """
    min_inclusive_version = version.LooseVersion('2.0')
    max_exclusive_version = version.LooseVersion('4.0')

    openapi_version = version.LooseVersion(openapi_version_str)

    if not min_inclusive_version <= openapi_version < max_exclusive_version:
        raise APISpecError(
            'Not a valid OpenAPI version number: {}'.format(openapi_version)
        )

    return openapi_version


class YAMLDumper(yaml.Dumper):

    @staticmethod
    def _represent_dict(dumper, instance):
        return dumper.represent_mapping('tag:yaml.org,2002:map',
                                        instance.items())

    if PY2:
        @staticmethod
        def _represent_unicode(dumper, uni):
            return yaml.ScalarNode(tag=u'tag:yaml.org,2002:str', value=uni)

if PY2:
    yaml.add_representer(unicode, YAMLDumper._represent_unicode,
                         Dumper=YAMLDumper)
yaml.add_representer(OrderedDict, YAMLDumper._represent_dict,
                     Dumper=YAMLDumper)
yaml.add_representer(LazyDict, YAMLDumper._represent_dict,
                     Dumper=YAMLDumper)
yaml.add_representer(Path, YAMLDumper._represent_dict,
                     Dumper=YAMLDumper)
