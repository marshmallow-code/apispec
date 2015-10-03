# -*- coding: utf-8 -*-
"""Marshmallow plugin for apispec. Allows passing a marshmallow
`Schema` to `APISpec.definition <apispec.APISpec.definition>`
and `APISpec.add_path <apispec.APISpec.add_path>` (for responses).

Requires marshmallow>=1.2.
"""
from __future__ import absolute_import

import marshmallow

from apispec.core import Path
from apispec.utils import load_operations_from_docstring
from . import swagger

NAME = 'apispec.ext.marshmallow'

def schema_definition_helper(spec, name, schema, **kwargs):
    """Definition helper that allows using a marshmallow
    :class:`Schema <marshmallow.Schema>` to provide Swagger
    metadata.

    :param type schema: A marshmallow Schema class.
    """
    # Store registered refs, keyed by Schema class
    plug = spec.plugins[NAME]
    if 'refs' not in plug:
        plug['refs'] = {}
    plug['refs'][schema] = name
    return swagger.schema2jsonschema(schema, spec=spec)

def schema_path_helper(spec, view, **kwargs):
    """Path helper that allows passing a Schema as a response. Responses can be
    defined in a view's docstring.
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

def resolve_schema_dict(spec, schema):
    if isinstance(schema, dict):
        return schema
    plug = spec.plugins[NAME] if spec else {}
    schema_cls = resolve_schema_cls(schema)
    if schema_cls in plug.get('refs', {}):
        return {'$ref': '#/definitions/{0}'.format(plug['refs'][schema_cls])}
    return swagger.schema2jsonschema(schema_cls, spec=spec)

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
