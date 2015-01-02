# -*- coding: utf-8 -*-
from __future__ import absolute_import

from marshmallow.compat import iteritems
from marshmallow import class_registry

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
    doc_operations = load_operations_from_docstring(view.__doc__)
    if not doc_operations:
        return
    operations = doc_operations.copy()
    plug = spec.plugins[NAME]
    for method, operation_dict in iteritems(doc_operations):
        for status_code, response_dict in iteritems(operation_dict.get('responses', {})):
            if 'schema' in response_dict:
                schema_cls = class_registry.get_class(response_dict['schema'])
                if not operations[method].get('responses'):
                    operations[method]['responses'] = {}
                # If Schema class has been registered as a definition, use {'$ref':...} syntax
                if schema_cls in plug.get('refs', {}):
                    schema_dict = {'$ref': plug['refs'][schema_cls]}
                else:  # use full schema object
                    schema_dict = swagger.schema2jsonschema(schema_cls)
                if not operations[method]['responses'].get(200):
                    operations[method]['responses'][200] = {}
                operations[method]['responses'][200]['schema'] = schema_dict
    return Path(operations=operations)

def setup(spec):
    spec.register_definition_helper(schema_definition_helper)
    spec.register_path_helper(schema_path_helper)
