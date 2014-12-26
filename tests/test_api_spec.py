# -*- coding: utf-8 -*-
import pytest

from smore.apispec import APISpec


@pytest.fixture()
def spec():
    return APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        description='This is a sample server Petstore server.  You can find out more '
        'about Swagger at <a href=\"http://swagger.wordnik.com\">http://swagger.wordnik.com</a> '
        'or on irc.freenode.net, #swagger.  For this sample, you can use the api '
        'key \"special-key\" to test the authorization filters'
    )


class TestDefinitions:

    properties = {
        'id': {'type': 'integer', 'format': 'int64'},
        'name': {'type': 'string', 'example': 'doggie'},
    }

    def test_definition(self, spec):
        spec.definition('Pet', properties=self.properties)
        defs_json = spec.to_dict()['definitions']
        assert 'Pet' in defs_json
        assert defs_json['Pet']['properties'] == self.properties

    def test_definition_stores_kwargs(self, spec):
        enum = ['name', 'photoUrls']
        spec.definition(
            'Pet',
            properties=self.properties,
            enum=enum
        )
        defs_json = spec.to_dict()['definitions']
        assert defs_json['Pet']['enum'] == enum
