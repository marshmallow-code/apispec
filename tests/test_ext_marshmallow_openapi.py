from datetime import datetime

import pytest

from marshmallow import EXCLUDE, fields, INCLUDE, RAISE, Schema, validate

from apispec.ext.marshmallow import MarshmallowPlugin
from apispec import exceptions, APISpec

from .schemas import CustomList, CustomStringField
from .utils import get_schemas, build_ref, validate_spec


class TestMarshmallowFieldToOpenAPI:
    def test_fields_with_load_default_load(self, openapi):
        class MySchema(Schema):
            field = fields.Str(dump_default="foo", load_default="bar")

        res = openapi.schema2parameters(MySchema, location="query")
        if openapi.openapi_version.major < 3:
            assert res[0]["default"] == "bar"
        else:
            assert res[0]["schema"]["default"] == "bar"

    # json/body is invalid for OpenAPI 3
    @pytest.mark.parametrize("openapi", ("2.0",), indirect=True)
    def test_fields_default_location_mapping_if_schema_many(self, openapi):
        class ExampleSchema(Schema):
            id = fields.Int()

        schema = ExampleSchema(many=True)
        res = openapi.schema2parameters(schema=schema, location="json")
        assert res[0]["in"] == "body"

    def test_fields_with_dump_only(self, openapi):
        class UserSchema(Schema):
            name = fields.Str(dump_only=True)

        res = openapi.schema2parameters(schema=UserSchema(), location="query")
        assert len(res) == 0

        class UserSchema(Schema):
            name = fields.Str()

            class Meta:
                dump_only = ("name",)

        res = openapi.schema2parameters(schema=UserSchema(), location="query")
        assert len(res) == 0


