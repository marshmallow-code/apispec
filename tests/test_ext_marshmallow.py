# -*- coding: utf-8 -*-
import pytest

from apispec import APISpec
from apispec.ext.marshmallow import swagger
from .schemas import PetSchema, AnalysisSchema, SampleSchema, RunSchema, SelfReferencingSchema


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
