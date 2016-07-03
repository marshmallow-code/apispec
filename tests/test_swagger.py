# -*- coding: utf-8 -*-

import pytest
from pytest import mark

from marshmallow import fields, Schema, validate

from apispec.ext.marshmallow import swagger
from apispec import exceptions, utils, APISpec
from apispec.ext.marshmallow.swagger import field2parameter


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
        field = fields.Str(default='foo', missing='bar')
        res = swagger.field2property(field)
        assert res['default'] == 'foo'

    def test_field_with_default_load(self):
        field = fields.Str(default='foo', missing='bar')
        res = swagger.field2property(field, dump=False)
        assert res['default'] == 'bar'

    def test_fields_with_default_load(self):
        field_dict = {'field': fields.Str(default='foo', missing='bar')}
        res = swagger.fields2parameters(field_dict, default_in='query', dump=False)
        assert res[0]['default'] == 'bar'

    def test_fields_with_location(self):
        field_dict = {'field': fields.Str(location='querystring')}
        res = swagger.fields2parameters(field_dict, default_in='headers')
        assert res[0]['in'] == 'query'

    def test_fields2parameters_does_not_modify_metadata(self):
        field_dict = {'field': fields.Str(location='querystring')}
        res = swagger.fields2parameters(field_dict, default_in='headers')
        assert res[0]['in'] == 'query'

        res = swagger.fields2parameters(field_dict, default_in='headers')
        assert res[0]['in'] == 'query'

    def test_fields_with_dump_only(self):
        field_dict = {'field': fields.Str(dump_only=True)}
        res = swagger.fields2parameters(field_dict, default_in='query', dump=False)
        assert len(res) == 0

    def test_field_with_choices(self):
        field = fields.Str(validate=validate.OneOf(['freddie', 'brian', 'john']))
        res = swagger.field2property(field)
        assert set(res['enum']) == {'freddie', 'brian', 'john'}

    def test_only_allows_valid_properties_in_metadata(self):
        field = fields.Str(
            default='foo',
            description='foo',
            enum=['red', 'blue'],
            allOf=['bar'],
            not_valid='lol'
        )
        res = swagger.field2property(field)
        assert 'default' in res
        assert res['default'] == field.default
        assert 'description' in res
        assert 'enum' in res
        assert 'allOf' in res
        assert 'not_valid' not in res

    def test_field_with_choices_multiple(self):
        field = fields.Str(validate=[
            validate.OneOf(['freddie', 'brian', 'john']),
            validate.OneOf(['brian', 'john', 'roger'])
        ])
        res = swagger.field2property(field)
        assert set(res['enum']) == {'brian', 'john'}

    def test_field_with_additional_metadata(self):
        field = fields.Str(minLength=6, maxLength=100)
        res = swagger.field2property(field)
        assert res['maxLength'] == 100
        assert res['minLength'] == 6


