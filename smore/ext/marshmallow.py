# -*- coding: utf-8 -*-
from __future__ import absolute_import

from marshmallow.compat import iteritems
from marshmallow import class_registry

from smore import swagger
from smore.apispec.core import Path
from smore.apispec.utils import load_operations_from_docstring

def schema_definition_helper(spec, name, schema, **kwargs):
    """Definition helper that allows using a marshmallow
    :class:`Schema <marshmallow.Schema>` to provide Swagger
    metadata.

    :param type schema: A marshmallow Schema class.
    """
    # Store registered refs, keyed by Schema class
    plug = spec.plugins['smore.ext.marshmallow']
    if 'refs' not in plug:
        plug['refs'] = {}
    plug['refs'][schema] = name
    return swagger.schema2jsonschema(schema)

def schema_path_helper(spec, view, **kwargs):
    doc_operations = load_operations_from_docstring(view.__doc__)
    if not doc_operations:
        return
    operations = doc_operations.copy()
    for method, config in iteritems(doc_operations):
        if 'schema' in config:
            schema_cls = class_registry.get_class(config['schema'])
            if not operations[method].get('responses'):
                operations[method]['responses'] = {}
            operations[method]['responses']['200'] = swagger.schema2jsonschema(schema_cls)
    return Path(operations=operations)

def setup(spec):
    spec.register_definition_helper(schema_definition_helper)
    spec.register_path_helper(schema_path_helper)
