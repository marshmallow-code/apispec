# -*- coding: utf-8 -*-
import pytest
from marshmallow import Schema, fields

from smore.apispec import APISpec
from smore import swagger

@pytest.fixture()
def spec():
    return APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        description='This is a sample Petstore server.  You can find out more '
        'about Swagger at <a href=\"http://swagger.wordnik.com\">http://swagger.wordnik.com</a> '
        'or on irc.freenode.net, #swagger.  For this sample, you can use the api '
        'key \"special-key\" to test the authorization filters',
        plugins=[
            'smore.ext.marshmallow'
        ]
    )

class TestDefinitionHelper:

    class PetSchema(Schema):
        id = fields.Int()
        name = fields.Str()

    def test_can_use_schema_as_definition(self, spec):
        spec.definition('Pet', schema=self.PetSchema)
        assert 'Pet' in spec._definitions
        props = spec._definitions['Pet']['properties']

        assert props['id']['type'] == 'integer'
        assert props['name']['type'] == 'string'

class TestOperationHelper:

    class PetSchema(Schema):
        id = fields.Int()
        name = fields.Str()

    def test_schema_in_docstring(self, spec):

        def pet_view():
            """Not much to see here.

            ---
            get:
                schema: PetSchema
            """
            return '...'

        spec.add_path(path='/pet', view=pet_view)
        p = spec._paths['/pet']
        assert 'get' in p
        op = p['get']
        assert 'responses' in op
        assert op['responses']['200'] == swagger.schema2jsonschema(self.PetSchema)

    def test_schema_in_docstring_uses_ref_if_available(self, spec):
        spec.definition('Pet', schema=self.PetSchema)

        def pet_view():
            """Not much to see here.

            ---
            get:
                schema: PetSchema
            """
            return '...'

        spec.add_path(path='/pet', view=pet_view)
        p = spec._paths['/pet']
        assert 'get' in p
        op = p['get']
        assert 'responses' in op
        assert op['responses']['200']['$ref'] == 'Pet'
