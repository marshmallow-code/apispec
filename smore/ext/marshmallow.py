# -*- coding: utf-8 -*-
from __future__ import absolute_import

import marshmallow
from marshmallow.compat import iteritems
from marshmallow.utils import is_instance_or_subclass

from smore import swagger
from smore.apispec.core import Path
from smore.apispec.utils import load_operations_from_docstring

NAME = 'smore.ext.marshmallow'

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
    return swagger.schema2jsonschema(schema)

def schema_path_helper(spec, view, **kwargs):
    operations = (
        load_operations_from_docstring(view.__doc__) or
        kwargs.get('operations')
    )
    if not operations:
        return
    operations = operations.copy()
    plug = spec.plugins[NAME]
    for method, operation_dict in iteritems(operations):
        for status_code, response_dict in iteritems(operation_dict.get('responses', {})):
            if 'schema' in response_dict:
                schema_dict = resolve_schema_dict(plug, response_dict['schema'])
                if not operations[method]['responses'].get(200):
                    operations[method]['responses'][200] = {}
                operations[method]['responses'][200]['schema'] = schema_dict
    return Path(operations=operations)

def resolve_schema_dict(plug, schema):
    if isinstance(schema, dict):
        return schema
    schema_cls = resolve_schema_cls(schema)
    if schema_cls in plug.get('refs', {}):
        return {'$ref': plug['refs'][schema_cls]}
    return swagger.schema2jsonschema(schema_cls)

def resolve_schema_cls(schema):
    if is_instance_or_subclass(schema, marshmallow.Schema):
        return schema
    return marshmallow.class_registry.get_class(schema)

def setup(spec):
    spec.register_definition_helper(schema_definition_helper)
    spec.register_path_helper(schema_path_helper)