class TestMarshmallowSchemaToModelDefinition:

    def test_invalid_schema(self):
        with pytest.raises(ValueError):
            swagger.schema2jsonschema(None)

    def test_schema2jsonschema_with_explicit_fields(self):
        class UserSchema(Schema):
            _id = fields.Int()
            email = fields.Email(description='email address of the user')
            name = fields.Str()

            class Meta:
                title = 'User'

        res = swagger.schema2jsonschema(UserSchema)
        assert res['title'] == 'User'
        assert res['type'] == 'object'
        props = res['properties']
        assert props['_id']['type'] == 'integer'
        assert props['email']['type'] == 'string'
        assert props['email']['format'] == 'email'
        assert props['email']['description'] == 'email address of the user'

    def test_schema2jsonschema_override_name(self):
        class ExampleSchema(Schema):
            _id = fields.Int(load_from='id', dump_to='id')
            _as = fields.Int(load_from='as', dump_to='other')
            _global = fields.Int(load_from='global', dump_to='global')

            class Meta:
                exclude = ('_global', )

        res = swagger.schema2jsonschema(ExampleSchema)
        assert res['type'] == 'object'
        props = res['properties']
        # `_id` renamed to `id`
        assert '_id' not in props and props['id']['type'] == 'integer'
        # `load_from` and `dump_to` do not match for `_as`
        assert 'as' not in props
        # `_global` excluded correctly
        assert '_global' not in props and 'global' not in props

    def test_required_fields(self):
        class BandSchema(Schema):
            drummer = fields.Str(required=True)
            bassist = fields.Str()
        res = swagger.schema2jsonschema(BandSchema)
        assert res['required'] == ['drummer']

    def test_partial(self):
        class BandSchema(Schema):
            drummer = fields.Str(required=True)
            bassist = fields.Str(required=True)

        res = swagger.schema2jsonschema(BandSchema(partial=True))
        assert 'required' not in res

        res = swagger.schema2jsonschema(BandSchema(partial=('drummer', )))
        assert res['required'] == ['bassist']

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
        assert res['type'] == 'object'
        props = res['properties']
        assert '_id' in props
        assert 'email' not in props
        warning = recwarn.pop()
        expected_msg = 'Only explicitly-declared fields will be included in the Schema Object.'
        assert expected_msg in str(warning.message)
        assert issubclass(warning.category, UserWarning)

    def test_observed_field_name_for_required_field(self):
        fields_dict = {
            "user_id": fields.Int(load_from="id", dump_to="id", required=True)
        }

        res = swagger.fields2jsonschema(fields_dict)
        assert res["required"] == ["id"]

    def test_schema_instance_inspection(self):
        class UserSchema(Schema):
            _id = fields.Int()

        res = swagger.schema2jsonschema(UserSchema())
        assert res['type'] == 'object'
        props = res['properties']
        assert '_id' in props

    def test_schema_instance_inspection_with_many(self):
        class UserSchema(Schema):
            _id = fields.Int()

        res = swagger.schema2jsonschema(UserSchema(many=True))
        assert res['type'] == 'array'
        assert 'items' in res
        props = res['items']['properties']
        assert '_id' in props

    def test_raises_error_if_no_declared_fields(self):
        class NotASchema(object):
            pass

        with pytest.raises(ValueError) as excinfo:
            swagger.schema2jsonschema(NotASchema)

        assert excinfo.value.args[0] == ("{0!r} doesn't have either `fields` "
                                         "or `_declared_fields`".format(NotASchema))


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

    def test_invalid_schema(self):
        with pytest.raises(ValueError):
            swagger.schema2parameters(None)

    def test_schema_body(self):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email()

        res = swagger.schema2parameters(UserSchema, default_in='body')
        assert len(res) == 1
        param = res[0]
        assert param['in'] == 'body'
        assert param['schema'] == swagger.schema2jsonschema(UserSchema)

    def test_schema_body_with_dump_only(self):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email(dump_only=True)

        res_dump = swagger.schema2parameters(UserSchema, default_in='body', dump=True)
        assert len(res_dump) == 1
        param = res_dump[0]
        assert param['in'] == 'body'
        assert param['schema'] == swagger.schema2jsonschema(UserSchema, dump=True)
        assert set(param['schema']['properties'].keys()) == {'name', 'email'}
        assert param['schema']['properties']['email']['readOnly'] is True

        res_nodump = swagger.schema2parameters(UserSchema, default_in='body', dump=False)
        assert len(res_nodump) == 1
        param = res_nodump[0]
        assert param['in'] == 'body'
        assert param['schema'] == swagger.schema2jsonschema(UserSchema, dump=False)
        assert set(param['schema']['properties'].keys()) == {'name'}

    def test_schema_body_many(self):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email()

        res = swagger.schema2parameters(UserSchema(many=True), default_in='body')
        assert len(res) == 1
        param = res[0]
        assert param['in'] == 'body'
        assert param['schema']['type'] == 'array'
        assert param['schema']['items']['type'] == 'object'
        assert param['schema']['items'] == swagger.schema2jsonschema(UserSchema)

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

    def test_schema_query_instance(self):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email()

        res = swagger.schema2parameters(UserSchema(), default_in='query')
        assert len(res) == 2
        res.sort(key=lambda param: param['name'])
        assert res[0]['name'] == 'email'
        assert res[0]['in'] == 'query'
        assert res[1]['name'] == 'name'
        assert res[1]['in'] == 'query'

    def test_schema_query_instance_many_should_raise_exception(self):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email()

        with pytest.raises(AssertionError):
            swagger.schema2parameters(UserSchema(many=True), default_in='query')

    def test_fields_default_in_body(self):
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

    def test_raises_error_if_not_a_schema(self):
        class NotASchema(object):
            pass

        with pytest.raises(ValueError) as excinfo:
            swagger.schema2jsonschema(NotASchema)

        assert excinfo.value.args[0] == ("{0!r} doesn't have either `fields` "
                                         "or `_declared_fields`".format(NotASchema))


