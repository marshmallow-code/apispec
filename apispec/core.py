# -*- coding: utf-8 -*-
"""Core apispec classes and functions."""
import re
from collections import OrderedDict

from apispec.compat import iterkeys, iteritems
from .exceptions import APISpecError, PluginMethodNotImplementedError
from .utils import OpenAPIVersion

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
    references to global parameters. Also checks for invalid HTTP methods.

    See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#parameterObject.

    :param dict operations: Dict mapping status codes to operations
    :param int openapi_major_version: The major version of the OpenAPI standard
        to use. Supported values are 2 and 3.
    """
    invalid = {key for key in
               set(iterkeys(operations)) - set(VALID_METHODS)
               if not key.startswith('x-')}
    if invalid:
        raise APISpecError(
            'One or more HTTP methods are invalid: {0}'.format(', '.join(invalid)),
        )

    def get_ref(param, openapi_major_version):
        if isinstance(param, dict):
            return param

        ref_paths = {
            2: 'parameters',
            3: 'components/parameters',
        }
        ref_path = ref_paths[openapi_major_version]
        return {'$ref': '#/{0}/{1}'.format(ref_path, param)}

    for operation in (operations or {}).values():
        if 'parameters' in operation:
            parameters = operation.get('parameters')
            for parameter in parameters:
                if (
                    isinstance(parameter, dict) and
                    'in' in parameter and parameter['in'] == 'path'
                ):
                    parameter['required'] = True
            operation['parameters'] = [
                get_ref(p, openapi_major_version)
                for p in parameters
            ]


class APISpec(object):
    """Stores metadata that describes a RESTful API using the OpenAPI specification.

    :param str title: API title
    :param str version: API version
    :param list|tuple plugins: Plugin instances.
        See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#infoObject
    :param str|OpenAPIVersion openapi_version: The OpenAPI version to use.
        Should be in the form '2.x' or '3.x.x' to comply with the OpenAPI standard.
    :param dict options: Optional top-level keys
        See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#swagger-object
    """
    def __init__(self, title, version, openapi_version, plugins=(), **options):
        self.title = title
        self.version = version
        self.openapi_version = OpenAPIVersion(openapi_version)
        self.options = options

        # Metadata
        self._definitions = {}
        self._parameters = {}
        self._tags = []
        self._paths = OrderedDict()

        # Plugins
        self.plugins = plugins
        for plugin in self.plugins:
            plugin.init_spec(self)

    def to_dict(self):
        ret = {
            'paths': self._paths,
            'tags': self._tags,
        }

        if self.openapi_version.major == 2:
            ret['swagger'] = self.openapi_version.vstring
            ret['definitions'] = self._definitions
            ret['parameters'] = self._parameters
            ret.update(self.options)

        elif self.openapi_version.major == 3:
            ret['openapi'] = self.openapi_version.vstring
            ret.update(self.options)

            # deep update components object
            components = ret.setdefault('components', {})
            components.setdefault('schemas', {}).update(self._definitions)
            components.setdefault('parameters', {}).update(self._parameters)

        # Add title and version unless those were provided in options['info']
        info = ret.setdefault('info', {})
        info.setdefault('title', self.title)
        info.setdefault('version', self.version)

        return ret

    def to_yaml(self):
        """Render the spec to YAML. Requires PyYAML to be installed.
        """
        from .yaml_utils import dict_to_yaml
        return dict_to_yaml(self.to_dict())

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

        :param str|None path: URL path component
        :param dict|None operations: describes the http methods and options for `path`
        :param dict kwargs: parameters used by any path helpers see :meth:`register_path_helper`
        """
        def normalize_path(path):
            if path and 'basePath' in self.options:
                pattern = '^{0}'.format(re.escape(self.options['basePath']))
                path = re.sub(pattern, '', path)
            return path

        path = normalize_path(path)
        operations = operations or OrderedDict()

        # Execute path helpers
        for plugin in self.plugins:
            try:
                ret = plugin.path_helper(path=path, operations=operations, **kwargs)
            except PluginMethodNotImplementedError:
                continue
            if ret is not None:
                path = normalize_path(ret)
        if not path:
            raise APISpecError('Path template is not specified')

        # Execute operation helpers
        for plugin in self.plugins:
            try:
                plugin.operation_helper(path=path, operations=operations, **kwargs)
            except PluginMethodNotImplementedError:
                continue

        # Execute response helpers
        # TODO: cache response helpers output for each (method, status_code) couple
        for method, operation in iteritems(operations):
            if method in VALID_METHODS and 'responses' in operation:
                for status_code, response in iteritems(operation['responses']):
                    for plugin in self.plugins:
                        try:
                            response.update(plugin.response_helper(method, status_code, **kwargs) or {})
                        except PluginMethodNotImplementedError:
                            continue

        clean_operations(operations, self.openapi_version.major)

        self._paths.setdefault(path, operations).update(operations)

    def definition(
        self, name, properties=None, enum=None, description=None, extra_fields=None,
        **kwargs
    ):
        """Add a new definition to the spec.

        .. note::

            If you are using `apispec.ext.marshmallow`, you can pass fields' metadata as
            additional keyword arguments.

            For example, to add ``enum`` and ``description`` to your field: ::

                status = fields.String(
                    required=True,
                    enum=['open', 'closed'],
                    description='Status (open or closed)',
                )

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#definitionsObject
        """
        ret = {}
        # Execute all helpers from plugins
        for plugin in self.plugins:
            try:
                ret.update(plugin.definition_helper(name, definition=ret, **kwargs))
            except PluginMethodNotImplementedError:
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
