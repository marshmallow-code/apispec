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
from . import swagger

NAME = 'apispec.ext.marshmallow'


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


def inspect_schema_for_auto_referencing(spec, original_schema_instance):
    """Parse given schema instance and reference eventual nested schemas
    :param spec: apispec.core.APISpec instance
    :param original_schema_instance: schema to parse
    """
    # spec.schema_name_resolver must be provided to use this function
    assert spec.schema_name_resolver

    plug = spec.plugins[NAME]
    if 'refs' not in plug:
        plug['refs'] = {}

    for field in original_schema_instance.fields.values():
        nested_schema_class = None

        if isinstance(field, marshmallow.fields.Nested):
            nested_schema_class = get_schema_class(field.schema)

        elif isinstance(field, marshmallow.fields.List) \
                and isinstance(field.container, marshmallow.fields.Nested):
            nested_schema_class = get_schema_class(field.container.schema)

        if nested_schema_class and nested_schema_class not in plug['refs']:
            definition_name = spec.schema_name_resolver(
                nested_schema_class,
            )
            if definition_name:
                spec.definition(
                    definition_name,
                    schema=nested_schema_class,
                )


def schema_definition_helper(spec, name, schema, **kwargs):
    """Definition helper that allows using a marshmallow
    :class:`Schema <marshmallow.Schema>` to provide OpenAPI
    metadata.

    :param type|Schema schema: A marshmallow Schema class or instance.
    """

    schema_cls = get_schema_class(schema)
    schema_instance = get_schema_instance(schema)

    # Store registered refs, keyed by Schema class
    plug = spec.plugins[NAME]
    if 'refs' not in plug:
        plug['refs'] = {}
    plug['refs'][schema_cls] = name

    json_schema = swagger.schema2jsonschema(schema_instance, spec=spec, name=name)

    # Auto reference schema if spec.schema_name_resolver
    if spec and spec.schema_name_resolver:
        inspect_schema_for_auto_referencing(spec, schema_instance)

    return json_schema


def schema_path_helper(spec, view=None, **kwargs):
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


def schema_operation_resolver(spec, operations, **kwargs):
    for operation in operations.values():
        if not isinstance(operation, dict):
            continue
        if 'parameters' in operation:
            operation['parameters'] = resolve_parameters(spec, operation['parameters'])
        if 'requestBody' in operation:  # OpenAPI 3
            resolve_schema_in_request_body(spec, operation['requestBody'])
        for response in operation.get('responses', {}).values():
            resolve_schema(spec, response)

def resolve_parameters(spec, parameters):
    resolved = []
    for parameter in parameters:
        if not isinstance(parameter.get('schema', {}), dict):
            schema_cls = resolve_schema_cls(parameter['schema'])
            if issubclass(schema_cls, marshmallow.Schema) and 'in' in parameter:
                del parameter['schema']
                resolved += swagger.schema2parameters(
                    schema_cls, default_in=parameter.pop('in'), spec=spec, **parameter)
                continue
        resolve_schema(spec, parameter)
        resolved.append(parameter)
    return resolved


def resolve_schema_in_request_body(spec, request_body):
    """Function to resolve a schema in a requestBody object - modifies then
    response dict to convert Marshmallow Schema object or class into dict

    :param APISpec spec: `APISpec` containing refs.
    """
    content = request_body['content']
    for content_type in content:
        schema = content[content_type]['schema']
        content[content_type]['schema'] = resolve_schema_dict(spec, schema)


def resolve_schema(spec, data):
    """Function to resolve a schema in a parameter or response - modifies the
    corresponding dict to convert Marshmallow Schema object or class into dict

    :param APISpec spec: `APISpec` containing refs.
    :param dict data: the parameter or response dictionary that may contain a schema
    """
    if 'schema' in data:  # OpenAPI 2
        data['schema'] = resolve_schema_dict(spec, data['schema'])
    if 'content' in data:  # OpenAPI 3
        for content_type in data['content']:
            schema = data['content'][content_type]['schema']
            data['content'][content_type]['schema'] = resolve_schema_dict(spec, schema)

def resolve_schema_dict(spec, schema, dump=True, use_instances=False):
    if isinstance(schema, dict):
        if schema.get('type') == 'array' and 'items' in schema:
            schema['items'] = resolve_schema_dict(spec, schema['items'], use_instances=use_instances)
        if schema.get('type') == 'object' and 'properties' in schema:
            schema['properties'] = {k: resolve_schema_dict(spec, v, dump=dump, use_instances=use_instances)
                                    for k, v in schema['properties'].items()}
        return schema
    plug = spec.plugins[NAME] if spec else {}
    if isinstance(schema, marshmallow.Schema) and use_instances:
        schema_cls = schema
    else:
        schema_cls = resolve_schema_cls(schema)

    if schema_cls in plug.get('refs', {}):
        ref_path = swagger.get_ref_path(spec.openapi_version.version[0])
        ref_schema = {'$ref': '#/{0}/{1}'.format(ref_path,
                                                 plug['refs'][schema_cls])}
        if getattr(schema, 'many', False):
            return {
                'type': 'array',
                'items': ref_schema,
            }
        return ref_schema
    if not isinstance(schema, marshmallow.Schema):
        schema = schema_cls
    return swagger.schema2jsonschema(schema, spec=spec, dump=dump)


def resolve_schema_cls(schema):
    if isinstance(schema, type) and issubclass(schema, marshmallow.Schema):
        return schema
    if isinstance(schema, marshmallow.Schema):
        return type(schema)
    return marshmallow.class_registry.get_class(schema)


def setup(spec):
    """Setup for the marshmallow plugin."""
    spec.register_definition_helper(schema_definition_helper)
    spec.register_path_helper(schema_path_helper)
    spec.register_operation_helper(schema_operation_resolver)
