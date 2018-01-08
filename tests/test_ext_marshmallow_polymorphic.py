# -*- coding: utf-8 -*-
from __future__ import print_function
import pytest
import json
from marshmallow import Schema, fields
from marshmallow.validate import Equal
from marshmallow_oneofschema import OneOfSchema

from apispec import APISpec
from apispec import utils
from apispec.ext.marshmallow import polymorphic

description = 'This is a sample Petstore server.  You can find out more '
'about Swagger at <a href=\"http://swagger.wordnik.com\">http://swagger.wordnik.com</a> '
'or on irc.freenode.net, #swagger.  For this sample, you can use the api '
'key \"special-key\" to test the authorization filters'


@pytest.fixture()
def spec_3():
    return APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        info={'description': description},
        openapi_version='3.0.0',
        plugins=[
            'apispec.ext.marshmallow'
        ]
    )


class Cat(Schema):
    pet_type = fields.Str(
        validate=Equal('cat'),
        required=True,
        load_from='petType',
        dump_to='petType'
    )
    name = fields.Str()


class Dog(Schema):
    pet_type = fields.Str(
        validate=Equal('dog'),
        required=True,
        load_from='petType',
        dump_to='petType',
    )
    bark = fields.Str()


class Lizard(Schema):
    pet_type = fields.Str(
        validate=Equal('lizard'),
        required=True,
        load_from='petType',
        dump_to='petType',
    )
    loves_rocks = fields.Boolean(
        load_from='lovesRocks',
        dump_to='lovesRocks',
    )

class Pet(OneOfSchema):
    type_schemas = {
        'cat': Cat,
        'dog': Dog,
        'lizard schema': Lizard,
    }
    type_field = 'petType'

class Home(Schema):
    pet = fields.Nested(Pet)

class TestIsOneofSchema:
    def test_is_oneof(self):
        assert polymorphic.is_oneof(Pet) is True

    def test_is_not_oneof(self):
        assert polymorphic.is_oneof(Cat) is False

class TestOneOfSchema2SchemaObject:
    def test(self, spec_3):
        def pet_view():
            """not much to see here
            ---
            post:
              requestBody:
                content:
                  application/json:
                    schema:
                      $ref: '#/components/schemas/Pet'
              responses:
                '201':
                  content:
                    application/json:
                      schema:
                        $ref: '#/components/schemas/Pet'
                  description: created
            """
        spec_3.add_path(path='/pet', view=pet_view)

        schema_object = polymorphic.oneof_schema_2_schema_object(spec_3, Pet)

        assert {'$ref': '#/components/schemas/cat'} in schema_object['oneOf']
        assert {'$ref': '#/components/schemas/dog'} in schema_object['oneOf']
        assert {'$ref': '#/components/schemas/lizard_schema'} in schema_object['oneOf']

        assert schema_object['discriminator'] == {'propertyName': 'petType',
                                                  'mapping': {
                                                      'cat': '#/components/schemas/cat',
                                                      'dog': '#/components/schemas/dog',
                                                      'lizard_schema': '#/components/schemas/lizard_schema',
                                                  }
                                                  }

        spec_3._definitions['Pet'] = schema_object
        print(json.dumps(spec_3.to_dict(), indent=4))
        utils.validate_swagger(spec_3)

class TestOneOfFunctional:
    def test(self, spec_3):
        def pet_view():
            """not much to see here
            ---
            post:
              requestBody:
                content:
                  application/json:
                    schema:
                      $ref: '#/components/schemas/Pet'
              responses:
                '201':
                  content:
                    application/json:
                      schema:
                        $ref: '#/components/schemas/Pet'
                  description: created
            """
        spec_3.add_path(path='/pet', view=pet_view)

        spec_3.definition('Pet', schema=Pet)

        pet_oneof = spec_3._definitions['Pet']['oneOf']
        assert {'$ref': '#/components/schemas/cat'} in pet_oneof

    def test_nested(self, spec_3):
        def home_view():
            """not much to see here
            ---
            post:
              requestBody:
                content:
                  application/json:
                    schema:
                      $ref: '#/components/schemas/Home'
              responses:
                '201':
                  content:
                    application/json:
                      schema:
                        $ref: '#/components/schemas/Home'
                  description: created
            """
        spec_3.add_path(path='/home', view=home_view)

        spec_3.definition('Home', schema=Home)

        pet_oneof = spec_3._definitions['Home']['properties']['pet']['oneOf']
        assert {'$ref': '#/components/schemas/cat'} in pet_oneof