class CategorySchema(Schema):
    id = fields.Int()
    name = fields.Str(required=True)
    breed = fields.Str(dump_only=True)

class PageSchema(Schema):
    offset = fields.Int()
    limit = fields.Int()

class PetSchema(Schema):
    category = fields.Nested(CategorySchema, many=True, ref='#/definitions/Category')
    name = fields.Str()


class TestNesting:

    @pytest.fixture()
    def spec(self):
        return APISpec(
            title='Pets',
            version='0.1',
            plugins=['apispec.ext.marshmallow'],
        )

    def test_field2property_nested_spec_metadatas(self, spec):
        spec.definition('Category', schema=CategorySchema)
        category = fields.Nested(CategorySchema, description="A category")
        result = swagger.field2property(category, spec=spec)
        assert result == {'$ref': '#/definitions/Category', 'description': 'A category'}

    def test_field2property_nested_spec(self, spec):
        spec.definition('Category', schema=CategorySchema)
        category = fields.Nested(CategorySchema)
        assert swagger.field2property(category, spec=spec) == {'$ref': '#/definitions/Category'}

    def test_field2property_nested_many_spec(self, spec):
        spec.definition('Category', schema=CategorySchema)
        category = fields.Nested(CategorySchema, many=True)
        ret = swagger.field2property(category, spec=spec)
        assert ret['type'] == 'array'
        assert ret['items'] == {'$ref': '#/definitions/Category'}

    def test_field2property_nested_ref(self, spec):
        category = fields.Nested(CategorySchema)
        assert swagger.field2property(category) == swagger.schema2jsonschema(CategorySchema)

        cat_with_ref = fields.Nested(CategorySchema, ref='Category')
        assert swagger.field2property(cat_with_ref) == {'$ref': 'Category'}

    def test_field2property_nested_ref_with_meta(self, spec):
        category = fields.Nested(CategorySchema)
        assert swagger.field2property(category) == swagger.schema2jsonschema(CategorySchema)

        cat_with_ref = fields.Nested(CategorySchema, ref='Category', description="A category")
        result = swagger.field2property(cat_with_ref)
        assert result == {'$ref': 'Category', 'description': "A category"}

    def test_field2property_nested_many(self, spec):
        categories = fields.Nested(CategorySchema, many=True)
        res = swagger.field2property(categories)
        assert res['type'] == 'array'
        assert res['items'] == swagger.schema2jsonschema(CategorySchema)

        cats_with_ref = fields.Nested(CategorySchema, many=True, ref='Category')
        res = swagger.field2property(cats_with_ref)
        assert res['type'] == 'array'
        assert res['items'] == {'$ref': 'Category'}

    def test_field2property_nested_self_without_name_raises_error(self, spec):
        self_nesting = fields.Nested('self')
        with pytest.raises(ValueError):
            swagger.field2property(self_nesting)

    def test_field2property_nested_self(self, spec):
        self_nesting = fields.Nested('self')
        res = swagger.field2property(self_nesting, name='Foo')
        assert res == {'$ref': '#/definitions/Foo'}

    def test_field2property_nested_self_many(self, spec):
        self_nesting = fields.Nested('self', many=True)
        res = swagger.field2property(self_nesting, name='Foo')
        assert res == {'type': 'array', 'items': {'$ref': '#/definitions/Foo'}}

    def test_field2property_nested_self_ref_with_meta(self, spec):
        self_nesting = fields.Nested('self', ref='#/definitions/Bar')
        res = swagger.field2property(self_nesting)
        assert res == {'$ref': '#/definitions/Bar'}

        self_nesting2 = fields.Nested('self', ref='#/definitions/Bar')
        # name is passed
        res = swagger.field2property(self_nesting2, name='Foo')
        assert res == {'$ref': '#/definitions/Bar'}

    def test_field2property_nested_dump_only(self, spec):
        category = fields.Nested(CategorySchema)
        res = swagger.field2property(category, name='Foo', dump=False)
        props = res['properties']
        assert 'breed' not in props

    def test_field2property_nested_dump_only_with_spec(self, spec):
        category = fields.Nested(CategorySchema)
        res = swagger.field2property(category, spec=spec, name='Foo', dump=False)
        props = res['properties']
        assert 'breed' not in props

    def test_schema2jsonschema_with_nested_fields(self):
        res = swagger.schema2jsonschema(PetSchema, use_refs=False)
        props = res['properties']
        assert props['category']['items'] == swagger.schema2jsonschema(CategorySchema)

    def test_schema2jsonschema_with_nested_fields_with_adhoc_changes(self, spec):
        category_schema = CategorySchema(many=True)
        category_schema.fields['id'].required = True

        class PetSchema(Schema):
            category = fields.Nested(category_schema, many=True, ref='#/definitions/Category')
            name = fields.Str()

        res = swagger.schema2jsonschema(PetSchema(), use_refs=False)
        props = res['properties']
        assert props['category'] == swagger.schema2jsonschema(category_schema)
        assert set(props['category']['items']['required']) == {'id', 'name'}

        props['category']['items']['required'] = ['name']
        assert props['category']['items'] == swagger.schema2jsonschema(CategorySchema)

    def test_schema2jsonschema_with_nested_excluded_fields(self, spec):
        category_schema = CategorySchema(exclude=('breed', ))

        class PetSchema(Schema):
            category = fields.Nested(category_schema)

        res = swagger.schema2jsonschema(PetSchema(), use_refs=False)
        category_props = res['properties']['category']['properties']
        assert 'breed' not in category_props


