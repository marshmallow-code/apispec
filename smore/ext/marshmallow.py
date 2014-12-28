# -*- coding: utf-8 -*-
from smore import swagger

def schema_definition_helper(name, schema, **kwargs):
    """Definition helper that allows using a marshmallow
    :class:`Schema <marshmallow.Schema>` to provide Swagger
    metadata.

    :param type schema: A marshmallow Schema class.
    """
    return swagger.schema2jsonschema(schema)


def setup(spec):
    spec.register_definition_helper(schema_definition_helper)
