# -*- coding: utf-8 -*-
"""Marshmallow plugin for apispec. Allows passing a marshmallow
`Schema` to `APISpec.definition <apispec.APISpec.definition>`
and `APISpec.add_path <apispec.APISpec.add_path>` (for responses).

Requires marshmallow>=2.0.

::

    from pprint import pprint

    from marshmallow import Schema, fields

    class UserSchema(Schema):
        id = fields.Int(dump_only=True)
        name = fields.Str(description="The user's name")

    spec.definition('User', schema=UserSchema)
    pprint(spec.to_dict()['definitions'])
    # {'User': {'properties': {'id': {'format': 'int32', 'type': 'integer'},
    #                         'name': {'description': "The user's name",
    #                                 'type': 'string'}},
    #         'type': 'object'}}

"""
from __future__ import absolute_import

import marshmallow

from apispec.core import Path
from apispec.utils import load_operations_from_docstring
from .swagger import Swagger


def get_schema_instance(schema):
    """Return schema instance for given schema (instance or class)
    :param schema: instance or class of marshmallow.Schema
    :return: schema instance of given schema (instance or class)
    """
    return schema() if isinstance(schema, type) else schema


def get_schema_class(schema):
    """Return schema class for given schema (instance or class)
    :param schema: instance or class of marshmallow.Schema
    :return: schema class of given schema (instance or class)
    """
    return schema if isinstance(schema, type) else type(schema)


def resolve_schema_cls(schema):
    if isinstance(schema, type) and issubclass(schema, marshmallow.Schema):
        return schema
    if isinstance(schema, marshmallow.Schema):
        return type(schema)
    return marshmallow.class_registry.get_class(schema)


class MarshmallowPlugin(object):
    """
    :param callable schema_name_resolver: Callable to generate the
        schema definition name. Receives the `Schema` class and returns the name to be used in
        refs within the generated spec.

        Example: ::

            def schema_name_resolver(schema):
                return schema.__name__
    """

    def __init__(self, spec=None, schema_name_resolver=None):
        self.swagger = Swagger()
        self.schema_name_resolver = schema_name_resolver
        if spec is not None:
            self.init_spec(spec)

    def init_spec(self, spec):
        self.spec = spec

    def inspect_schema_for_auto_referencing(self, original_schema_instance):
        """Parse given schema instance and reference eventual nested schemas
        :param spec: apispec.core.APISpec instance
        :param original_schema_instance: schema to parse
        """
        # schema_name_resolver must be provided to use this function
        assert self.schema_name_resolver

        for field in original_schema_instance.fields.values():
            nested_schema_class = None

            if isinstance(field, marshmallow.fields.Nested):
                nested_schema_class = get_schema_class(field.schema)

            elif isinstance(field, marshmallow.fields.List) \
                    and isinstance(field.container, marshmallow.fields.Nested):
                nested_schema_class = get_schema_class(field.container.schema)

            if nested_schema_class and nested_schema_class not in self.swagger.refs:
                definition_name = self.schema_name_resolver(
                    nested_schema_class,
                )
                if definition_name:
                    self.spec.definition(
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
                    resolved += self.swagger.schema2parameters(
                        schema_cls,
                        default_in=parameter.pop('in'), spec=self.spec, **parameter)
                    continue
            self.resolve_schema(parameter)
            resolved.append(parameter)
        return resolved

    def resolve_schema_in_request_body(self, request_body):
        """Function to resolve a schema in a requestBody object - modifies then
        response dict to convert Marshmallow Schema object or class into dict

        :param APISpec spec: `APISpec` containing refs.
        """
        content = request_body['content']
        for content_type in content:
            schema = content[content_type]['schema']
            content[content_type]['schema'] = self.swagger.resolve_schema_dict(self.spec, schema)

    def resolve_schema(self, data):
        """Function to resolve a schema in a parameter or response - modifies the
        corresponding dict to convert Marshmallow Schema object or class into dict

        :param APISpec spec: `APISpec` containing refs.
        :param dict data: the parameter or response dictionary that may contain a schema
        """
        if 'schema' in data:  # OpenAPI 2
            data['schema'] = self.swagger.resolve_schema_dict(self.spec, data['schema'])
        if 'content' in data:  # OpenAPI 3
            for content_type in data['content']:
                schema = data['content'][content_type]['schema']
                data['content'][content_type]['schema'] = self.swagger.resolve_schema_dict(
                    self.spec, schema)

    def definition_helper(self, name, schema, **kwargs):
        """Definition helper that allows using a marshmallow
        :class:`Schema <marshmallow.Schema>` to provide OpenAPI
        metadata.

        :param type|Schema schema: A marshmallow Schema class or instance.
        """

        schema_cls = get_schema_class(schema)
        schema_instance = get_schema_instance(schema)

        # Store registered refs, keyed by Schema class
        self.swagger.refs[schema_cls] = name

        json_schema = self.swagger.schema2jsonschema(schema_instance, spec=self.spec, name=name)

        # Auto reference schema if schema_name_resolver
        if self.schema_name_resolver:
            self.inspect_schema_for_auto_referencing(schema_instance)

        return json_schema

    def path_helper(self, view=None, **kwargs):
        """Path helper that allows passing a Schema as a response. Responses can be
        defined in a view's docstring.
        ::

            from pprint import pprint

            from my_app import Users, UserSchema

            class UserHandler:
                def get(self, user_id):
                    '''Get a user endpoint.
                    ---
                    description: Get a user
                    responses:
                        200:
                            description: A user
                            schema: UserSchema
                    '''
                    user = Users.get(id=user_id)
                    schema = UserSchema()
                    return schema.dumps(user)

            urlspec = (r'/users/{user_id}', UserHandler)
            spec.add_path(urlspec=urlspec)
            pprint(spec.to_dict()['paths'])
            # {'/users/{user_id}': {'get': {'description': 'Get a user',
            #                               'responses': {200: {'description': 'A user',
            #                                                   'schema': {'$ref': '#/definitions/User'}}}}}}

        ::

            from pprint import pprint

            from my_app import Users, UserSchema

            class UsersHandler:
                def get(self):
                    '''Get users endpoint.
                    ---
                    description: Get a list of users
                    responses:
                        200:
                            description: A list of user
                            schema:
                                type: array
                                items: UserSchema
                    '''
                    users = Users.all()
                    schema = UserSchema(many=True)
                    return schema.dumps(users)

            urlspec = (r'/users', UsersHandler)
            spec.add_path(urlspec=urlspec)
            pprint(spec.to_dict()['paths'])
            # {'/users': {'get': {'description': 'Get a list of users',
            #                     'responses': {200: {'description': 'A list of users',
            #                                         'schema': {'type': 'array',
            #                                                    'items': {'$ref': '#/definitions/User'}}}}}}}

        """
        operations = (
            kwargs.get('operations') or
            (view and load_operations_from_docstring(view.__doc__))
        )
        if not operations:
            return None
        operations = operations.copy()
        return Path(operations=operations)

    def operation_helper(self, operations, **kwargs):
        for operation in operations.values():
            if not isinstance(operation, dict):
                continue
            if 'parameters' in operation:
                operation['parameters'] = self.resolve_parameters(operation['parameters'])
            if 'requestBody' in operation:  # OpenAPI 3
                self.resolve_schema_in_request_body(operation['requestBody'])
            for response in operation.get('responses', {}).values():
                self.resolve_schema(response)


# Deprecated interface
def setup(spec):
    """Setup for the plugin."""
    plugin = MarshmallowPlugin(schema_name_resolver=spec.schema_name_resolver)
    plugin.init_spec(spec)
    spec.plugins.append(plugin)
