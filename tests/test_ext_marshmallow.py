# -*- coding: utf-8 -*-

import json

import pytest

from marshmallow.fields import Field, DateTime, Dict, String
from marshmallow import Schema

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec.ext.marshmallow.openapi import MARSHMALLOW_VERSION_INFO
from .schemas import (
    PetSchema, AnalysisSchema, SampleSchema, RunSchema,
    SelfReferencingSchema, OrderedSchema, PatternedObjectSchema,
    DefaultValuesSchema, AnalysisWithListSchema,
)

from .utils import get_definitions, get_parameters, get_responses, get_paths


def ref_path(spec):
    if spec.openapi_version.version[0] < 3:
        return '#/definitions/'
    return '#/components/schemas/'


class TestDefinitionHelper:

    @pytest.mark.parametrize('schema', [PetSchema, PetSchema()])
    def test_can_use_schema_as_definition(self, spec, schema):
        spec.components.schema('Pet', schema=schema)
        definitions = get_definitions(spec)
        props = definitions['Pet']['properties']

        assert props['id']['type'] == 'integer'
        assert props['name']['type'] == 'string'

    def test_schema_helper_without_schema(self, spec):
        spec.components.schema('Pet', properties={'key': {'type': 'integer'}})
        definitions = get_definitions(spec)
        assert definitions['Pet']['properties'] == {'key': {'type': 'integer'}}

    @pytest.mark.parametrize('schema', [AnalysisSchema, AnalysisSchema()])
    def test_resolve_schema_dict_auto_reference(self, schema):
        def resolver(schema):
            return schema.__name__
        spec = APISpec(
            title='Test auto-reference',
            version='0.1',
            openapi_version='2.0',
            plugins=(
                MarshmallowPlugin(schema_name_resolver=resolver),
            ),
        )
        assert {} == get_definitions(spec)

        spec.components.schema('analysis', schema=schema)
        spec.path(
            '/test', operations={
                'get': {
                    'responses': {
                        '200': {
                            'schema': {
                                '$ref': '#/definitions/analysis',
                            },
                        },
                    },
                },
            },
        )
        definitions = get_definitions(spec)
        assert 3 == len(definitions)

        assert 'analysis' in definitions
        assert 'SampleSchema' in definitions
        assert 'RunSchema' in definitions

    @pytest.mark.parametrize('schema', [AnalysisWithListSchema, AnalysisWithListSchema()])
    def test_resolve_schema_dict_auto_reference_in_list(self, schema):
        def resolver(schema):
            return schema.__name__
        spec = APISpec(
            title='Test auto-reference',
            version='0.1',
            openapi_version='2.0',
            plugins=(
                MarshmallowPlugin(schema_name_resolver=resolver,),
            ),
        )
        assert {} == get_definitions(spec)

        spec.components.schema('analysis', schema=schema)
        spec.path(
            '/test', operations={
                'get': {
                    'responses': {
                        '200': {
                            'schema': {
                                '$ref': '#/definitions/analysis',
                            },
                        },
                    },
                },
            },
        )
        definitions = get_definitions(spec)
        assert 3 == len(definitions)

        assert 'analysis' in definitions
        assert 'SampleSchema' in definitions
        assert 'RunSchema' in definitions

    @pytest.mark.parametrize('schema', [AnalysisSchema, AnalysisSchema()])
    def test_resolve_schema_dict_auto_reference_return_none(self, schema):
        # this resolver return None
        def resolver(schema):
            return None
        spec = APISpec(
            title='Test auto-reference',
            version='0.1',
            openapi_version='2.0',
            plugins=(
                MarshmallowPlugin(schema_name_resolver=resolver,),
            ),
        )
        assert {} == get_definitions(spec)

        spec.components.schema('analysis', schema=schema)
        spec.path(
            '/test', operations={
                'get': {
                    'responses': {
                        '200': {
                            'schema': {
                                '$ref': '#/definitions/analysis',
                            },
                        },
                    },
                },
            },
        )
        # Other shemas not yet referenced
        definitions = get_definitions(spec)
        assert 1 == len(definitions)
        assert 'analysis' in definitions
        # Inspect/Read objects will not auto reference because resolver func
        # return None
        json.dumps(spec.to_dict())
        # Other shema still not referenced
        definitions = get_definitions(spec)
        assert 1 == len(definitions)


