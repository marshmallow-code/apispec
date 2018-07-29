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
    DefaultValuesSchema, AnalysisWithListSchema
)


def ref_path(spec):
    if spec.openapi_version.version[0] < 3:
        return '#/definitions/'
    return '#/components/schemas/'


class TestDefinitionHelper:

    @pytest.mark.parametrize('schema', [PetSchema, PetSchema()])
    def test_can_use_schema_as_definition(self, spec, schema):
        spec.definition('Pet', schema=schema)
        assert 'Pet' in spec._definitions
        props = spec._definitions['Pet']['properties']

        assert props['id']['type'] == 'integer'
        assert props['name']['type'] == 'string'

    @pytest.mark.parametrize('deprecated_interface', (True, False))
    @pytest.mark.parametrize('schema', [AnalysisSchema, AnalysisSchema()])
    def test_resolve_schema_dict_auto_reference(self, schema, deprecated_interface):
        def resolver(schema):
            return schema.__name__
        if deprecated_interface:
            spec = APISpec(
                title='Test auto-reference',
                version='0.1',
                description='Test auto-reference',
                plugins=(
                    'apispec.ext.marshmallow',
                ),
                schema_name_resolver=resolver,
            )
        else:
            spec = APISpec(
                title='Test auto-reference',
                version='0.1',
                description='Test auto-reference',
                plugins=(
                    MarshmallowPlugin(schema_name_resolver=resolver),
                ),
            )
        assert {} == spec._definitions

        spec.definition('analysis', schema=schema)
        spec.add_path(
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

        assert 3 == len(spec._definitions)

        assert 'analysis' in spec._definitions
        assert 'SampleSchema' in spec._definitions
        assert 'RunSchema' in spec._definitions

    @pytest.mark.parametrize('deprecated_interface', (True, False))
    @pytest.mark.parametrize('schema', [AnalysisWithListSchema, AnalysisWithListSchema()])
    def test_resolve_schema_dict_auto_reference_in_list(self, schema, deprecated_interface):
        def resolver(schema):
            return schema.__name__
        if deprecated_interface:
            spec = APISpec(
                title='Test auto-reference',
                version='0.1',
                description='Test auto-reference',
                plugins=(
                    'apispec.ext.marshmallow',
                ),
                schema_name_resolver=resolver,
            )
        else:
            spec = APISpec(
                title='Test auto-reference',
                version='0.1',
                description='Test auto-reference',
                plugins=(
                    MarshmallowPlugin(schema_name_resolver=resolver,),
                ),
            )
        assert {} == spec._definitions

        spec.definition('analysis', schema=schema)
        spec.add_path(
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

        assert 3 == len(spec._definitions)

        assert 'analysis' in spec._definitions
        assert 'SampleSchema' in spec._definitions
        assert 'RunSchema' in spec._definitions

    @pytest.mark.parametrize('deprecated_interface', (True, False))
    @pytest.mark.parametrize('schema', [AnalysisSchema, AnalysisSchema()])
    def test_resolve_schema_dict_auto_reference_return_none(self, schema, deprecated_interface):
        # this resolver return None
        def resolver(schema):
            return None
        if deprecated_interface:
            spec = APISpec(
                title='Test auto-reference',
                version='0.1',
                description='Test auto-reference',
                plugins=(
                    'apispec.ext.marshmallow',
                ),
                schema_name_resolver=resolver,
            )
        else:
            spec = APISpec(
                title='Test auto-reference',
                version='0.1',
                description='Test auto-reference',
                plugins=(
                    MarshmallowPlugin(schema_name_resolver=resolver,),
                ),
            )
        assert {} == spec._definitions

        spec.definition('analysis', schema=schema)
        spec.add_path(
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

        spec_fixture.spec.definition('Pet', schema=PetSchema)
        spec_fixture.spec.definition('CustomPetA', schema=CustomPetASchema)
        spec_fixture.spec.definition('CustomPetB', schema=CustomPetBSchema)

        props_0 = spec_fixture.spec._definitions['Pet']['properties']
        props_a = spec_fixture.spec._definitions['CustomPetA']['properties']
        props_b = spec_fixture.spec._definitions['CustomPetB']['properties']

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
        spec_fixture.spec.add_path(
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
        get = spec_fixture.spec._paths['/pet']['get']
        assert get['responses'][200]['schema'] == spec_fixture.openapi.schema2jsonschema(PetSchema)
        assert get['responses'][200]['description'] == 'successful operation'

    @pytest.mark.parametrize('pet_schema', (PetSchema, PetSchema(), 'tests.schemas.PetSchema'))
    @pytest.mark.parametrize('spec_fixture', ('3.0.0', ), indirect=True)
    def test_schema_v3(self, spec_fixture, pet_schema):
        spec_fixture.spec.add_path(
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
        get = spec_fixture.spec._paths['/pet']['get']
        resolved_schema = get['responses'][200]['content']['application/json']['schema']
        assert resolved_schema == spec_fixture.openapi.schema2jsonschema(PetSchema)
        assert get['responses'][200]['description'] == 'successful operation'

    @pytest.mark.parametrize('spec_fixture', ('2.0', ), indirect=True)
    def test_schema_expand_parameters_v2(self, spec_fixture):
        spec_fixture.spec.add_path(
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
        p = spec_fixture.spec._paths['/pet']
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
        spec_fixture.spec.add_path(
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
        p = spec_fixture.spec._paths['/pet']
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
        post_schema = spec_fixture.openapi.resolve_schema_dict(PetSchema)
        assert post['requestBody']['content']['application/json']['schema'] == post_schema
        assert post['requestBody']['description'] == 'a pet schema'
        assert post['requestBody']['required']

    @pytest.mark.parametrize('spec_fixture', ('2.0', ), indirect=True)
    def test_schema_uses_ref_if_available_v2(self, spec_fixture):
        spec_fixture.spec.definition('Pet', schema=PetSchema)
        spec_fixture.spec.add_path(
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
        get = spec_fixture.spec._paths['/pet']['get']
        assert get['responses'][200]['schema']['$ref'] == self.ref_path(spec_fixture.spec) + 'Pet'

    @pytest.mark.parametrize('spec_fixture', ('3.0.0', ), indirect=True)
    def test_schema_uses_ref_if_available_v3(self, spec_fixture):
        spec_fixture.spec.definition('Pet', schema=PetSchema)
        spec_fixture.spec.add_path(
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
        get = spec_fixture.spec._paths['/pet']['get']
        assert get['responses'][200]['content']['application/json']['schema']['$ref'] == self.ref_path(
            spec_fixture.spec,
        ) + 'Pet'

    @pytest.mark.parametrize('spec_fixture', ('2.0', ), indirect=True)
    def test_schema_uses_ref_in_parameters_and_request_body_if_available_v2(self, spec_fixture):
        spec_fixture.spec.definition('Pet', schema=PetSchema)
        spec_fixture.spec.add_path(
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
        p = spec_fixture.spec._paths['/pet']
        assert 'schema' not in p['get']['parameters'][0]
        post = p['post']
        assert len(post['parameters']) == 1
        assert post['parameters'][0]['schema']['$ref'] == self.ref_path(spec_fixture.spec) + 'Pet'

    @pytest.mark.parametrize('spec_fixture', ('3.0.0', ), indirect=True)
    def test_schema_uses_ref_in_parameters_and_request_body_if_available_v3(self, spec_fixture):
        spec_fixture.spec.definition('Pet', schema=PetSchema)
        spec_fixture.spec.add_path(
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
        p = spec_fixture.spec._paths['/pet']
        assert 'schema' in p['get']['parameters'][0]
        post = p['post']
        schema_ref = post['requestBody']['content']['application/json']['schema']
        assert schema_ref == {'$ref': self.ref_path(spec_fixture.spec) + 'Pet'}

    @pytest.mark.parametrize('spec_fixture', ('2.0', ), indirect=True)
    def test_schema_array_uses_ref_if_available_v2(self, spec_fixture):
        spec_fixture.spec.definition('Pet', schema=PetSchema)
        spec_fixture.spec.add_path(
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
        get = spec_fixture.spec._paths['/pet']['get']
        len(get['parameters']) == 1
        resolved_schema = {
            'type': 'array',
            'items': {'$ref': self.ref_path(spec_fixture.spec) + 'Pet'},
        }
        assert get['parameters'][0]['schema'] == resolved_schema
        assert get['responses'][200]['schema'] == resolved_schema

    @pytest.mark.parametrize('spec_fixture', ('3.0.0', ), indirect=True)
    def test_schema_array_uses_ref_if_available_v3(self, spec_fixture):
        spec_fixture.spec.definition('Pet', schema=PetSchema)
        spec_fixture.spec.add_path(
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
        p = spec_fixture.spec._paths['/pet']
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
        spec_fixture.spec.definition('Pet', schema=PetSchema)
        spec_fixture.spec.add_path(
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
        get = spec_fixture.spec._paths['/parents']['get']
        assert get['responses'][200]['schema'] == {
            'type': 'object',
            'properties': {
                'mother': {'$ref': self.ref_path(spec_fixture.spec) + 'Pet'},
                'father': {'$ref': self.ref_path(spec_fixture.spec) + 'Pet'},
            },
        }

    @pytest.mark.parametrize('spec_fixture', ('3.0.0', ), indirect=True)
    def test_schema_partially_v3(self, spec_fixture):
        spec_fixture.spec.definition('Pet', schema=PetSchema)
        spec_fixture.spec.add_path(
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
        get = spec_fixture.spec._paths['/parents']['get']
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
        spec.definition('Analysis', schema=AnalysisSchema)
        spec.definition('Sample', schema=SampleSchema)
        spec.definition('Run', schema=RunSchema)
        ref = spec._definitions['Analysis']['properties']['sample']['$ref']
        assert ref == ref_path(spec) + 'Sample'

# Regression tests for issue #55
class TestSelfReference:

    def test_self_referencing_field_single(self, spec):
        spec.definition('SelfReference', schema=SelfReferencingSchema)
        ref = spec._definitions['SelfReference']['properties']['single']['$ref']
        assert ref == ref_path(spec) + 'SelfReference'

    def test_self_referencing_field_many(self, spec):
        spec.definition('SelfReference', schema=SelfReferencingSchema)
        result = spec._definitions['SelfReference']['properties']['many']
        assert result == {
            'type': 'array',
            'items': {'$ref': ref_path(spec) + 'SelfReference'},
        }

    def test_self_referencing_with_ref(self, spec):
        version = 'v2' if spec.openapi_version.version[0] < 3 else 'v3'
        spec.definition('SelfReference', schema=SelfReferencingSchema)
        result = spec._definitions['SelfReference']['properties'][
            'single_with_ref_{}'.format(version)
        ]
        assert result == {'$ref': ref_path(spec) + 'Self'}
        result = spec._definitions['SelfReference']['properties'][
            'many_with_ref_{}'.format(version)
        ]
        assert result == {'type': 'array', 'items': {'$ref': ref_path(spec) + 'Selves'}}


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


class TestSchemaWithDefaultValues:
    def test_schema_with_default_values(self, spec):
        spec.definition('DefaultValuesSchema', schema=DefaultValuesSchema)
        props = spec._definitions['DefaultValuesSchema']['properties']
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

        spec.definition('SchemaWithDict', schema=SchemaWithDict)
        result = spec._definitions['SchemaWithDict']['properties']['dict_field']
        assert result == {'type': 'object', 'additionalProperties': {'type': 'string'}}

    def test_dict_with_empty_values_field(self, spec):

        class SchemaWithDict(Schema):
            dict_field = Dict()

        spec.definition('SchemaWithDict', schema=SchemaWithDict)
        result = spec._definitions['SchemaWithDict']['properties']['dict_field']
        assert result == {'type': 'object'}
