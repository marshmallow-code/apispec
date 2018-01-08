# -*- coding: utf-8 -*-

def is_oneof(schema):
    """Function to determine if a schema matches the oneOf api

    :param Schema schema: A marshmallow Schema instance or a class object
    :rtype: bool, True if the schema matches the oneOf API False otherwise
    """
    return hasattr(schema, 'type_field') and hasattr(schema, 'type_schemas')


def oneof_schema_2_schema_object(spec, oneof_schema):
    """Function to generate an OpenAPI schema object based on a oneOf Schema
    This function will add all of the Schemas to the spec and then return a
    dictionary containing references to those Schemas

    :param APISpec spec: Current `APISpec` instance
    :param OneOfSchema oneof_schema: A OneOfSchema instance or a class object
    """
    mapping = {}
    oneof = []
    for name, schema in oneof_schema.type_schemas.items():
        name = name.replace(' ', '_')
        spec.definition(name, schema=schema)
        ref = '#/components/schemas/{}'.format(name)
        mapping.update({name: ref})
        oneof.append({'$ref': ref})

    ret = {
        'oneOf': oneof,
        'discriminator': {
            'propertyName': oneof_schema.type_field,
            'mapping': mapping
        }
    }
    return ret