class TestComponentParameterHelper:

    @pytest.mark.parametrize('schema', [PetSchema, PetSchema()])
    def test_can_use_schema_in_parameter(self, spec, schema):
        if spec.openapi_version.major < 3:
            kwargs = {'schema': schema}
        else:
            kwargs = {'content': {'application/json': {'schema': schema}}}
        spec.components.parameter('Pet', 'body', **kwargs)
        parameter = get_parameters(spec)['Pet']
        assert parameter['in'] == 'body'
        if spec.openapi_version.major < 3:
            schema = parameter['schema']['properties']
        else:
            schema = parameter['content']['application/json']['schema']['properties']

        assert schema['name']['type'] == 'string'
        assert schema['password']['type'] == 'string'
        # dump_only field is ignored
        assert 'id' not in schema


class TestComponentResponseHelper:

    @pytest.mark.parametrize('schema', [PetSchema, PetSchema()])
    def test_can_use_schema_in_response(self, spec, schema):
        if spec.openapi_version.major < 3:
            kwargs = {'schema': schema}
        else:
            kwargs = {'content': {'application/json': {'schema': schema}}}
        spec.components.response('GetPetOk', **kwargs)
        response = get_responses(spec)['GetPetOk']
        if spec.openapi_version.major < 3:
            schema = response['schema']['properties']
        else:
            schema = response['content']['application/json']['schema']['properties']

        assert schema['id']['type'] == 'integer'
        assert schema['name']['type'] == 'string'
        # load_only field is ignored
        assert 'password' not in schema


class TestCustomField:

    def test_can_use_custom_field_decorator(self, spec_fixture):

        @spec_fixture.marshmallow_plugin.map_to_openapi_type(DateTime)
        class CustomNameA(Field):
            pass

        @spec_fixture.marshmallow_plugin.map_to_openapi_type('integer', 'int32')
        class CustomNameB(Field):
            pass

        with pytest.raises(TypeError):
            @spec_fixture.marshmallow_plugin.map_to_openapi_type('integer')
            class BadCustomField(Field):
                pass

        class CustomPetASchema(PetSchema):
            name = CustomNameA()

        class CustomPetBSchema(PetSchema):
            name = CustomNameB()

        spec_fixture.spec.components.schema('Pet', schema=PetSchema)
        spec_fixture.spec.components.schema('CustomPetA', schema=CustomPetASchema)
        spec_fixture.spec.components.schema('CustomPetB', schema=CustomPetBSchema)

        props_0 = get_definitions(spec_fixture.spec)['Pet']['properties']
        props_a = get_definitions(spec_fixture.spec)['CustomPetA']['properties']
        props_b = get_definitions(spec_fixture.spec)['CustomPetB']['properties']

        assert props_0['name']['type'] == 'string'
        assert 'format' not in props_0['name']

        assert props_a['name']['type'] == 'string'
        assert props_a['name']['format'] == 'date-time'

        assert props_b['name']['type'] == 'integer'
        assert props_b['name']['format'] == 'int32'