class TestMarshmallowSchemaToModelDefinition:
    def test_schema2jsonschema_with_explicit_fields(self, openapi):
        class UserSchema(Schema):
            _id = fields.Int()
            email = fields.Email(metadata={"description": "email address of the user"})
            name = fields.Str()

            class Meta:
                title = "User"

        res = openapi.schema2jsonschema(UserSchema)
        assert res["title"] == "User"
        assert res["type"] == "object"
        props = res["properties"]
        assert props["_id"]["type"] == "integer"
        assert props["email"]["type"] == "string"
        assert props["email"]["format"] == "email"
        assert props["email"]["description"] == "email address of the user"

    def test_schema2jsonschema_override_name(self, openapi):
        class ExampleSchema(Schema):
            _id = fields.Int(data_key="id")
            _global = fields.Int(data_key="global")

            class Meta:
                exclude = ("_global",)

        res = openapi.schema2jsonschema(ExampleSchema)
        assert res["type"] == "object"
        props = res["properties"]
        # `_id` renamed to `id`
        assert "_id" not in props and props["id"]["type"] == "integer"
        # `_global` excluded correctly
        assert "_global" not in props and "global" not in props

    def test_required_fields(self, openapi):
        class BandSchema(Schema):
            drummer = fields.Str(required=True)
            bassist = fields.Str()

        res = openapi.schema2jsonschema(BandSchema)
        assert res["required"] == ["drummer"]

    def test_partial(self, openapi):
        class BandSchema(Schema):
            drummer = fields.Str(required=True)
            bassist = fields.Str(required=True)

        res = openapi.schema2jsonschema(BandSchema(partial=True))
        assert "required" not in res

        res = openapi.schema2jsonschema(BandSchema(partial=("drummer",)))
        assert res["required"] == ["bassist"]

    def test_no_required_fields(self, openapi):
        class BandSchema(Schema):
            drummer = fields.Str()
            bassist = fields.Str()

        res = openapi.schema2jsonschema(BandSchema)
        assert "required" not in res

    def test_title_and_description_may_be_added(self, openapi):
        class UserSchema(Schema):
            class Meta:
                title = "User"
                description = "A registered user"

        res = openapi.schema2jsonschema(UserSchema)
        assert res["description"] == "A registered user"
        assert res["title"] == "User"

    def test_excluded_fields(self, openapi):
        class WhiteStripesSchema(Schema):
            class Meta:
                exclude = ("bassist",)

            guitarist = fields.Str()
            drummer = fields.Str()
            bassist = fields.Str()

        res = openapi.schema2jsonschema(WhiteStripesSchema)
        assert set(res["properties"].keys()) == {"guitarist", "drummer"}

    def test_unknown_values_disallow(self, openapi):
        class UnknownRaiseSchema(Schema):
            class Meta:
                unknown = RAISE

            first = fields.Str()

        res = openapi.schema2jsonschema(UnknownRaiseSchema)
        assert res["additionalProperties"] is False

    def test_unknown_values_allow(self, openapi):
        class UnknownIncludeSchema(Schema):
            class Meta:
                unknown = INCLUDE

            first = fields.Str()

        res = openapi.schema2jsonschema(UnknownIncludeSchema)
        assert res["additionalProperties"] is True

    def test_unknown_values_ignore(self, openapi):
        class UnknownExcludeSchema(Schema):
            class Meta:
                unknown = EXCLUDE

            first = fields.Str()

        res = openapi.schema2jsonschema(UnknownExcludeSchema)
        assert "additionalProperties" not in res

    def test_only_explicitly_declared_fields_are_translated(self, openapi):
        class UserSchema(Schema):
            _id = fields.Int()

            class Meta:
                title = "User"
                fields = ("_id", "email")

        with pytest.warns(
            UserWarning,
            match="Only explicitly-declared fields will be included in the Schema Object.",
        ):
            res = openapi.schema2jsonschema(UserSchema)
            assert res["type"] == "object"
            props = res["properties"]
            assert "_id" in props
            assert "email" not in props

    def test_observed_field_name_for_required_field(self, openapi):
        fields_dict = {"user_id": fields.Int(data_key="id", required=True)}
        res = openapi.fields2jsonschema(fields_dict)
        assert res["required"] == ["id"]

    @pytest.mark.parametrize("many", (True, False))
    def test_schema_instance_inspection(self, openapi, many):
        class UserSchema(Schema):
            _id = fields.Int()

        res = openapi.schema2jsonschema(UserSchema(many=many))
        assert res["type"] == "object"
        props = res["properties"]
        assert "_id" in props

    def test_raises_error_if_no_declared_fields(self, openapi):
        class NotASchema:
            pass

        expected_error = (
            f"{NotASchema!r} is neither a Schema class nor a Schema instance."
        )
        with pytest.raises(ValueError, match=expected_error):
            openapi.schema2jsonschema(NotASchema)


