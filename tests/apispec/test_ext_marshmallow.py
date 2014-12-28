# -*- coding: utf-8 -*-
import pytest
from marshmallow import Schema, fields

from smore.apispec import APISpec

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
