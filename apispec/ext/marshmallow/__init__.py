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


def schema_definition_helper(spec, name, schema, **kwargs):
    """Definition helper that allows using a marshmallow
    :class:`Schema <marshmallow.Schema>` to provide OpenAPI
    metadata.

    :param type schema: A marshmallow Schema class.
    """
    # Store registered refs, keyed by Schema class
    plug = spec.plugins[NAME]
    if 'refs' not in plug:
        plug['refs'] = {}
    plug['refs'][schema] = name
    return swagger.schema2jsonschema(schema, spec=spec, name=name)


def schema_path_helper(spec, view, **kwargs):
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
        load_operations_from_docstring(view.__doc__) or
        kwargs.get('operations')
    )
    if not operations:
        return
    operations = operations.copy()
    for operation in operations.values():
        for response in operation.get('responses', {}).values():
            if 'schema' in response:
                response['schema'] = resolve_schema_dict(spec, response['schema'])
    return Path(operations=operations)


def resolve_schema_dict(spec, schema, dump=True):
    if isinstance(schema, dict):
        if (schema.get('type') == 'array' and 'items' in schema):
            schema['items'] = resolve_schema_dict(spec, schema['items'])
        return schema
    plug = spec.plugins[NAME] if spec else {}
    schema_cls = resolve_schema_cls(schema)
    if schema_cls in plug.get('refs', {}):
        ref_schema = {'$ref': '#/definitions/{0}'.format(plug['refs'][schema_cls])}
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
