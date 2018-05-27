# -*- coding: utf-8 -*-
import pytest
import json

from marshmallow.fields import Field, DateTime, Dict, String
from marshmallow import Schema

from apispec import APISpec
from apispec.ext.marshmallow import swagger
from .schemas import PetSchema, AnalysisSchema, SampleSchema, RunSchema, \
    SelfReferencingSchema, OrderedSchema, PatternedObjectSchema, \
    DefaultCallableSchema, AnalysisWithListSchema


description = 'This is a sample Petstore server.  You can find out more '
'about Swagger at <a href=\"http://swagger.wordnik.com\">http://swagger.wordnik.com</a> '
'or on irc.freenode.net, #swagger.  For this sample, you can use the api '
'key \"special-key\" to test the authorization filters'


@pytest.fixture()
def spec():
    return APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        description=description,
        plugins=[
            'apispec.ext.marshmallow'
        ]
    )


@pytest.fixture()
def spec_3():
    return APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        info={'description': description},
        security=[{'apiKey': []}],
        openapi_version='3.0.0',
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

    @pytest.mark.parametrize('schema', [AnalysisSchema, AnalysisSchema()])
    def test_resolve_schema_dict_auto_reference(self, schema):
        def resolver(schema):
            return schema.__name__
        spec = APISpec(
            title='Test auto-reference',
            version='2.0',
            description='Test auto-reference',
            plugins=(
                'apispec.ext.marshmallow',
            ),
            schema_name_resolver=resolver,
        )
        assert {} == spec._definitions

        spec.definition('analysis', schema=schema)
        spec.add_path('/test', operations={
            'get': {
                'responses': {
                    '200': {
                        'schema': {
                            '$ref': '#/definitions/analysis'
                        }
                    }
                }
            }
        })

        assert 3 == len(spec._definitions)

        assert 'analysis' in spec._definitions
        assert 'SampleSchema' in spec._definitions
        assert 'RunSchema' in spec._definitions

    @pytest.mark.parametrize('schema', [AnalysisWithListSchema, AnalysisWithListSchema()])
    def test_resolve_schema_dict_auto_reference_in_list(self, schema):
        def resolver(schema):
            return schema.__name__
        spec = APISpec(
            title='Test auto-reference',
            version='2.0',
            description='Test auto-reference',
            plugins=(
                'apispec.ext.marshmallow',
            ),
            schema_name_resolver=resolver,
        )
        assert {} == spec._definitions

        spec.definition('analysis', schema=schema)
        spec.add_path('/test', operations={
            'get': {
                'responses': {
                    '200': {
                        'schema': {
                            '$ref': '#/definitions/analysis'
                        }
                    }
                }
            }
        })

        assert 3 == len(spec._definitions)

        assert 'analysis' in spec._definitions
        assert 'SampleSchema' in spec._definitions
        assert 'RunSchema' in spec._definitions

    @pytest.mark.parametrize('schema', [AnalysisSchema, AnalysisSchema()])
    def test_resolve_schema_dict_auto_reference_return_none(self, schema):
        # this resolver return None
        def resolver(schema):
            return None

        spec = APISpec(
            title='Test auto-reference',
            version='2.0',
            description='Test auto-reference',
            plugins=(
                'apispec.ext.marshmallow',
            ),
            schema_name_resolver=resolver,
        )
        assert {} == spec._definitions

        spec.definition('analysis', schema=schema)
        spec.add_path('/test', operations={
            'get': {
                'responses': {
                    '200': {
                        'schema': {
                            '$ref': '#/definitions/analysis'
                        }
                    }
                }
            }
        })

        # Other shemas not yet referenced
        assert 1 == len(spec._definitions)

        spec_dict = spec.to_dict()
        assert spec_dict.get('definitions')
        assert 'analysis' in spec_dict['definitions']
        # Inspect/Read objects will not auto reference because resolver func
        # return None
        json.dumps(spec_dict)
        # Other shema still not referenced
        assert 1 == len(spec._definitions)


