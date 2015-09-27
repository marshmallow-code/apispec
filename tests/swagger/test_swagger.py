# -*- coding: utf-8 -*-

import pytest
from pytest import mark
try:  # older versions of webargs
    from webargs import Arg
except ImportError:
    HAS_WEBARGS_ARG = False
else:
    HAS_WEBARGS_ARG = True

from marshmallow import fields, Schema
from marshmallow.compat import binary_type

from smore import swagger
from smore import exceptions
from smore.apispec import utils
from smore.apispec import APISpec
from smore.swagger import arg2parameter, arg2property, field2parameter

if HAS_WEBARGS_ARG:
    class TestArgToSwagger:

        @mark.parametrize(('pytype', 'jsontype'), [
            (int, 'integer'),
            (float, 'number'),
            (str, 'string'),
            (bool, 'boolean'),
            (list, 'array'),
            (tuple, 'array'),
            (set, 'array'),
        ])
        def test_type_translation(self, pytype, jsontype):
            arg = Arg(pytype, location='form')
            result = arg2parameter(arg)
            assert result['type'] == jsontype

        @mark.parametrize(('webargs_location', 'swagger_location'), [
            ('querystring', 'query'),
            ('json', 'body'),
            ('headers', 'header'),
            ('form', 'formData'),
            ('files', 'formData')
        ])
        def test_location_translation(self, webargs_location, swagger_location):
            arg = Arg(int, location=webargs_location)
            result = arg2parameter(arg)
            assert result['in'] == swagger_location

        def test_location_defaults_to_json_body(self):
            # No location specified
            arg = Arg(int)
            result = arg2parameter(arg)
            assert result['in'] == 'body'

        def test_required_translation(self):
            arg = Arg(int, required=True)
            arg.location = 'json'
            result = arg2parameter(arg)
            assert result['required'] is True
            arg2 = Arg(int, location='json')
            result2 = arg2parameter(arg2)
            assert result2['required'] is False

        def test_collection_translation_multiple(self):
            arg = Arg(int, multiple=True, location='querystring')
            result = arg2parameter(arg)
            assert result['type'] == 'array'
            assert result['collectionFormat'] == 'multi'

        def test_collection_translation_single(self):
            arg = Arg(int, location='querystring')
            result = arg2parameter(arg)
            assert 'collectionFormat' not in result

        def test_items_multiple_querystring(self):
            arg = Arg(int, multiple=True, location='querystring')
            result = arg2parameter(arg)
            assert result['items'] == {'type': 'integer', 'format': 'int32'}

        def test_arg_with_description(self):
            arg = Arg(int, location='form', description='a webargs arg')
            result = arg2parameter(arg)
            assert result['description'] == arg.metadata['description']

        def test_arg_with_format(self):
            arg = Arg(int, location='form', format='int32')
            result = arg2parameter(arg)
            assert result['format'] == 'int32'

        def test_arg_with_default(self):
            arg = Arg(int, location='form', default=42)
            result = arg2parameter(arg)
            assert result['default'] == 42

        def test_arg_name_is_body_if_location_is_json(self):
            arg = Arg(int, location='json')
            result = arg2parameter(arg)
            assert result['name'] == 'body'

        def test_arg_with_name(self):
            arg = Arg(int, location='form', name='foo')
            res = arg2parameter(arg)
            assert res['name'] == 'foo'

        def test_schema_if_json_body(self):
            arg = Arg(int, location='json')
            res = arg2parameter(arg)
            assert 'schema' in res

        def test_no_schema_if_form_body(self):
            arg = Arg(int, location='form')
            res = arg2parameter(arg)
            assert 'schema' not in res

        def test_arg2property_with_description(self):
            arg = Arg(int, location='json', description='status')
            res = arg2property(arg)
            assert res['type'] == 'integer'
            assert res['description'] == arg.metadata['description']

        @mark.parametrize(('pytype', 'expected_format'), [
            (int, 'int32'),
            (float, 'float'),
            (binary_type, 'byte'),
        ])
        def test_arg2property_formats(self, pytype, expected_format):
            arg = Arg(pytype, location='json')
            res = arg2property(arg)
            assert res['format'] == expected_format

        def test_arg_with_no_type_default_to_string(self):
            arg = Arg()
            res = arg2property(arg)
            assert res['type'] == 'string'

        def test_arg2property_with_additional_metadata(self):
            arg = Arg(minLength=6, maxLength=100)
            res = arg2property(arg)
            assert res['minLength'] == 6
            assert res['maxLength'] == 100

        def test_arg2swagger_puts_json_arguments_in_schema(self):
            arg = Arg(int, location='json', description='a count', format='int32')
            res = arg2parameter(arg, 'username')
            assert res['name'] == 'body'
            assert 'description' not in res
            schema_props = res['schema']['properties']

            # property is defined on schema
            assert schema_props['username']['type'] == 'integer'
            assert schema_props['username']['description'] == arg.metadata['description']
            assert schema_props['username']['format'] == 'int32'

    class TestWebargsSchemaToSwagger:

        def test_args2parameters(self):
            args = {
                'username': Arg(str, location='querystring', required=False,
                                description='The user name for login'),
            }
            result = swagger.args2parameters(args)
            username = result[0]
            assert username['name'] == 'username'
            assert username['in'] == 'query'
            assert username['type'] == 'string'
            assert username['required'] is False
            assert username['description'] == args['username'].metadata['description']

        def test_arg2parameters_with_dest(self):
            args = {
                'X-Neat-Header': Arg(str, location='headers', dest='neat_header')
            }
            result = swagger.args2parameters(args)
            header = result[0]
            assert header['name'] == 'X-Neat-Header'