class TestMarshmallowSchemaToParameters:
    def test_custom_properties_for_custom_fields(self, spec_fixture):
        class DelimitedList(fields.List):
            """Delimited list field"""

        def delimited_list2param(self, field, **kwargs):
            ret: dict = {}
            if isinstance(field, DelimitedList):
                if self.openapi_version.major < 3:
                    ret["collectionFormat"] = "csv"
                else:
                    ret["explode"] = False
                    ret["style"] = "form"
            return ret

        spec_fixture.marshmallow_plugin.converter.add_parameter_attribute_function(
            delimited_list2param
        )

        class MySchema(Schema):
            delimited_list = DelimitedList(fields.Int)

        param = spec_fixture.marshmallow_plugin.converter.schema2parameters(
            MySchema(), location="query"
        )[0]

        if spec_fixture.openapi.openapi_version.major < 3:
            assert param["collectionFormat"] == "csv"
        else:
            assert param["explode"] is False
            assert param["style"] == "form"

    def test_field_required(self, openapi):
        field = fields.Str(required=True)
        res = openapi._field2parameter(field, name="field", location="query")
        assert res["required"] is True

    def test_schema_partial(self, openapi):
        class UserSchema(Schema):
            field = fields.Str(required=True)

        res_nodump = openapi.schema2parameters(
            UserSchema(partial=True), location="query"
        )

        param = res_nodump[0]
        assert param["required"] is False

    def test_schema_partial_list(self, openapi):
        class UserSchema(Schema):
            field = fields.Str(required=True)
            partial_field = fields.Str(required=True)

        res_nodump = openapi.schema2parameters(
            UserSchema(partial=("partial_field",)), location="query"
        )

        param = next(p for p in res_nodump if p["name"] == "field")
        assert param["required"] is True
        param = next(p for p in res_nodump if p["name"] == "partial_field")
        assert param["required"] is False

    @pytest.mark.parametrize("ListClass", [fields.List, CustomList])
    def test_field_list(self, ListClass, openapi):
        field = ListClass(fields.Str)
        res = openapi._field2parameter(field, name="field", location="query")
        assert res["in"] == "query"
        if openapi.openapi_version.major < 3:
            assert res["type"] == "array"
            assert res["items"]["type"] == "string"
            assert res["collectionFormat"] == "multi"
        else:
            assert res["schema"]["type"] == "array"
            assert res["schema"]["items"]["type"] == "string"
            assert res["style"] == "form"
            assert res["explode"] is True

    # json/body is invalid for OpenAPI 3
    @pytest.mark.parametrize("openapi", ("2.0",), indirect=True)
    def test_schema_body(self, openapi):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email()

        res = openapi.schema2parameters(UserSchema, location="body")
        assert len(res) == 1
        param = res[0]
        assert param["in"] == "body"
        assert param["schema"] == {"$ref": "#/definitions/User"}

    # json/body is invalid for OpenAPI 3
    @pytest.mark.parametrize("openapi", ("2.0",), indirect=True)
    def test_schema_body_with_dump_only(self, openapi):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email(dump_only=True)

        res_nodump = openapi.schema2parameters(UserSchema, location="body")
        assert len(res_nodump) == 1
        param = res_nodump[0]
        assert param["in"] == "body"
        assert param["schema"] == build_ref(openapi.spec, "schema", "User")

    # json/body is invalid for OpenAPI 3
    @pytest.mark.parametrize("openapi", ("2.0",), indirect=True)
    def test_schema_body_many(self, openapi):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email()

        res = openapi.schema2parameters(UserSchema(many=True), location="body")
        assert len(res) == 1
        param = res[0]
        assert param["in"] == "body"
        assert param["schema"]["type"] == "array"
        assert param["schema"]["items"] == {"$ref": "#/definitions/User"}

    def test_schema_query(self, openapi):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email()

        res = openapi.schema2parameters(UserSchema, location="query")
        assert len(res) == 2
        res.sort(key=lambda param: param["name"])
        assert res[0]["name"] == "email"
        assert res[0]["in"] == "query"
        assert res[1]["name"] == "name"
        assert res[1]["in"] == "query"

    def test_schema_query_instance(self, openapi):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email()

        res = openapi.schema2parameters(UserSchema(), location="query")
        assert len(res) == 2
        res.sort(key=lambda param: param["name"])
        assert res[0]["name"] == "email"
        assert res[0]["in"] == "query"
        assert res[1]["name"] == "name"
        assert res[1]["in"] == "query"

    def test_schema_query_instance_many_should_raise_exception(self, openapi):
        class UserSchema(Schema):
            name = fields.Str()
            email = fields.Email()

        with pytest.raises(AssertionError):
            openapi.schema2parameters(UserSchema(many=True), location="query")

    def test_fields_query(self, openapi):
        class MySchema(Schema):
            name = fields.Str()
            email = fields.Email()

        res = openapi.schema2parameters(MySchema, location="query")
        assert len(res) == 2
        res.sort(key=lambda param: param["name"])
        assert res[0]["name"] == "email"
        assert res[0]["in"] == "query"
        assert res[1]["name"] == "name"
        assert res[1]["in"] == "query"

    def test_raises_error_if_not_a_schema(self, openapi):
        class NotASchema:
            pass

        expected_error = (
            f"{NotASchema!r} is neither a Schema class nor a Schema instance."
        )
        with pytest.raises(ValueError, match=expected_error):
            openapi.schema2jsonschema(NotASchema)


class CategorySchema(Schema):
    id = fields.Int()
    name = fields.Str(required=True)
    breed = fields.Str(dump_only=True)


class PageSchema(Schema):
    offset = fields.Int()
    limit = fields.Int()


class PetSchema(Schema):
    category = fields.Nested(CategorySchema, many=True)
    name = fields.Str()