class TestCustomField:

    def test_can_use_custom_field_decorator(self, spec):

        @swagger.map_to_swagger_type(DateTime)
        class CustomNameA(Field):
            pass

        @swagger.map_to_swagger_type('integer', 'int32')
        class CustomNameB(Field):
            pass

        with pytest.raises(TypeError):
            @swagger.map_to_swagger_type('integer')
            class BadCustomField(Field):
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

    def test_schema_v3(self, spec_3):
        def pet_view():
            return '...'

        spec_3.add_path(
            path='/pet',
            view=pet_view,
            operations={
                'get': {
                    'responses': {
                        200: {
                            'content': {
                                'application/json': {
                                    'schema': PetSchema
                                }
                            }
                        }
                    }
                }
            }
        )
        p = spec_3._paths['/pet']
        assert 'get' in p
        op = p['get']
        assert 'responses' in op

        resolved_schema = op['responses'][200]['content']['application/json']['schema']
        assert resolved_schema == swagger.schema2jsonschema(PetSchema)

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

    def test_schema_in_docstring_v3(self, spec_3):

        def pet_view():
            """Not much to see here.

            ---
            get:
                responses:
                    200:
                        content:
                            application/json:
                                schema: tests.schemas.PetSchema
                        description: successful operation
            post:
                responses:
                    201:
                        content:
                            application/json:
                                schema: tests.schemas.PetSchema
                        description: successful operation
            """
            return '...'

        spec_3.add_path(path='/pet', view=pet_view)
        p = spec_3._paths['/pet']
        assert 'get' in p
        get = p['get']
        assert 'responses' in get

        resolved_schema = get['responses'][200]['content']['application/json']['schema']
        assert resolved_schema == swagger.schema2jsonschema(PetSchema)

        assert get['responses'][200]['description'] == 'successful operation'
        post = p['post']
        assert 'responses' in post

        resolved_schema = post['responses'][201]['content']['application/json']['schema']
        assert resolved_schema == swagger.schema2jsonschema(PetSchema)
        assert post['responses'][201]['description'] == 'successful operation'

    def test_schema_in_docstring_expand_parameters(self, spec):

        def pet_view():
            """Not much to see here.

            ---
            get:
                parameters:
                    - in: query
                      schema: tests.schemas.PetSchema
            post:
                parameters:
                    - in: body
                      description: "a pet schema"
                      required: true
                      name: pet
                      schema: tests.schemas.PetSchema
            """
            return '...'

        spec.add_path(path='/pet', view=pet_view)
        p = spec._paths['/pet']
        assert 'get' in p
        get = p['get']
        assert 'parameters' in get
        assert get['parameters'] == swagger.schema2parameters(PetSchema, default_in='query')
        post = p['post']
        assert 'parameters' in post
        assert post['parameters'] == swagger.schema2parameters(PetSchema, default_in='body', required=True,
                                                               name='pet', description='a pet schema')

    def test_schema_in_docstring_expand_parameters_v3(self, spec_3):
        def pet_view():
            """Not much to see here.

            ---
            get:
                parameters:
                    - in: query
                      schema: tests.schemas.PetSchema
            post:
                parameters:
                    - in: body
                      description: "a pet schema"
                      required: true
                      name: pet
                      schema: tests.schemas.PetSchema
            """
            return '...'

        spec_3.add_path(path='/pet', view=pet_view)
        p = spec_3._paths['/pet']
        assert 'get' in p
        get = p['get']
        assert 'parameters' in get
        assert get['parameters'] == swagger.schema2parameters(PetSchema, default_in='query', spec=spec_3)
        post = p['post']
        assert 'parameters' in post
        post_parameters = swagger.schema2parameters(PetSchema, default_in='body', required=True,
                                                     name='pet', description='a pet schema', spec=spec_3)
        assert post['parameters'] == post_parameters

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

    def test_schema_in_docstring_uses_ref_in_parameters_if_available(self, spec):
        spec.definition('Pet', schema=PetSchema)

        def pet_view():
            """Not much to see here.

            ---
            get:
                parameters:
                    - in: query
                      schema: tests.schemas.PetSchema
            post:
                parameters:
                    - in: body
                      schema: tests.schemas.PetSchema
            """
            return '...'

        spec.add_path(path='/pet', view=pet_view)
        p = spec._paths['/pet']
        assert 'get' in p
        get = p['get']
        assert 'parameters' in get
        for parameter in get['parameters']:
            assert 'schema' not in parameter
        post = p['post']
        assert 'parameters' in post
        assert len(post['parameters']) == 1
        assert post['parameters'][0]['schema']['$ref'] == '#/definitions/Pet'

    def test_schema_in_request_body(self, spec_3):
        def pet_view():
            """Not much to see here.

            ---
            post:
                requestBody:
                    content:
                        application/json:
                            schema: tests.schemas.PetSchema
            """
            return '...'
        spec_3.definition('Pet', schema=PetSchema)
        spec_3.add_path(path='/pet', view=pet_view)
        p = spec_3._paths['/pet']
        assert 'post' in p
        post = p['post']
        schema_ref = post['requestBody']['content']['application/json']['schema']
        assert schema_ref == {'$ref': '#/components/schemas/Pet'}

    def test_schema_array_in_docstring_uses_ref_if_available(self, spec):
        spec.definition('Pet', schema=PetSchema)

        def pet_view():
            """Not much to see here.

            ---
            get:
                parameters:
                    - in: body
                      schema:
                        type: array
                        items: tests.schemas.PetSchema
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
        assert 'parameters' in op
        len(op['parameters']) == 1
        assert 'responses' in op
        resolved_schema = {
            'type': 'array',
            'items': {'$ref': '#/definitions/Pet'}
        }
        assert op['parameters'][0]['schema'] == resolved_schema
        assert op['responses'][200]['schema'] == resolved_schema

    def test_schema_array_in_docstring_uses_ref_if_available_v3(self, spec_3):
        def pet_view():
            """Not much to see here.

            ---
            get:
                parameters:
                    - in: body
                      content:
                        application/json:
                            schema:
                                type: array
                                items: tests.schemas.PetSchema
                responses:
                    200:
                        content:
                            application/json:
                                schema:
                                    type: array
                                    items: tests.schemas.PetSchema
            """
            return '...'

        spec_3.add_path(path='/pet', view=pet_view)
        p = spec_3._paths['/pet']
        assert 'get' in p
        op = p['get']
        resolved_schema = {
            'type': 'array',
            'items': swagger.schema2jsonschema(PetSchema),
        }
        request_schema = op['parameters'][0]['content']['application/json']['schema']
        assert request_schema == resolved_schema
        response_schema = op['responses'][200]['content']['application/json']['schema']
        assert response_schema == resolved_schema

    def test_schema_partially_in_docstring(self, spec):
        spec.definition('Pet', schema=PetSchema)

        def pet_parents_view():
            """Not much to see here.

            ---
            get:
                responses:
                    200:
                        schema:
                            type: object
                            properties:
                                mother: tests.schemas.PetSchema
                                father: tests.schemas.PetSchema
            """
            return '...'

        spec.add_path(path='/parents', view=pet_parents_view)
        p = spec._paths['/parents']
        op = p['get']
        assert op['responses'][200]['schema'] == {
            'type': 'object',
            'properties': {
                'mother': {'$ref': '#/definitions/Pet'},
                'father': {'$ref': '#/definitions/Pet'},
            },
        }

    def test_other_than_http_method_in_docstring(self, spec):
        def pet_view():
            """Not much to see here.

            ---
            x-extension: value
            get:
                responses:
                    200:
                        schema:
                            type: array
                            items: tests.schemas.PetSchema
            foo:
                description: not a valid operation
                responses:
                    200:
                        description: more junk
            """
            return '...'

        spec.add_path(path='/pet', view=pet_view)
        p = spec._paths['/pet']
        assert 'get' in p
        assert 'x-extension' in p
        assert 'foo' not in p

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


@pytest.mark.skipif(swagger.MARSHMALLOW_VERSION_INFO[0] < 3,
                    reason='Values ignored in marshmallow 2')
class TestDictValues:
    def test_dict_values_resolve_to_additional_properties(self, spec):

        class SchemaWithDict(Schema):
            dict_field = Dict(values=String())

        spec.definition('SchemaWithDict', schema=SchemaWithDict)
        result = spec._definitions['SchemaWithDict']['properties']['dict_field']
        assert result == {'type': 'object', 'additionalProperties': {'type': 'string'}}

    def test_dict_with_empty_values_field(self, spec):

        class SchemaWithDict(Schema):
            dict_field = Dict()

        spec.definition('SchemaWithDict', schema=SchemaWithDict)
        result = spec._definitions['SchemaWithDict']['properties']['dict_field']
        assert result == {'type': 'object'}