def test_swagger_tools_validate():
    spec = APISpec(
        title='Pets',
        version='0.1',
        plugins=['apispec.ext.marshmallow'],
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
                        field=fields.List(
                            fields.Str(),
                            validate=validate.OneOf(['freddie', 'roger']),
                            location='querystring',
                        ),
                        name='body',
                        use_refs=False,
                    ),
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
    try:
        utils.validate_swagger(spec)
    except exceptions.SwaggerError as error:
        pytest.fail(str(error))

class ValidationSchema(Schema):
    id = fields.Int(dump_only=True)
    range = fields.Int(validate=validate.Range(min=1, max=10))
    multiple_ranges = fields.Int(validate=[
        validate.Range(min=1),
        validate.Range(min=3),
        validate.Range(max=10),
        validate.Range(max=7)
    ])
    list_length = fields.List(fields.Str, validate=validate.Length(min=1, max=10))
    string_length = fields.Str(validate=validate.Length(min=1, max=10))
    multiple_lengths = fields.Str(validate=[
        validate.Length(min=1),
        validate.Length(min=3),
        validate.Length(max=10),
        validate.Length(max=7)
    ])
    equal_length = fields.Str(validate=[
        validate.Length(equal=5),
        validate.Length(min=1, max=10)
    ])

class TestFieldValidation:

    @pytest.fixture()
    def spec(self):
        return APISpec(
            title='Validation',
            version='0.1',
            plugins=['apispec.ext.marshmallow'],
        )

    def test_range(self, spec):
        spec.definition('Validation', schema=ValidationSchema)
        result = spec._definitions['Validation']['properties']['range']

        assert 'minimum' in result
        assert result['minimum'] == 1
        assert 'maximum' in result
        assert result['maximum'] == 10

    def test_multiple_ranges(self, spec):
        spec.definition('Validation', schema=ValidationSchema)
        result = spec._definitions['Validation']['properties']['multiple_ranges']

        assert 'minimum' in result
        assert result['minimum'] == 3
        assert 'maximum' in result
        assert result['maximum'] == 7

    def test_list_length(self, spec):
        spec.definition('Validation', schema=ValidationSchema)
        result = spec._definitions['Validation']['properties']['list_length']

        assert 'minLength' in result
        assert result['minLength'] == 1
        assert 'maxLength' in result
        assert result['maxLength'] == 10

    def test_string_length(self, spec):
        spec.definition('Validation', schema=ValidationSchema)
        result = spec._definitions['Validation']['properties']['string_length']

        assert 'minLength' in result
        assert result['minLength'] == 1
        assert 'maxLength' in result
        assert result['maxLength'] == 10

    def test_multiple_lengths(self, spec):
        spec.definition('Validation', schema=ValidationSchema)
        result = spec._definitions['Validation']['properties']['multiple_lengths']

        assert 'minLength' in result
        assert result['minLength'] == 3
        assert 'maxLength' in result
        assert result['maxLength'] == 7

    def test_equal_length(self, spec):
        spec.definition('Validation', schema=ValidationSchema)
        result = spec._definitions['Validation']['properties']['equal_length']

        assert 'minLength' in result
        assert result['minLength'] == 5
        assert 'maxLength' in result
        assert result['maxLength'] == 5