class TestOperationHelper:

    @staticmethod
    def ref_path(spec):
        if spec.openapi_version.version[0] < 3:
            return '#/definitions/'
        return '#/components/schemas/'

    @pytest.mark.parametrize('pet_schema', (PetSchema, PetSchema(), 'tests.schemas.PetSchema'))
    @pytest.mark.parametrize('spec_fixture', ('2.0', ), indirect=True)
    def test_schema_v2(self, spec_fixture, pet_schema):
        spec_fixture.spec.path(
            path='/pet',
            operations={
                'get': {
                    'responses': {
                        200: {
                            'schema': pet_schema,
                            'description': 'successful operation',
                        },
                    },
                },
            },
        )
        get = get_paths(spec_fixture.spec)['/pet']['get']
        assert get['responses'][200]['schema'] == spec_fixture.openapi.schema2jsonschema(
            PetSchema, dump=True, load=False,
        )
        assert get['responses'][200]['description'] == 'successful operation'

    @pytest.mark.parametrize('pet_schema', (PetSchema, PetSchema(), 'tests.schemas.PetSchema'))
    @pytest.mark.parametrize('spec_fixture', ('3.0.0', ), indirect=True)
    def test_schema_v3(self, spec_fixture, pet_schema):
        spec_fixture.spec.path(
            path='/pet',
            operations={
                'get': {
                    'responses': {
                        200: {
                            'content': {
                                'application/json': {
                                    'schema': pet_schema,
                                },
                            },
                            'description': 'successful operation',
                        },
                    },
                },
            },
        )
        get = get_paths(spec_fixture.spec)['/pet']['get']
        resolved_schema = get['responses'][200]['content']['application/json']['schema']
        assert resolved_schema == spec_fixture.openapi.schema2jsonschema(
            PetSchema, dump=True, load=False,
        )
        assert get['responses'][200]['description'] == 'successful operation'

    @pytest.mark.parametrize('spec_fixture', ('2.0', ), indirect=True)
    def test_schema_expand_parameters_v2(self, spec_fixture):
        spec_fixture.spec.path(
            path='/pet',
            operations={
                'get': {
                    'parameters': [{
                        'in': 'query',
                        'schema': PetSchema,
                    }],
                },
                'post': {
                    'parameters': [{
                        'in': 'body',
                        'description': 'a pet schema',
                        'required': True,
                        'name': 'pet',
                        'schema': PetSchema,
                    }],
                },
            },
        )
        p = get_paths(spec_fixture.spec)['/pet']
        get = p['get']
        assert get['parameters'] == spec_fixture.openapi.schema2parameters(
            PetSchema, default_in='query',
        )
        post = p['post']
        assert post['parameters'] == spec_fixture.openapi.schema2parameters(
            PetSchema, default_in='body', required=True,
            name='pet', description='a pet schema',
        )

    @pytest.mark.parametrize('spec_fixture', ('3.0.0', ), indirect=True)
    def test_schema_expand_parameters_v3(self, spec_fixture):
        spec_fixture.spec.path(
            path='/pet',
            operations={
                'get': {
                    'parameters': [{
                        'in': 'query',
                        'schema': PetSchema,
                    }],
                },
                'post': {
                    'requestBody': {
                        'description': 'a pet schema',
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': PetSchema,
                            },
                        },
                    },
                },
            },
        )
        p = get_paths(spec_fixture.spec)['/pet']
        get = p['get']
        assert get['parameters'] == spec_fixture.openapi.schema2parameters(
            PetSchema, default_in='query',
        )
        for parameter in get['parameters']:
            description = parameter.get('description', False)
            assert description
            name = parameter['name']
            assert description == PetSchema.description[name]
        post = p['post']
        post_schema = spec_fixture.openapi.resolve_schema_dict(PetSchema, dump=False, load=True)
        assert post['requestBody']['content']['application/json']['schema'] == post_schema
        assert post['requestBody']['description'] == 'a pet schema'
        assert post['requestBody']['required']

    @pytest.mark.parametrize('spec_fixture', ('2.0', ), indirect=True)
    def test_schema_uses_ref_if_available_v2(self, spec_fixture):
        spec_fixture.spec.components.schema('Pet', schema=PetSchema)
        spec_fixture.spec.path(
            path='/pet',
            operations={
                'get': {
                    'responses': {
                        200: {
                            'schema': PetSchema,
                        },
                    },
                },
            },
        )
        get = get_paths(spec_fixture.spec)['/pet']['get']
        assert get['responses'][200]['schema']['$ref'] == self.ref_path(spec_fixture.spec) + 'Pet'

    @pytest.mark.parametrize('spec_fixture', ('3.0.0', ), indirect=True)
    def test_schema_uses_ref_if_available_v3(self, spec_fixture):
        spec_fixture.spec.components.schema('Pet', schema=PetSchema)
        spec_fixture.spec.path(
            path='/pet',
            operations={
                'get': {
                    'responses': {
                        200: {
                            'content': {
                                'application/json': {
                                    'schema': PetSchema,
                                },
                            },
                        },
                    },
                },
            },
        )
        get = get_paths(spec_fixture.spec)['/pet']['get']
        assert get['responses'][200]['content']['application/json']['schema']['$ref'] == self.ref_path(
            spec_fixture.spec,
        ) + 'Pet'

    @pytest.mark.parametrize('spec_fixture', ('2.0', ), indirect=True)
    def test_schema_uses_ref_in_parameters_and_request_body_if_available_v2(self, spec_fixture):
        spec_fixture.spec.components.schema('Pet', schema=PetSchema)
        spec_fixture.spec.path(
            path='/pet',
            operations={
                'get': {
                    'parameters': [{
                        'in': 'query',
                        'schema': PetSchema,
                    }],
                },
                'post': {
                    'parameters': [{
                        'in': 'body',
                        'schema': PetSchema,
                    }],
                },
            },
        )
        p = get_paths(spec_fixture.spec)['/pet']
        assert 'schema' not in p['get']['parameters'][0]
        post = p['post']
        assert len(post['parameters']) == 1
        assert post['parameters'][0]['schema']['$ref'] == self.ref_path(spec_fixture.spec) + 'Pet'

    @pytest.mark.parametrize('spec_fixture', ('3.0.0', ), indirect=True)
    def test_schema_uses_ref_in_parameters_and_request_body_if_available_v3(self, spec_fixture):
        spec_fixture.spec.components.schema('Pet', schema=PetSchema)
        spec_fixture.spec.path(
            path='/pet',
            operations={
                'get': {
                    'parameters': [{
                        'in': 'query',
                        'schema': PetSchema,
                    }],
                },
                'post': {
                    'requestBody': {
                        'content': {
                            'application/json': {
                                'schema': PetSchema,
                            },
                        },
                    },
                },
            },
        )
        p = get_paths(spec_fixture.spec)['/pet']
        assert 'schema' in p['get']['parameters'][0]
        post = p['post']
        schema_ref = post['requestBody']['content']['application/json']['schema']
        assert schema_ref == {'$ref': self.ref_path(spec_fixture.spec) + 'Pet'}

    @pytest.mark.parametrize('spec_fixture', ('2.0', ), indirect=True)
    def test_schema_array_uses_ref_if_available_v2(self, spec_fixture):
        spec_fixture.spec.components.schema('Pet', schema=PetSchema)
        spec_fixture.spec.path(
            path='/pet',
            operations={
                'get': {
                    'parameters': [{
                        'in': 'body',
                        'schema': {
                            'type': 'array',
                            'items': PetSchema,
                        },
                    }],
                    'responses': {
                        200: {
                            'schema': {
                                'type': 'array',
                                'items': PetSchema,
                            },
                        },
                    },
                },
            },
        )
        get = get_paths(spec_fixture.spec)['/pet']['get']
        len(get['parameters']) == 1
        resolved_schema = {
            'type': 'array',
            'items': {'$ref': self.ref_path(spec_fixture.spec) + 'Pet'},
        }
        assert get['parameters'][0]['schema'] == resolved_schema
        assert get['responses'][200]['schema'] == resolved_schema

    @pytest.mark.parametrize('spec_fixture', ('3.0.0', ), indirect=True)
    def test_schema_array_uses_ref_if_available_v3(self, spec_fixture):
        spec_fixture.spec.components.schema('Pet', schema=PetSchema)
        spec_fixture.spec.path(
            path='/pet',
            operations={
                'get': {
                    'parameters': [{
                        'in': 'body',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'array',
                                    'items': PetSchema,
                                },
                            },
                        },
                    }],
                    'responses': {
                        200: {
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'array',
                                        'items': PetSchema,
                                    },
                                },
                            },
                        },
                    },
                },
            },
        )
        p = get_paths(spec_fixture.spec)['/pet']
        assert 'get' in p
        op = p['get']
        resolved_schema = {
            'type': 'array',
            'items': {'$ref': self.ref_path(spec_fixture.spec) + 'Pet'},
        }
        request_schema = op['parameters'][0]['content']['application/json']['schema']
        assert request_schema == resolved_schema
        response_schema = op['responses'][200]['content']['application/json']['schema']
        assert response_schema == resolved_schema

    @pytest.mark.parametrize('spec_fixture', ('2.0', ), indirect=True)
    def test_schema_partially_v2(self, spec_fixture):
        spec_fixture.spec.components.schema('Pet', schema=PetSchema)
        spec_fixture.spec.path(
            path='/parents',
            operations={
                'get': {
                    'responses': {
                        200: {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'mother': PetSchema,
                                    'father': PetSchema,
                                },
                            },
                        },
                    },
                },
            },
        )
        get = get_paths(spec_fixture.spec)['/parents']['get']
        assert get['responses'][200]['schema'] == {
            'type': 'object',
            'properties': {
                'mother': {'$ref': self.ref_path(spec_fixture.spec) + 'Pet'},
                'father': {'$ref': self.ref_path(spec_fixture.spec) + 'Pet'},
            },
        }

    @pytest.mark.parametrize('spec_fixture', ('3.0.0', ), indirect=True)
    def test_schema_partially_v3(self, spec_fixture):
        spec_fixture.spec.components.schema('Pet', schema=PetSchema)
        spec_fixture.spec.path(
            path='/parents',
            operations={
                'get': {
                    'responses': {
                        200: {
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'mother': PetSchema,
                                            'father': PetSchema,
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        )
        get = get_paths(spec_fixture.spec)['/parents']['get']
        assert get['responses'][200]['content']['application/json']['schema'] == {
            'type': 'object',
            'properties': {
                'mother': {'$ref': self.ref_path(spec_fixture.spec) + 'Pet'},
                'father': {'$ref': self.ref_path(spec_fixture.spec) + 'Pet'},
            },
        }

    def test_schema_global_state_untouched_2json(self, spec_fixture):
        assert RunSchema._declared_fields['sample']._Nested__schema is None
        data = spec_fixture.openapi.schema2jsonschema(RunSchema)
        json.dumps(data)
        assert RunSchema._declared_fields['sample']._Nested__schema is None

    def test_schema_global_state_untouched_2parameters(self, spec_fixture):
        assert RunSchema._declared_fields['sample']._Nested__schema is None
        data = spec_fixture.openapi.schema2parameters(RunSchema)
        json.dumps(data)
        assert RunSchema._declared_fields['sample']._Nested__schema is None

class TestCircularReference:

    def test_circular_referencing_schemas(self, spec):
        spec.components.schema('Analysis', schema=AnalysisSchema)
        spec.components.schema('Sample', schema=SampleSchema)
        spec.components.schema('Run', schema=RunSchema)
        definitions = get_definitions(spec)
        ref = definitions['Analysis']['properties']['sample']['$ref']
        assert ref == ref_path(spec) + 'Sample'

# Regression tests for issue #55
class TestSelfReference:

    def test_self_referencing_field_single(self, spec):
        spec.components.schema('SelfReference', schema=SelfReferencingSchema)
        definitions = get_definitions(spec)
        ref = definitions['SelfReference']['properties']['single']['$ref']
        assert ref == ref_path(spec) + 'SelfReference'

    def test_self_referencing_field_many(self, spec):
        spec.components.schema('SelfReference', schema=SelfReferencingSchema)
        definitions = get_definitions(spec)
        result = definitions['SelfReference']['properties']['many']
        assert result == {
            'type': 'array',
            'items': {'$ref': ref_path(spec) + 'SelfReference'},
        }

    def test_self_referencing_with_ref(self, spec):
        version = 'v2' if spec.openapi_version.version[0] < 3 else 'v3'
        spec.components.schema('SelfReference', schema=SelfReferencingSchema)
        definitions = get_definitions(spec)
        result = definitions['SelfReference']['properties'][
            'single_with_ref_{}'.format(version)
        ]
        assert result == {'$ref': ref_path(spec) + 'Self'}
        result = definitions['SelfReference']['properties'][
            'many_with_ref_{}'.format(version)
        ]
        assert result == {'type': 'array', 'items': {'$ref': ref_path(spec) + 'Selves'}}


class TestOrderedSchema:

    def test_ordered_schema(self, spec):
        spec.components.schema('Ordered', schema=OrderedSchema)
        result = get_definitions(spec)['Ordered']['properties']
        assert list(result.keys()) == ['field1', 'field2', 'field3', 'field4', 'field5']


class TestFieldWithCustomProps:
    def test_field_with_custom_props(self, spec):
        spec.components.schema('PatternedObject', schema=PatternedObjectSchema)
        result = get_definitions(spec)['PatternedObject']['properties']['count']
        assert 'x-count' in result
        assert result['x-count'] == 1

    def test_field_with_custom_props_passed_as_snake_case(self, spec):
        spec.components.schema('PatternedObject', schema=PatternedObjectSchema)
        result = get_definitions(spec)['PatternedObject']['properties']['count2']
        assert 'x-count2' in result
        assert result['x-count2'] == 2


class TestSchemaWithDefaultValues:
    def test_schema_with_default_values(self, spec):
        spec.components.schema('DefaultValuesSchema', schema=DefaultValuesSchema)
        definitions = get_definitions(spec)
        props = definitions['DefaultValuesSchema']['properties']
        assert props['number_auto_default']['default'] == 12
        assert props['number_manual_default']['default'] == 42
        assert 'default' not in props['string_callable_default']
        assert props['string_manual_default']['default'] == 'Manual'
        assert 'default' not in props['numbers']


@pytest.mark.skipif(
    MARSHMALLOW_VERSION_INFO[0] < 3,
    reason='Values ignored in marshmallow 2',
)
class TestDictValues:
    def test_dict_values_resolve_to_additional_properties(self, spec):

        class SchemaWithDict(Schema):
            dict_field = Dict(values=String())

        spec.components.schema('SchemaWithDict', schema=SchemaWithDict)
        result = get_definitions(spec)['SchemaWithDict']['properties']['dict_field']
        assert result == {'type': 'object', 'additionalProperties': {'type': 'string'}}

    def test_dict_with_empty_values_field(self, spec):

        class SchemaWithDict(Schema):
            dict_field = Dict()

        spec.components.schema('SchemaWithDict', schema=SchemaWithDict)
        result = get_definitions(spec)['SchemaWithDict']['properties']['dict_field']
        assert result == {'type': 'object'}
