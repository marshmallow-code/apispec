# -*- coding: utf-8 -*-
"""Core apispec classes and functions."""
from collections import OrderedDict
from copy import deepcopy

from apispec.compat import iteritems

from .cleaners import Cleaner
from .exceptions import (
    APISpecError,
    PluginMethodNotImplementedError,
    DuplicateComponentNameError,
)
from .utils import OpenAPIVersion, deepupdate, COMPONENT_SUBSECTIONS


class Components(object):
    """Stores OpenAPI components

    Components are top-level fields in OAS v2.
    They became sub-fields of "components" top-level field in OAS v3.
    """

    def __init__(self, plugins, openapi_version):
        self._plugins = plugins
        self.openapi_version = openapi_version
        self._schemas = {}
        self._parameters = {}
        self._responses = {}
        self._security_schemes = {}

    def to_dict(self):
        subsections = {
            "schema": self._schemas,
            "parameter": self._parameters,
            "response": self._responses,
            "security_scheme": self._security_schemes,
        }
        return {
            COMPONENT_SUBSECTIONS[self.openapi_version.major][k]: v
            for k, v in iteritems(subsections)
            if v != {}
        }

    def schema(self, name, component=None, **kwargs):
        """Add a new schema to the spec.

        :param str name: identifier by which schema may be referenced.
        :param dict component: schema definition.

        .. note::

            If you are using `apispec.ext.marshmallow`, you can pass fields' metadata as
            additional keyword arguments.

            For example, to add ``enum`` and ``description`` to your field: ::

                status = fields.String(
                    required=True,
                    enum=['open', 'closed'],
                    description='Status (open or closed)',
                )

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#schemaObject
        """
        if name in self._schemas:
            raise DuplicateComponentNameError(
                'Another schema with name "{}" is already registered.'.format(name)
            )
        component = component or {}
        ret = component.copy()
        # Execute all helpers from plugins
        for plugin in self._plugins:
            try:
                ret.update(plugin.schema_helper(name, component, **kwargs) or {})
            except PluginMethodNotImplementedError:
                continue
        self._schemas[name] = ret
        return self

    def parameter(self, component_id, location, component=None, **kwargs):
        """ Add a parameter which can be referenced.

        :param str param_id: identifier by which parameter may be referenced.
        :param str location: location of the parameter.
        :param dict component: parameter fields.
        :param dict kwargs: plugin-specific arguments
        """
        if component_id in self._parameters:
            raise DuplicateComponentNameError(
                'Another parameter with name "{}" is already registered.'.format(
                    component_id
                )
            )
        component = component or {}
        ret = component.copy()
        ret.setdefault("name", component_id)
        ret["in"] = location

        # if "in" is set to "path", enforce required flag to True
        if location == "path":
            ret["required"] = True

        # Execute all helpers from plugins
        for plugin in self._plugins:
            try:
                ret.update(plugin.parameter_helper(component, **kwargs) or {})
            except PluginMethodNotImplementedError:
                continue
        self._parameters[component_id] = ret
        return self

    def response(self, component_id, component=None, **kwargs):
        """Add a response which can be referenced.

        :param str component_id: ref_id to use as reference
        :param dict component: response fields
        :param dict kwargs: plugin-specific arguments
        """
        if component_id in self._responses:
            raise DuplicateComponentNameError(
                'Another response with name "{}" is already registered.'.format(
                    component_id
                )
            )
        component = component or {}
        ret = component.copy()
        # Execute all helpers from plugins
        for plugin in self._plugins:
            try:
                ret.update(plugin.response_helper(component, **kwargs) or {})
            except PluginMethodNotImplementedError:
                continue
        self._responses[component_id] = ret
        return self

    def security_scheme(self, component_id, component):
        """Add a security scheme which can be referenced.

        :param str component_id: component_id to use as reference
        :param dict kwargs: security scheme fields
        """
        if component_id in self._security_schemes:
            raise DuplicateComponentNameError(
                'Another security scheme with name "{}" is already registered.'.format(
                    component_id
                )
            )
        self._security_schemes[component_id] = component
        return self


class APISpec(object):
    """Stores metadata that describes a RESTful API using the OpenAPI specification.

    :param str title: API title
    :param str version: API version
    :param list|tuple plugins: Plugin instances.
        See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#infoObject
    :param str|OpenAPIVersion openapi_version: OpenAPI Specification version.
        Should be in the form '2.x' or '3.x.x' to comply with the OpenAPI standard.
    :param dict options: Optional top-level keys
        See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#openapi-object
    """

    cleaner_class = Cleaner

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
            "paths": self._paths,
            "info": {"title": self.title, "version": self.version},
        }
        if self._tags:
            ret["tags"] = self._tags
        if self.openapi_version.major < 3:
            ret["swagger"] = self.openapi_version.vstring
            ret.update(self.components.to_dict())
        else:
            ret["openapi"] = self.openapi_version.vstring
            components_dict = self.components.to_dict()
            if components_dict:
                ret["components"] = components_dict
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

    def path(
        self,
        path=None,
        operations=None,
        summary=None,
        description=None,
        parameters=None,
        **kwargs
    ):
        """Add a new path object to the spec.

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#path-item-object

        :param str|None path: URL path component
        :param dict|None operations: describes the http methods and options for `path`
        :param str summary: short summary relevant to all operations in this path
        :param str description: long description relevant to all operations in this path
        :param list|None parameters: list of parameters relevant to all operations in this path
        :param dict kwargs: parameters used by any path helpers see :meth:`register_path_helper`
        """
        # operations and parameters must be deepcopied because they are mutated
        # in clean_operations and operation helpers and path may be called twice
        operations = deepcopy(operations) or OrderedDict()
        parameters = deepcopy(parameters) or []

        # Execute path helpers
        for plugin in self.plugins:
            try:
                ret = plugin.path_helper(
                    path=path, operations=operations, parameters=parameters, **kwargs
                )
            except PluginMethodNotImplementedError:
                continue
            if ret is not None:
                path = ret
        if not path:
            raise APISpecError("Path template is not specified.")

        # Execute operation helpers
        for plugin in self.plugins:
            try:
                plugin.operation_helper(path=path, operations=operations, **kwargs)
            except PluginMethodNotImplementedError:
                continue

        cleaner = self.cleaner_class(self.openapi_version.major)
        cleaner.clean_operations(operations)

        self._paths.setdefault(path, operations).update(operations)
        if summary is not None:
            self._paths[path]["summary"] = summary
        if description is not None:
            self._paths[path]["description"] = description
        if parameters:
            parameters = cleaner.refer_parameters(parameters)
            self._paths[path]["parameters"] = parameters
        return self
