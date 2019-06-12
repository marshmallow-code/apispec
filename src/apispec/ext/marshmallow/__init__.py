# -*- coding: utf-8 -*-
"""Marshmallow plugin for apispec. Allows passing a marshmallow
`Schema` to `spec.components.schema <apispec.core.Components.schema>`,
`spec.components.parameter <apispec.core.Components.parameter>`,
`spec.components.response <apispec.core.Components.response>`
(for response and headers schemas) and
`spec.path <apispec.APISpec.path>` (for responses and response headers).

Requires marshmallow>=2.15.2.

::

    from pprint import pprint
    import datetime as dt

    from marshmallow import Schema, fields

    class UserSchema(Schema):
        id = fields.Int(dump_only=True)
        name = fields.Str(description="The user's name")
        created = fields.Datetime(
            dump_only=True,
            default=dt.datetime.utcnow,
            default_doc="The current datetime"
        )

    spec.components.schema('User', schema=UserSchema)
    pprint(spec.to_dict()['definitions'])
    # {'User': {'properties': {'id': {'format': 'int32', 'type': 'integer'},
    #                         'name': {'description': "The user's name",
    #                                 'type': 'string'}},
    #         'type': 'object'}}

"""
from __future__ import absolute_import
import warnings

from apispec import BasePlugin
from apispec.compat import itervalues
from .common import resolve_schema_instance, make_schema_key
from .openapi import OpenAPIConverter


def resolver(schema):
    """Default implementation of a schema name resolver function
    """
    name = schema.__name__
    if name.endswith("Schema"):
        return name[:-6] or name
    return name


class MarshmallowPlugin(BasePlugin):
    """APISpec plugin handling marshmallow schemas

    :param callable schema_name_resolver: Callable to generate the schema definition name.
        Receives the `Schema` class and returns the name to be used in refs within
        the generated spec. When working with circular referencing this function
        must must not return `None` for schemas in a circular reference chain.

        Example: ::

            def schema_name_resolver(schema):
                return schema.__name__
    """

    def __init__(self, schema_name_resolver=None):
        super(MarshmallowPlugin, self).__init__()
        self.schema_name_resolver = schema_name_resolver or resolver
        self.spec = None
        self.openapi_version = None
        self.openapi = None

    def init_spec(self, spec):
        super(MarshmallowPlugin, self).init_spec(spec)
        self.spec = spec
        self.openapi_version = spec.openapi_version
        self.openapi = OpenAPIConverter(
            openapi_version=spec.openapi_version,
            schema_name_resolver=self.schema_name_resolver,
            spec=spec,
        )

    def resolve_parameters(self, parameters):
        resolved = []
        for parameter in parameters:
            if (
                isinstance(parameter, dict)
                and not isinstance(parameter.get("schema", {}), dict)
                and "in" in parameter
            ):
                schema_instance = resolve_schema_instance(parameter.pop("schema"))
                resolved += self.openapi.schema2parameters(
                    schema_instance, default_in=parameter.pop("in"), **parameter
                )
            else:
                self.resolve_schema(parameter)
                resolved.append(parameter)
        return resolved

    def resolve_schema_in_request_body(self, request_body):
        """Function to resolve a schema in a requestBody object - modifies then
        response dict to convert Marshmallow Schema object or class into dict
        """
        content = request_body["content"]
        for content_type in content:
            schema = content[content_type]["schema"]
            content[content_type]["schema"] = self.openapi.resolve_schema_dict(schema)

    def resolve_schema(self, data):
        """Function to resolve a schema in a parameter or response - modifies the
        corresponding dict to convert Marshmallow Schema object or class into dict

        :param APISpec spec: `APISpec` containing refs.
        :param dict|str data: either a parameter or response dictionary that may
            contain a schema, or a reference provided as string
        """
        if not isinstance(data, dict):
            return

        # OAS 2 component or OAS 3 header
        if "schema" in data:
            data["schema"] = self.openapi.resolve_schema_dict(data["schema"])
        # OAS 3 component except header
        if self.openapi_version.major >= 3:
            if "content" in data:
                for content in itervalues(data["content"]):
                    if "schema" in content:
                        content["schema"] = self.openapi.resolve_schema_dict(
                            content["schema"]
                        )

    def map_to_openapi_type(self, *args):
        """Decorator to set mapping for custom fields.

        ``*args`` can be:

        - a pair of the form ``(type, format)``
        - a core marshmallow field type (in which case we reuse that type's mapping)

        Examples: ::

            @ma_plugin.map_to_openapi_type('string', 'uuid')
            class MyCustomField(Integer):
                # ...

            @ma_plugin.map_to_openapi_type(Integer)  # will map to ('integer', 'int32')
            class MyCustomFieldThatsKindaLikeAnInteger(Integer):
                # ...
        """
        return self.openapi.map_to_openapi_type(*args)

    def schema_helper(self, name, _, schema=None, **kwargs):
        """Definition helper that allows using a marshmallow
        :class:`Schema <marshmallow.Schema>` to provide OpenAPI
        metadata.

        :param type|Schema schema: A marshmallow Schema class or instance.
        """
        if schema is None:
            return None

        schema_instance = resolve_schema_instance(schema)

        schema_key = make_schema_key(schema_instance)
        self.warn_if_schema_already_in_spec(schema_key)
        self.openapi.refs[schema_key] = name

        json_schema = self.openapi.schema2jsonschema(schema_instance)

        return json_schema

    def parameter_helper(self, parameter, **kwargs):
        """Parameter component helper that allows using a marshmallow
        :class:`Schema <marshmallow.Schema>` in parameter definition.

        :param dict parameter: parameter fields. May contain a marshmallow
            Schema class or instance.
        """
        # In OpenAPIv3, this only works when using the complex form using "content"
        self.resolve_schema(parameter)
        return parameter

    def response_helper(self, response, **kwargs):
        """Response component helper that allows using a marshmallow
        :class:`Schema <marshmallow.Schema>` in response definition.

        :param dict parameter: response fields. May contain a marshmallow
            Schema class or instance.
        """
        self.resolve_schema(response)
        if "headers" in response:
            for header in response["headers"].values():
                self.resolve_schema(header)
        return response

    def operation_helper(self, operations, **kwargs):
        for operation in operations.values():
            if not isinstance(operation, dict):
                continue
            if "parameters" in operation:
                operation["parameters"] = self.resolve_parameters(
                    operation["parameters"]
                )
            if self.openapi_version.major >= 3:
                if "requestBody" in operation:
                    self.resolve_schema_in_request_body(operation["requestBody"])
            for response in operation.get("responses", {}).values():
                self.resolve_schema(response)
                if "headers" in response:
                    for header in response["headers"].values():
                        self.resolve_schema(header)

    def warn_if_schema_already_in_spec(self, schema_key):
        """Method to warn the user if the schema has already been added to the
        spec.
        """
        if schema_key in self.openapi.refs:
            warnings.warn(
                "{} has already been added to the spec. Adding it twice may "
                "cause references to not resolve properly.".format(schema_key[0]),
                UserWarning,
            )