class TestMarshmallowFieldToSwagger:

    @mark.parametrize(('FieldClass', 'jsontype'), [
        (fields.Integer, 'integer'),
        (fields.Number, 'number'),
        (fields.Float, 'number'),
        (fields.String, 'string'),
        (fields.Str, 'string'),
        (fields.Boolean, 'boolean'),
        (fields.Bool, 'boolean'),
        (fields.UUID, 'string'),
        (fields.DateTime, 'string'),
        (fields.Date, 'string'),
        (fields.Time, 'string'),
        (fields.Email, 'string'),
        (fields.URL, 'string'),
        # Assume base Field and Raw are strings
        (fields.Field, 'string'),
        (fields.Raw, 'string'),
    ])
    def test_field2property_type(self, FieldClass, jsontype):
        field = FieldClass()
        res = swagger.field2property(field)
        assert res['type'] == jsontype

    def test_formatted_field_translates_to_array(self):
        field = fields.List(fields.String)
        res = swagger.field2property(field)
        assert res['type'] == 'array'
        assert res['items'] == swagger.field2property(fields.String())

    @mark.parametrize(('FieldClass', 'expected_format'), [
        (fields.Integer, 'int32'),
        (fields.Float, 'float'),
        (fields.UUID, 'uuid'),
        (fields.DateTime, 'date-time'),
        (fields.Date, 'date'),
        (fields.Email, 'email'),
        (fields.URL, 'url'),
    ])
    def test_field2property_formats(self, FieldClass, expected_format):
        field = FieldClass()
        res = swagger.field2property(field)
        assert res['format'] == expected_format

    def test_field_with_description(self):
        field = fields.Str(description='a username')
        res = swagger.field2property(field)
        assert res['description'] == 'a username'

    def test_field_with_default(self):
        field = fields.Str(default='foo')
        res = swagger.field2property(field)
        assert res['default'] == 'foo'

    def test_field_with_additional_metadata(self):
        field = fields.Str(minLength=6, maxLength=100)
        res = swagger.field2property(field)
        assert res['maxLength'] == 100
        assert res['minLength'] == 6


class TestMarshmallowSchemaToModelDefinition:

    def test_schema2jsonschema_with_explicit_fields(self):
        class UserSchema(Schema):
            _id = fields.Int()
            email = fields.Email(description='email address of the user')
            name = fields.Str()

            class Meta:
                title = 'User'

        res = swagger.schema2jsonschema(UserSchema)
        assert res['title'] == 'User'
        props = res['properties']
        assert props['_id']['type'] == 'integer'
        assert props['email']['type'] == 'string'
        assert props['email']['format'] == 'email'
        assert props['email']['description'] == 'email address of the user'

    def test_required_fields(self):
        class BandSchema(Schema):
            drummer = fields.Str(required=True)
            bassist = fields.Str()
        res = swagger.schema2jsonschema(BandSchema)
        assert res['required'] == ['drummer']

    def test_no_required_fields(self):
        class BandSchema(Schema):
            drummer = fields.Str()
            bassist = fields.Str()
        res = swagger.schema2jsonschema(BandSchema)
        assert 'required' not in res

    def test_title_and_description_may_be_added(self):
        class UserSchema(Schema):
            class Meta:
                title = 'User'
                description = 'A registered user'

        res = swagger.schema2jsonschema(UserSchema)
        assert res['description'] == 'A registered user'
        assert res['title'] == 'User'

    def test_excluded_fields(self):
        class WhiteStripesSchema(Schema):
            class Meta:
                exclude = ('bassist', )
            guitarist = fields.Str()
            drummer = fields.Str()
            bassist = fields.Str()

        res = swagger.schema2jsonschema(WhiteStripesSchema)
        assert set(res['properties'].keys()) == set(['guitarist', 'drummer'])

    def test_only_explicitly_declared_fields_are_translated(self, recwarn):
        class UserSchema(Schema):
            _id = fields.Int()

            class Meta:
                title = 'User'
                fields = ('_id', 'email', )

        res = swagger.schema2jsonschema(UserSchema)
        props = res['properties']
        assert '_id' in props
        assert 'email' not in props
        warning = recwarn.pop()
        expected_msg = 'Only explicitly-declared fields will be included in the Schema Object.'
        assert expected_msg in str(warning.message)
        assert issubclass(warning.category, UserWarning)

