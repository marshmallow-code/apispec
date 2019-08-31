import re

import pytest
from marshmallow import fields, validate

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

from .schemas import CategorySchema, CustomList, CustomStringField, CustomIntegerField
from .utils import build_ref


def test_field2choices_preserving_order(ma_plugin):
    choices = ["a", "b", "c", "aa", "0", "cc"]
    field = fields.String(validate=validate.OneOf(choices))
    assert ma_plugin.field2choices(field) == {"enum": choices}


@pytest.mark.parametrize(
    ("FieldClass", "jsontype"),
    [
        (fields.Integer, "integer"),
        (fields.Number, "number"),
        (fields.Float, "number"),
        (fields.String, "string"),
        (fields.Str, "string"),
        (fields.Boolean, "boolean"),
        (fields.Bool, "boolean"),
        (fields.UUID, "string"),
        (fields.DateTime, "string"),
        (fields.Date, "string"),
        (fields.Time, "string"),
        (fields.Email, "string"),
        (fields.URL, "string"),
        # Assume base Field and Raw are strings
        (fields.Field, "string"),
        (fields.Raw, "string"),
        # Custom fields inherit types from their parents
        (CustomStringField, "string"),
        (CustomIntegerField, "integer"),
    ],
)
def test_field2property_type(FieldClass, jsontype, ma_plugin):
    field = FieldClass()
    res = ma_plugin.field2property(field)
    assert res["type"] == jsontype


@pytest.mark.parametrize("ListClass", [fields.List, CustomList])
def test_formatted_field_translates_to_array(ListClass, ma_plugin):
    field = ListClass(fields.String)
    res = ma_plugin.field2property(field)
    assert res["type"] == "array"
    assert res["items"] == ma_plugin.field2property(fields.String())


@pytest.mark.parametrize(
    ("FieldClass", "expected_format"),
    [
        (fields.Integer, "int32"),
        (fields.Float, "float"),
        (fields.UUID, "uuid"),
        (fields.DateTime, "date-time"),
        (fields.Date, "date"),
        (fields.Email, "email"),
        (fields.URL, "url"),
    ],
)
def test_field2property_formats(FieldClass, expected_format, ma_plugin):
    field = FieldClass()
    res = ma_plugin.field2property(field)
    assert res["format"] == expected_format


def test_field_with_description(ma_plugin):
    field = fields.Str(description="a username")
    res = ma_plugin.field2property(field)
    assert res["description"] == "a username"


def test_field_with_missing(ma_plugin):
    field = fields.Str(default="foo", missing="bar")
    res = ma_plugin.field2property(field)
    assert res["default"] == "bar"


def test_field_with_boolean_false_missing(ma_plugin):
    field = fields.Boolean(default=None, missing=False)
    res = ma_plugin.field2property(field)
    assert res["default"] is False


def test_field_with_missing_load(ma_plugin):
    field = fields.Str(default="foo", missing="bar")
    res = ma_plugin.field2property(field)
    assert res["default"] == "bar"


def test_field_with_boolean_false_missing_load(ma_plugin):
    field = fields.Boolean(default=None, missing=False)
    res = ma_plugin.field2property(field)
    assert res["default"] is False


def test_field_with_missing_callable(ma_plugin):
    field = fields.Str(missing=lambda: "dummy")
    res = ma_plugin.field2property(field)
    assert "default" not in res


def test_field_with_doc_default(ma_plugin):
    field = fields.Str(doc_default="Manual default")
    res = ma_plugin.field2property(field)
    assert res["default"] == "Manual default"


def test_field_with_doc_default_and_missing(ma_plugin):
    field = fields.Int(doc_default=42, missing=12)
    res = ma_plugin.field2property(field)
    assert res["default"] == 42


def test_field_with_choices(ma_plugin):
    field = fields.Str(validate=validate.OneOf(["freddie", "brian", "john"]))
    res = ma_plugin.field2property(field)
    assert set(res["enum"]) == {"freddie", "brian", "john"}


def test_field_with_equal(ma_plugin):
    field = fields.Str(validate=validate.Equal("only choice"))
    res = ma_plugin.field2property(field)
    assert res["enum"] == ["only choice"]


def test_only_allows_valid_properties_in_metadata(ma_plugin):
    field = fields.Str(
        missing="foo",
        description="foo",
        enum=["red", "blue"],
        allOf=["bar"],
        not_valid="lol",
    )
    res = ma_plugin.field2property(field)
    assert res["default"] == field.missing
    assert "description" in res
    assert "enum" in res
    assert "allOf" in res
    assert "not_valid" not in res


def test_field_with_choices_multiple(ma_plugin):
    field = fields.Str(
        validate=[
            validate.OneOf(["freddie", "brian", "john"]),
            validate.OneOf(["brian", "john", "roger"]),
        ]
    )
    res = ma_plugin.field2property(field)
    assert set(res["enum"]) == {"brian", "john"}