class TestNesting:
    def test_schema2jsonschema_with_nested_fields(self, spec_fixture):
        res = spec_fixture.openapi.schema2jsonschema(PetSchema)
        props = res["properties"]

        assert props["category"]["items"] == build_ref(
            spec_fixture.spec, "schema", "Category"
        )

    @pytest.mark.parametrize("modifier", ("only", "exclude"))
    def test_schema2jsonschema_with_nested_fields_only_exclude(
        self, spec_fixture, modifier
    ):
        class Child(Schema):
            i = fields.Int()
            j = fields.Int()

        class Parent(Schema):
            child = fields.Nested(Child, **{modifier: ("i",)})

        spec_fixture.openapi.schema2jsonschema(Parent)
        props = get_schemas(spec_fixture.spec)["Child"]["properties"]
        assert ("i" in props) == (modifier == "only")
        assert ("j" not in props) == (modifier == "only")

    def test_schema2jsonschema_with_plucked_field(self, spec_fixture):
        class PetSchema(Schema):
            breed = fields.Pluck(CategorySchema, "breed")

        category_schema = spec_fixture.openapi.schema2jsonschema(CategorySchema)
        pet_schema = spec_fixture.openapi.schema2jsonschema(PetSchema)
        assert (
            pet_schema["properties"]["breed"] == category_schema["properties"]["breed"]
        )

    def test_schema2jsonschema_with_nested_fields_with_adhoc_changes(
        self, spec_fixture
    ):
        category_schema = CategorySchema()
        category_schema.fields["id"].required = True

        class PetSchema(Schema):
            category = fields.Nested(category_schema, many=True)
            name = fields.Str()

        spec_fixture.spec.components.schema("Pet", schema=PetSchema)
        props = get_schemas(spec_fixture.spec)

        assert props["Category"] == spec_fixture.openapi.schema2jsonschema(
            category_schema
        )
        assert set(props["Category"]["required"]) == {"id", "name"}

        props["Category"]["required"] = ["name"]
        assert props["Category"] == spec_fixture.openapi.schema2jsonschema(
            CategorySchema
        )

    def test_schema2jsonschema_with_plucked_fields_with_adhoc_changes(
        self, spec_fixture
    ):
        category_schema = CategorySchema()
        category_schema.fields["breed"].dump_only = True

        class PetSchema(Schema):
            breed = fields.Pluck(category_schema, "breed", many=True)

        spec_fixture.spec.components.schema("Pet", schema=PetSchema)
        props = get_schemas(spec_fixture.spec)["Pet"]["properties"]

        assert props["breed"]["items"]["readOnly"] is True

    def test_schema2jsonschema_with_nested_excluded_fields(self, spec):
        category_schema = CategorySchema(exclude=("breed",))

        class PetSchema(Schema):
            category = fields.Nested(category_schema)

        spec.components.schema("Pet", schema=PetSchema)

        category_props = get_schemas(spec)["Category"]["properties"]
        assert "breed" not in category_props


def test_openapi_tools_validate_v2():
    ma_plugin = MarshmallowPlugin()
    spec = APISpec(
        title="Pets", version="0.1", plugins=(ma_plugin,), openapi_version="2.0"
    )
    openapi = ma_plugin.converter

    spec.components.schema("Category", schema=CategorySchema)
    spec.components.schema("Pet", {"discriminator": "name"}, schema=PetSchema)

    spec.path(
        view=None,
        path="/category/{category_id}",
        operations={
            "get": {
                "parameters": [
                    {"name": "q", "in": "query", "type": "string"},
                    {
                        "name": "category_id",
                        "in": "path",
                        "required": True,
                        "type": "string",
                    },
                    openapi._field2parameter(
                        field=fields.List(
                            fields.Str(),
                            validate=validate.OneOf(["freddie", "roger"]),
                        ),
                        location="query",
                        name="body",
                    ),
                ]
                + openapi.schema2parameters(PageSchema, location="query"),
                "responses": {200: {"schema": PetSchema, "description": "A pet"}},
            },
            "post": {
                "parameters": (
                    [
                        {
                            "name": "category_id",
                            "in": "path",
                            "required": True,
                            "type": "string",
                        }
                    ]
                    + openapi.schema2parameters(CategorySchema, location="body")
                ),
                "responses": {201: {"schema": PetSchema, "description": "A pet"}},
            },
        },
    )
    try:
        validate_spec(spec)
    except exceptions.OpenAPIError as error:
        pytest.fail(str(error))