class TestMarshmallowSchemaToParameters:

    def test_field_multiple(self):
        field = fields.List(fields.Str, location='querystring')
        res = swagger.field2parameter(field, name='field')
        assert res['in'] == 'query'
        assert res['type'] == 'array'
        assert res['items']['type'] == 'string'
        assert res['collectionFormat'] == 'multi'

    def test_field_required(self):
        field = fields.Str(required=True)
        res = swagger.field2parameter(field, name='field')
        assert res['required'] is True

    def test_schema_body(self):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email()
        res = swagger.schema2parameters(UserSchema, default_in='body')
        assert len(res) == 1
        param = res[0]
        assert param['in'] == 'body'
        assert param['schema'] == swagger.schema2jsonschema(UserSchema)

    def test_schema_query(self):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email()
        res = swagger.schema2parameters(UserSchema, default_in='query')
        assert len(res) == 2
        res.sort(key=lambda param: param['name'])
        assert res[0]['name'] == 'email'
        assert res[0]['in'] == 'query'
        assert res[1]['name'] == 'name'
        assert res[1]['in'] == 'query'

    def test_fields_body(self):
        field_dict = {
            'name': fields.Str(),
            'email': fields.Email(),
        }
        res = swagger.fields2parameters(field_dict)
        assert len(res) == 1
        assert set(res[0]['schema']['properties'].keys()) == {'name', 'email'}

    def test_fields_query(self):
        field_dict = {
            'name': fields.Str(),
            'email': fields.Email(),
        }
        res = swagger.fields2parameters(field_dict, default_in='query')
        assert len(res) == 2
        res.sort(key=lambda param: param['name'])
        assert res[0]['name'] == 'email'
        assert res[0]['in'] == 'query'
        assert res[1]['name'] == 'name'
        assert res[1]['in'] == 'query'

class CategorySchema(Schema):
    id = fields.Int()
    name = fields.Str(required=True)

class PageSchema(Schema):
    offset = fields.Int()
    limit = fields.Int()

class PetSchema(Schema):
    category = fields.Nested(CategorySchema, many=True, ref='#/definitions/Category')
    name = fields.Str()


class TestNesting:

    def test_field2property_nested_spec(self):
        spec.definition('Category', schema=CategorySchema)
        category = fields.Nested(CategorySchema)
        assert swagger.field2property(category, spec=spec) == {'$ref': '#/definitions/Category'}

    def test_field2property_nested_ref(self):
        category = fields.Nested(CategorySchema)
        assert swagger.field2property(category) == swagger.schema2jsonschema(CategorySchema)

        cat_with_ref = fields.Nested(CategorySchema, ref='Category')
        assert swagger.field2property(cat_with_ref) == {'$ref': 'Category'}

    def test_field2property_nested_many(self):
        categories = fields.Nested(CategorySchema, many=True)
        res = swagger.field2property(categories)
        assert res['type'] == 'array'
        assert res['items'] == swagger.schema2jsonschema(CategorySchema)

        cats_with_ref = fields.Nested(CategorySchema, many=True, ref='Category')
        res = swagger.field2property(cats_with_ref)
        assert res['type'] == 'array'
        assert res['items'] == {'$ref': 'Category'}

    def test_schema2jsonschema_with_nested_fields(self):
        res = swagger.schema2jsonschema(PetSchema, use_refs=False)
        props = res['properties']
        assert props['category']['items'] == swagger.schema2jsonschema(CategorySchema)


spec = APISpec(
    title='Pets',
    version='0.1',
    plugins=['smore.ext.marshmallow'],
)

spec.definition('Category', schema=CategorySchema)
spec.definition('Pet', schema=PetSchema)

spec.add_path(
    view=None,
    path='/category/{category_id}',
    operations={
        'get': {
            'parameters': [
                {'name': 'q', 'in': 'query', 'type': 'string'},
                {'name': 'category_id', 'in': 'path', 'required': True, 'type': 'string'},
                field2parameter(
                    field=fields.List(fields.Str(), location='querystring'),
                    name='body', use_refs=False),
            ] + swagger.schema2parameters(PageSchema, default_in='query'),
            'responses': {
                200: {
                    'schema': PetSchema,
                    'description': 'A pet',
                },
            },
        },
        'post': {
            'parameters': (
                [{'name': 'category_id', 'in': 'path', 'required': True, 'type': 'string'}] +
                swagger.schema2parameters(CategorySchema, spec=spec, default_in='body')
            ),
            'responses': {
                201: {
                    'schema': PetSchema,
                    'description': 'A pet',
                },
            },
        }
    },
)

def test_swagger_tools_validate():
    try:
        utils.validate_swagger(spec)
    except exceptions.SwaggerError as error:
        pytest.fail(str(error))
