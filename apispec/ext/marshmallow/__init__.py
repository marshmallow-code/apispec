# -*- coding: utf-8 -*-
"""Marshmallow plugin for apispec. Allows passing a marshmallow
`Schema` to `APISpec.definition <apispec.APISpec.definition>`
and `APISpec.path <apispec.APISpec.path>` (for responses).

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

import marshmallow

from apispec import BasePlugin
from .common import resolve_schema_cls, resolve_schema_instance
from .openapi import OpenAPIConverter


class MarshmallowPlugin(BasePlugin):
    """APISpec plugin handling marshmallow schemas

    :param callable schema_name_resolver: Callable to generate the schema definition name.
        Receives the `Schema` class and returns the name to be used in refs within
        the generated spec.

        Example: ::

            def schema_name_resolver(schema):
                return schema.__name__
    """
    def __init__(self, schema_name_resolver=None):
        super(MarshmallowPlugin, self).__init__()
        self.schema_name_resolver = schema_name_resolver
        self.spec = None
        self.openapi_version = None
        self.openapi = None

    def init_spec(self, spec):
        super(MarshmallowPlugin, self).init_spec(spec)
        self.spec = spec
        self.openapi_version = spec.openapi_version
        self.openapi = OpenAPIConverter(openapi_version=spec.openapi_version)

    def inspect_schema_for_auto_referencing(self, original_schema_instance):
        """Parse given schema instance and reference eventual nested schemas
        :param original_schema_instance: schema to parse
        """
        # schema_name_resolver must be provided to use this function
        assert self.schema_name_resolver

        for field in original_schema_instance.fields.values():
            nested_schema_class = None

            if isinstance(field, marshmallow.fields.Nested):
                nested_schema_class = self.openapi.resolve_schema_class(field.schema)

            elif isinstance(field, marshmallow.fields.List) \
                    and isinstance(field.container, marshmallow.fields.Nested):
                nested_schema_class = self.openapi.resolve_schema_class(field.container.schema)

            if nested_schema_class and nested_schema_class not in self.openapi.refs:
                definition_name = self.schema_name_resolver(
                    nested_schema_class,
                )
                if definition_name:
                    self.spec.components.schema(
                        definition_name,
                        schema=nested_schema_class,
                    )

    def resolve_parameters(self, parameters):
        resolved = []
        for parameter in parameters:
            if not isinstance(parameter.get('schema', {}), dict):
                schema_cls = resolve_schema_cls(parameter['schema'])
                if issubclass(schema_cls, marshmallow.Schema) and 'in' in parameter:
                    del parameter['schema']
                    resolved += self.openapi.schema2parameters(
                        schema_cls,
                        default_in=parameter.pop('in'), **parameter
                    )
                    continue
            self.resolve_schema(parameter, dump=False, load=True)
            resolved.append(parameter)
        return resolved

    def resolve_schema_in_request_body(self, request_body):
        """Function to resolve a schema in a requestBody object - modifies then
        response dict to convert Marshmallow Schema object or class into dict
        """
        content = request_body['content']
        for content_type in content:
            schema = content[content_type]['schema']
            content[content_type]['schema'] = self.openapi.resolve_schema_dict(schema, dump=False, load=True)

    def resolve_schema(self, data, dump=True, load=True):
        """Function to resolve a schema in a parameter or response - modifies the
        corresponding dict to convert Marshmallow Schema object or class into dict

        :param APISpec spec: `APISpec` containing refs.
        :param dict data: the parameter or response dictionary that may contain a schema
        :param bool dump: Introspect dump logic.
        :param bool load: Introspect load logic.
        """
        if self.openapi_version.major < 3:
            if 'schema' in data:
                data['schema'] = self.openapi.resolve_schema_dict(data['schema'], dump=dump, load=load)
        else:
            if 'content' in data:
                for content_type in data['content']:
                    schema = data['content'][content_type]['schema']
                    data['content'][content_type]['schema'] = self.openapi.resolve_schema_dict(
                        schema, dump=dump, load=load,
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

    def schema_helper(self, name, schema=None, **kwargs):
        """Definition helper that allows using a marshmallow
        :class:`Schema <marshmallow.Schema>` to provide OpenAPI
        metadata.

        :param type|Schema schema: A marshmallow Schema class or instance.
        """
        if schema is None:
            return None

        schema_cls = resolve_schema_cls(schema)
        schema_instance = resolve_schema_instance(schema)

        # Store registered refs, keyed by Schema class
        self.openapi.refs[schema_cls] = name

        json_schema = self.openapi.schema2jsonschema(schema_instance, name=name)

        # Auto reference schema if schema_name_resolver
        if self.schema_name_resolver:
            self.inspect_schema_for_auto_referencing(schema_instance)

        return json_schema

    def parameter_helper(self, **kwargs):
        """Parameter component helper that allows using a marshmallow
        :class:`Schema <marshmallow.Schema>` in parameter definition.

        :param type|Schema schema: A marshmallow Schema class or instance.
        """
        # In OpenAPIv3, this only works when using the complex form using "content"
        self.resolve_schema(kwargs, dump=False, load=True)
        return kwargs

    def response_helper(self, **kwargs):
        """Response component helper that allows using a marshmallow
        :class:`Schema <marshmallow.Schema>` in response definition.

        :param type|Schema schema: A marshmallow Schema class or instance.
        """
        self.resolve_schema(kwargs, dump=True, load=False)
        return kwargs

    def operation_helper(self, operations, **kwargs):
        for operation in operations.values():
            if not isinstance(operation, dict):
                continue
            if 'parameters' in operation:
                operation['parameters'] = self.resolve_parameters(operation['parameters'])
            if self.openapi_version.major >= 3:
                if 'requestBody' in operation:
                    self.resolve_schema_in_request_body(operation['requestBody'])
            for response in operation.get('responses', {}).values():
                self.resolve_schema(response, dump=True, load=False)