def test_openapi_tools_validate_v3():
    ma_plugin = MarshmallowPlugin()
    spec = APISpec(
        title="Pets", version="0.1", plugins=(ma_plugin,), openapi_version="3.0.0"
    )
    openapi = ma_plugin.converter

    spec.components.schema("Category", schema=CategorySchema)
    spec.components.schema("Pet", schema=PetSchema)

    spec.path(
        view=None,
        path="/category/{category_id}",
        operations={
            "get": {
                "parameters": [
                    {"name": "q", "in": "query", "schema": {"type": "string"}},
                    {
                        "name": "category_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    openapi._field2parameter(
                        field=fields.List(
                            fields.Str(),
                            validate=validate.OneOf(["freddie", "roger"]),
                        ),
                        location="query",
                        name="body",
                    ),
                ]
                + openapi.schema2parameters(PageSchema, location="query"),
                "responses": {
                    200: {
                        "description": "success",
                        "content": {"application/json": {"schema": PetSchema}},
                    }
                },
            },
            "post": {
                "parameters": (
                    [
                        {
                            "name": "category_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ]
                ),
                "requestBody": {
                    "content": {"application/json": {"schema": CategorySchema}}
                },
                "responses": {
                    201: {
                        "description": "created",
                        "content": {"application/json": {"schema": PetSchema}},
                    }
                },
            },
        },
    )
    try:
        validate_spec(spec)
    except exceptions.OpenAPIError as error:
        pytest.fail(str(error))


class TestFieldValidation:
    class ValidationSchema(Schema):
        id = fields.Int(dump_only=True)
        range = fields.Int(validate=validate.Range(min=1, max=10))
        range_no_upper = fields.Float(validate=validate.Range(min=1))
        multiple_ranges = fields.Int(
            validate=[
                validate.Range(min=1),
                validate.Range(min=3),
                validate.Range(max=10),
                validate.Range(max=7),
            ]
        )
        list_length = fields.List(fields.Str, validate=validate.Length(min=1, max=10))
        custom_list_length = CustomList(
            fields.Str, validate=validate.Length(min=1, max=10)
        )
        string_length = fields.Str(validate=validate.Length(min=1, max=10))
        custom_field_length = CustomStringField(validate=validate.Length(min=1, max=10))
        multiple_lengths = fields.Str(
            validate=[
                validate.Length(min=1),
                validate.Length(min=3),
                validate.Length(max=10),
                validate.Length(max=7),
            ]
        )
        equal_length = fields.Str(
            validate=[validate.Length(equal=5), validate.Length(min=1, max=10)]
        )
        date_range = fields.DateTime(
            validate=validate.Range(
                min=datetime(1900, 1, 1),
            )
        )

    @pytest.mark.parametrize(
        ("field", "properties"),
        [
            ("range", {"minimum": 1, "maximum": 10}),
            ("range_no_upper", {"minimum": 1}),
            ("multiple_ranges", {"minimum": 3, "maximum": 7}),
            ("list_length", {"minItems": 1, "maxItems": 10}),
            ("custom_list_length", {"minItems": 1, "maxItems": 10}),
            ("string_length", {"minLength": 1, "maxLength": 10}),
            ("custom_field_length", {"minLength": 1, "maxLength": 10}),
            ("multiple_lengths", {"minLength": 3, "maxLength": 7}),
            ("equal_length", {"minLength": 5, "maxLength": 5}),
            ("date_range", {"x-minimum": datetime(1900, 1, 1)}),
        ],
    )
    def test_properties(self, field, properties, spec):
        spec.components.schema("Validation", schema=self.ValidationSchema)
        result = get_schemas(spec)["Validation"]["properties"][field]

        for attr, expected_value in properties.items():
            assert attr in result
            assert result[attr] == expected_value
