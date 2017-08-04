# -*- coding: utf-8 -*-
import pytest
import json

from marshmallow.fields import Field, DateTime

from apispec import APISpec
from apispec.ext.marshmallow import swagger
from .schemas import PetSchema, AnalysisSchema, SampleSchema, RunSchema, SelfReferencingSchema,\
    OrderedSchema, PatternedObjectSchema, DefaultCallableSchema


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
            'apispec.ext.marshmallow'
        ]
    )

class TestDefinitionHelper:

    @pytest.mark.parametrize('schema', [PetSchema, PetSchema()])
    def test_can_use_schema_as_as_definition(self, spec, schema):
        spec.definition('Pet', schema=schema)
        assert 'Pet' in spec._definitions
        props = spec._definitions['Pet']['properties']

        assert props['id']['type'] == 'integer'
        assert props['name']['type'] == 'string'


class TestCustomField:

    def test_can_use_custom_field_decorator(self, spec):

        @swagger.map_to_swagger_field(DateTime)
        class CustomNameA(Field):
            pass

        @swagger.map_to_swagger_field('integer', 'int32')
        class CustomNameB(Field):
            pass

        class CustomPetASchema(PetSchema):
            name = CustomNameA()

        class CustomPetBSchema(PetSchema):
            name = CustomNameB()

        spec.definition('Pet', schema=PetSchema)
        spec.definition('CustomPetA', schema=CustomPetASchema)
        spec.definition('CustomPetB', schema=CustomPetBSchema)

        props_0 = spec._definitions['Pet']['properties']
        props_a = spec._definitions['CustomPetA']['properties']
        props_b = spec._definitions['CustomPetB']['properties']

        assert props_0['name']['type'] == 'string'
        assert 'format' not in props_0['name']

        assert props_a['name']['type'] == 'string'
        assert props_a['name']['format'] == 'date-time'

        assert props_b['name']['type'] == 'integer'
        assert props_b['name']['format'] == 'int32'

class TestOperationHelper:

    def test_schema(self, spec):
        def pet_view():
            return '...'

        spec.add_path(
            path='/pet',
            view=pet_view,
            operations={
                'get': {
                    'responses': {
                        200: {'schema': PetSchema}
                    }
                }
            }
        )
        p = spec._paths['/pet']
        assert 'get' in p
        op = p['get']
        assert 'responses' in op
        assert op['responses'][200]['schema'] == swagger.schema2jsonschema(PetSchema)

    def test_schema_in_docstring(self, spec):

        def pet_view():
            """Not much to see here.

            ---
            get:
                responses:
                    200:
                        schema: tests.schemas.PetSchema
                        description: successful operation
            post:
                responses:
                    201:
                        schema: tests.schemas.PetSchema
                        description: successful operation
            """
            return '...'

        spec.add_path(path='/pet', view=pet_view)
        p = spec._paths['/pet']
        assert 'get' in p
        get = p['get']
        assert 'responses' in get
        assert get['responses'][200]['schema'] == swagger.schema2jsonschema(PetSchema)
        assert get['responses'][200]['description'] == 'successful operation'
        post = p['post']
        assert 'responses' in post
        assert post['responses'][201]['schema'] == swagger.schema2jsonschema(PetSchema)
        assert post['responses'][201]['description'] == 'successful operation'

    def test_schema_in_docstring_uses_ref_if_available(self, spec):
        spec.definition('Pet', schema=PetSchema)

        def pet_view():
            """Not much to see here.

            ---
            get:
                responses:
                    200:
                        schema: tests.schemas.PetSchema
            """
            return '...'

        spec.add_path(path='/pet', view=pet_view)
        p = spec._paths['/pet']
        assert 'get' in p
        op = p['get']
        assert 'responses' in op
        assert op['responses'][200]['schema']['$ref'] == '#/definitions/Pet'

    def test_schema_array_in_docstring_uses_ref_if_available(self, spec):
        spec.definition('Pet', schema=PetSchema)

        def pet_view():
            """Not much to see here.

            ---
            get:
                responses:
                    200:
                        schema:
                            type: array
                            items: tests.schemas.PetSchema
            """
            return '...'

        spec.add_path(path='/pet', view=pet_view)
        p = spec._paths['/pet']
        assert 'get' in p
        op = p['get']
        assert 'responses' in op
        assert op['responses'][200]['schema'] == {
            'type': 'array',
            'items': {'$ref': '#/definitions/Pet'}
        }

    def test_schema_global_state_untouched_2json(self):
        assert RunSchema._declared_fields['sample']._Nested__schema is None
        data = swagger.schema2jsonschema(RunSchema)
        json.dumps(data)
        assert RunSchema._declared_fields['sample']._Nested__schema is None

    def test_schema_global_state_untouched_2parameters(self):
        assert RunSchema._declared_fields['sample']._Nested__schema is None
        data = swagger.schema2parameters(RunSchema)
        json.dumps(data)
        assert RunSchema._declared_fields['sample']._Nested__schema is None

class TestCircularReference:

    def test_circular_referencing_schemas(self, spec):
        spec.definition('Analysis', schema=AnalysisSchema)
        spec.definition('Sample', schema=SampleSchema)
        spec.definition('Run', schema=RunSchema)
        ref = spec._definitions['Analysis']['properties']['sample']['$ref']
        assert ref == '#/definitions/Sample'

# Regression tests for issue #55
class TestSelfReference:

    def test_self_referencing_field_single(self, spec):
        spec.definition('SelfReference', schema=SelfReferencingSchema)
        ref = spec._definitions['SelfReference']['properties']['single']['$ref']
        assert ref == '#/definitions/SelfReference'

    def test_self_referencing_field_many(self, spec):
        spec.definition('SelfReference', schema=SelfReferencingSchema)
        result = spec._definitions['SelfReference']['properties']['many']
        assert result == {
            'type': 'array',
            'items': {'$ref': '#/definitions/SelfReference'}
        }

    def test_self_referencing_with_ref(self, spec):
        spec.definition('SelfReference', schema=SelfReferencingSchema)
        result = spec._definitions['SelfReference']['properties']['single_with_ref']
        assert result == {'$ref': '#/definitions/Self'}

        result = spec._definitions['SelfReference']['properties']['many_with_ref']
        assert result == {'type': 'array', 'items': {'$ref': '#/definitions/Selves'}}


class TestOrderedSchema:

    def test_ordered_schema(self, spec):
        spec.definition('Ordered', schema=OrderedSchema)
        result = spec._definitions['Ordered']['properties']
        assert list(result.keys()) == ['field1', 'field2', 'field3', 'field4', 'field5']


class TestFieldWithCustomProps:
    def test_field_with_custom_props(self, spec):
        spec.definition('PatternedObject', schema=PatternedObjectSchema)
        result = spec._definitions['PatternedObject']['properties']['count']
        assert 'x-count' in result
        assert result['x-count'] == 1

    def test_field_with_custom_props_passed_as_snake_case(self, spec):
        spec.definition('PatternedObject', schema=PatternedObjectSchema)
        result = spec._definitions['PatternedObject']['properties']['count2']
        assert 'x-count2' in result
        assert result['x-count2'] == 2


class TestDefaultCanBeCallable:
    def test_default_can_be_callable(self, spec):
        spec.definition('DefaultCallableSchema', schema=DefaultCallableSchema)
        result = spec._definitions['DefaultCallableSchema']['properties']['numbers']
        assert result['default'] == []
