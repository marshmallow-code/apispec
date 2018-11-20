# -*- coding: utf-8 -*-
"""Core apispec classes and functions."""
from collections import OrderedDict

from apispec.compat import iterkeys, iteritems
from .exceptions import APISpecError, PluginMethodNotImplementedError
from .utils import OpenAPIVersion, deepupdate

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

    def get_ref(obj_type, obj, openapi_major_version):
        """Return object or rererence

        If obj is a dict, it is assumed to be a complete description and it is returned as is.
        Otherwise, it is assumed to be a reference name as string and the corresponding $ref
        string is returned.

        :param str obj_type: 'parameter' or 'response'
        :param dict|str obj: parameter or response in dict form or as ref_id string
        :param int openapi_major_version: The major version of the OpenAPI standard
        """
        if isinstance(obj, dict):
            return obj

        ref_paths = {
            'parameter': {
                2: 'parameters',
                3: 'components/parameters',
            },
            'response': {
                2: 'responses',
                3: 'components/responses',
            },
        }
        ref_path = ref_paths[obj_type][openapi_major_version]
        return {'$ref': '#/{0}/{1}'.format(ref_path, obj)}

    for operation in (operations or {}).values():
        if 'parameters' in operation:
            parameters = operation['parameters']
            for parameter in parameters:
                if (
                        isinstance(parameter, dict) and
                        'in' in parameter and parameter['in'] == 'path'
                ):
                    parameter['required'] = True
            operation['parameters'] = [
                get_ref('parameter', p, openapi_major_version) for p in parameters
            ]
        if 'responses' in operation:
            for code, response in iteritems(operation['responses']):
                operation['responses'][code] = get_ref('response', response, openapi_major_version)


class Components(object):
    """Stores OpenAPI components

    Components are top-level fields in Openapi v2.
    They became sub-fields of "components" top-level field in Openapi v3.
    """
    def __init__(self, plugins, openapi_version):
        self._plugins = plugins
        self.openapi_version = openapi_version
        self._schemas = {}
        self._parameters = {}
        self._responses = {}

    def to_dict(self):
        schemas_key = 'definitions' if self.openapi_version.major < 3 else 'schemas'
        return {
            'parameters': self._parameters,
            'responses': self._responses,
            schemas_key: self._schemas,
        }

    def schema(
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
        for plugin in self._plugins:
            try:
                ret.update(plugin.schema_helper(name, definition=ret, **kwargs) or {})
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
        self._schemas[name] = ret
        return self

    def parameter(self, param_id, location, **kwargs):
        """ Add a parameter which can be referenced.

        :param str param_id: identifier by which parameter may be referenced.
        :param str location: location of the parameter.
        :param dict kwargs: parameter fields.
        """
        ret = kwargs.copy()
        ret.setdefault('name', param_id)
        ret['in'] = location
        # Execute all helpers from plugins
        for plugin in self._plugins:
            try:
                ret.update(plugin.parameter_helper(**kwargs) or {})
            except PluginMethodNotImplementedError:
                continue
        self._parameters[param_id] = ret
        return self

    def response(self, ref_id, **kwargs):
        """Add a response which can be referenced.

        :param str ref_id: ref_id to use as reference
        :param dict kwargs: response fields
        """
        ret = kwargs.copy()
        # Execute all helpers from plugins
        for plugin in self._plugins:
            try:
                ret.update(plugin.response_helper(**kwargs) or {})
            except PluginMethodNotImplementedError:
                continue
        self._responses[ref_id] = ret
        return self


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
        self._tags = []
        self._paths = OrderedDict()

        # Plugins
        self.plugins = plugins
        for plugin in self.plugins:
            plugin.init_spec(self)

        # Components
        self.components = Components(self.plugins, self.openapi_version)

    def to_dict(self):
        ret = {
            'paths': self._paths,
            'tags': self._tags,
            'info': {
                'title': self.title,
                'version': self.version,
            },
        }
        if self.openapi_version.major < 3:
            ret['swagger'] = self.openapi_version.vstring
            ret.update(self.components.to_dict())
        else:
            ret['openapi'] = self.openapi_version.vstring
            ret.update({'components': self.components.to_dict()})
        ret = deepupdate(ret, self.options)
        return ret

    def to_yaml(self):
        """Render the spec to YAML. Requires PyYAML to be installed."""
        from .yaml_utils import dict_to_yaml
        return dict_to_yaml(self.to_dict())

    def tag(self, tag):
        """ Store information about a tag.

        :param dict tag: the dictionary storing information about the tag.
        """
        self._tags.append(tag)
        return self

    def path(self, path=None, operations=None, **kwargs):
        """Add a new path object to the spec.

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#pathsObject

        :param str|None path: URL path component
        :param dict|None operations: describes the http methods and options for `path`
        :param dict kwargs: parameters used by any path helpers see :meth:`register_path_helper`
        """
        operations = operations or OrderedDict()

        # Execute path helpers
        for plugin in self.plugins:
            try:
                ret = plugin.path_helper(path=path, operations=operations, **kwargs)
            except PluginMethodNotImplementedError:
                continue
            if ret is not None:
                path = ret
        if not path:
            raise APISpecError('Path template is not specified')

        # Execute operation helpers
        for plugin in self.plugins:
            try:
                plugin.operation_helper(path=path, operations=operations, **kwargs)
            except PluginMethodNotImplementedError:
                continue

        clean_operations(operations, self.openapi_version.major)

        self._paths.setdefault(path, operations).update(operations)
        return self