def test_field_with_additional_metadata(ma_plugin):
    field = fields.Str(minLength=6, maxLength=100)
    res = ma_plugin.field2property(field)
    assert res["maxLength"] == 100
    assert res["minLength"] == 6


def test_field_with_allow_none(ma_plugin):
    field = fields.Str(allow_none=True)
    res = ma_plugin.field2property(field)
    if ma_plugin.openapi_version.major < 3:
        assert res["x-nullable"] is True
    else:
        assert res["nullable"] is True


def test_field_with_str_regex(ma_plugin):
    regex_str = "^[a-zA-Z0-9]$"
    field = fields.Str(validate=validate.Regexp(regex_str))
    ret = ma_plugin.field2property(field)
    assert ret["pattern"] == regex_str


def test_field_with_pattern_obj_regex(ma_plugin):
    regex_str = "^[a-zA-Z0-9]$"
    field = fields.Str(validate=validate.Regexp(re.compile(regex_str)))
    ret = ma_plugin.field2property(field)
    assert ret["pattern"] == regex_str


def test_field_with_no_pattern(ma_plugin):
    field = fields.Str()
    ret = ma_plugin.field2property(field)
    assert "pattern" not in ret


def test_field_with_multiple_patterns(recwarn, ma_plugin):
    regex_validators = [validate.Regexp("winner"), validate.Regexp("loser")]
    field = fields.Str(validate=regex_validators)
    with pytest.warns(UserWarning, match="More than one regex validator"):
        ret = ma_plugin.field2property(field)
    assert ret["pattern"] == "winner"


def test_field2property_nested_spec_metadatas(spec_fixture):
    spec_fixture.spec.components.schema("Category", schema=CategorySchema)
    category = fields.Nested(
        CategorySchema,
        description="A category",
        invalid_property="not in the result",
        x_extension="A great extension",
    )
    result = spec_fixture.ma_plugin.field2property(category)
    assert result == {
        "allOf": [build_ref(spec_fixture.spec, "schema", "Category")],
        "description": "A category",
        "x-extension": "A great extension",
    }


def test_field2property_nested_spec(ma_plugin):
    ma_plugin.spec.components.schema("Category", schema=CategorySchema)
    category = fields.Nested(CategorySchema)
    assert ma_plugin.field2property(category) == build_ref(
        ma_plugin.spec, "schema", "Category"
    )


def test_field2property_nested_many_spec(ma_plugin):
    ma_plugin.spec.components.schema("Category", schema=CategorySchema)
    category = fields.Nested(CategorySchema, many=True)
    ret = ma_plugin.field2property(category)
    assert ret["type"] == "array"
    assert ret["items"] == build_ref(ma_plugin.spec, "schema", "Category")


def test_field2property_nested_ref(ma_plugin):
    category = fields.Nested(CategorySchema)
    ref = ma_plugin.field2property(category)
    assert ref == build_ref(ma_plugin.spec, "schema", "Category")


def test_field2property_nested_many(ma_plugin):
    categories = fields.Nested(CategorySchema, many=True)
    res = ma_plugin.field2property(categories)
    assert res["type"] == "array"
    assert res["items"] == build_ref(ma_plugin.spec, "schema", "Category")


def test_nested_field_with_property(ma_plugin):
    category_1 = fields.Nested(CategorySchema)
    category_2 = fields.Nested(CategorySchema, dump_only=True)
    category_3 = fields.Nested(CategorySchema, many=True)
    category_4 = fields.Nested(CategorySchema, many=True, dump_only=True)
    ma_plugin.spec.components.schema("Category", schema=CategorySchema)

    assert ma_plugin.field2property(category_1) == build_ref(
        ma_plugin.spec, "schema", "Category"
    )
    assert ma_plugin.field2property(category_2) == {
        "allOf": [build_ref(ma_plugin.spec, "schema", "Category")],
        "readOnly": True,
    }
    assert ma_plugin.field2property(category_3) == {
        "items": build_ref(ma_plugin.spec, "schema", "Category"),
        "type": "array",
    }
    assert ma_plugin.field2property(category_4) == {
        "items": build_ref(ma_plugin.spec, "schema", "Category"),
        "readOnly": True,
        "type": "array",
    }


def test_custom_properties_for_custom_fields():
    def custom_string2properties(field, **kwargs):
        ret = {}
        if isinstance(field, CustomStringField):
            ret["x-customString"] = True
        return ret

    ma_plugin = MarshmallowPlugin()
    APISpec(
        title="Validation", version="0.1", openapi_version="3.0.0", plugins=(ma_plugin,)
    )
    ma_plugin.add_attribute_function(custom_string2properties)
    properties = ma_plugin.field2property(CustomStringField())
    assert properties["x-customString"]
