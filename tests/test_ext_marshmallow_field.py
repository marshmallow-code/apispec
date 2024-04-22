import datetime as dt
import re
from enum import Enum

import pytest
from marshmallow import Schema, fields, validate

from .schemas import CategorySchema, CustomIntegerField, CustomList, CustomStringField
from .utils import build_ref, get_schemas


def test_field2choices_preserving_order(openapi):
    choices = ["a", "b", "c", "aa", "0", "cc"]
    field = fields.String(validate=validate.OneOf(choices))
    assert openapi.field2choices(field) == {"enum": choices}


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
        (fields.TimeDelta, "integer"),
        (fields.Email, "string"),
        (fields.URL, "string"),
        (fields.IP, "string"),
        (fields.IPv4, "string"),
        (fields.IPv6, "string"),
        # Custom fields inherit types from their parents
        (CustomStringField, "string"),
        (CustomIntegerField, "integer"),
    ],
)
def test_field2property_type(FieldClass, jsontype, spec_fixture):
    field = FieldClass()
    res = spec_fixture.openapi.field2property(field)
    assert res["type"] == jsontype


@pytest.mark.parametrize("FieldClass", [fields.Field, fields.Raw])
def test_field2property_no_type_(FieldClass, spec_fixture):
    field = FieldClass()
    res = spec_fixture.openapi.field2property(field)
    assert "type" not in res


@pytest.mark.parametrize("ListClass", [fields.List, CustomList])
def test_formatted_field_translates_to_array(ListClass, spec_fixture):
    field = ListClass(fields.String)
    res = spec_fixture.openapi.field2property(field)
    assert res["type"] == "array"
    assert res["items"] == spec_fixture.openapi.field2property(fields.String())


@pytest.mark.parametrize(
    ("FieldClass", "expected_format"),
    [
        (fields.UUID, "uuid"),
        (fields.DateTime, "date-time"),
        (fields.Date, "date"),
        (fields.Email, "email"),
        (fields.URL, "url"),
        (fields.IP, "ip"),
        (fields.IPv4, "ipv4"),
        (fields.IPv6, "ipv6"),
    ],
)
def test_field2property_formats(FieldClass, expected_format, spec_fixture):
    field = FieldClass()
    res = spec_fixture.openapi.field2property(field)
    assert res["format"] == expected_format


def test_field_with_description(spec_fixture):
    field = fields.Str(metadata={"description": "a username"})
    res = spec_fixture.openapi.field2property(field)
    assert res["description"] == "a username"


def test_field_with_load_default(spec_fixture):
    field = fields.Str(dump_default="foo", load_default="bar")
    res = spec_fixture.openapi.field2property(field)
    assert res["default"] == "bar"


def test_boolean_field_with_false_load_default(spec_fixture):
    field = fields.Boolean(dump_default=None, load_default=False)
    res = spec_fixture.openapi.field2property(field)
    assert res["default"] is False


def test_datetime_field_with_load_default(spec_fixture):
    field = fields.Date(load_default=dt.date(2014, 7, 18))
    res = spec_fixture.openapi.field2property(field)
    assert res["default"] == dt.date(2014, 7, 18).isoformat()


def test_field_with_load_default_callable(spec_fixture):
    field = fields.Str(load_default=lambda: "dummy")
    res = spec_fixture.openapi.field2property(field)
    assert "default" not in res


def test_field_with_default(spec_fixture):
    field = fields.Str(metadata={"default": "Manual default"})
    res = spec_fixture.openapi.field2property(field)
    assert res["default"] == "Manual default"


def test_field_with_default_and_load_default(spec_fixture):
    field = fields.Int(load_default=12, metadata={"default": 42})
    res = spec_fixture.openapi.field2property(field)
    assert res["default"] == 42


def test_field_with_choices(spec_fixture):
    field = fields.Str(validate=validate.OneOf(["freddie", "brian", "john"]))
    res = spec_fixture.openapi.field2property(field)
    assert set(res["enum"]) == {"freddie", "brian", "john"}


def test_field_with_nullable_choices(spec_fixture):
    field = fields.Str(
        validate=validate.OneOf(["freddie", "brian", "john"]), allow_none=True
    )
    res = spec_fixture.openapi.field2property(field)
    assert set(res["enum"]) == {"freddie", "brian", "john", None}


def test_field_with_nullable_choices_returns_only_one_none(spec_fixture):
    field = fields.Str(
        validate=validate.OneOf(["freddie", "brian", "john", None]), allow_none=True
    )
    res = spec_fixture.openapi.field2property(field)
    assert res["enum"] == ["freddie", "brian", "john", None]


def test_field_with_equal(spec_fixture):
    field = fields.Str(validate=validate.Equal("only choice"))
    res = spec_fixture.openapi.field2property(field)
    assert res["enum"] == ["only choice"]


def test_only_allows_valid_properties_in_metadata(spec_fixture):
    field = fields.Str(
        load_default="foo",
        metadata={
            "description": "foo",
            "not_valid": "lol",
            "allOf": ["bar"],
            "enum": ["red", "blue"],
        },
    )
    res = spec_fixture.openapi.field2property(field)
    assert res["default"] == field.load_default
    assert "description" in res
    assert "enum" in res
    assert "allOf" in res
    assert "not_valid" not in res


def test_field_with_choices_multiple(spec_fixture):
    field = fields.Str(
        validate=[
            validate.OneOf(["freddie", "brian", "john"]),
            validate.OneOf(["brian", "john", "roger"]),
        ]
    )
    res = spec_fixture.openapi.field2property(field)
    assert set(res["enum"]) == {"brian", "john"}


def test_field_with_additional_metadata(spec_fixture):
    field = fields.Str(metadata={"minLength": 6, "maxLength": 100})
    res = spec_fixture.openapi.field2property(field)
    assert res["maxLength"] == 100
    assert res["minLength"] == 6


@pytest.mark.parametrize("spec_fixture", ("2.0", "3.0.0", "3.1.0"), indirect=True)
def test_field_with_allow_none(spec_fixture):
    field = fields.Str(allow_none=True)
    res = spec_fixture.openapi.field2property(field)
    if spec_fixture.openapi.openapi_version.major < 3:
        assert res["x-nullable"] is True
    elif spec_fixture.openapi.openapi_version.minor < 1:
        assert res["nullable"] is True
    else:
        assert "nullable" not in res
        assert res["type"] == ["string", "null"]


@pytest.mark.parametrize("spec_fixture", ("2.0", "3.0.0", "3.1.0"), indirect=True)
def test_nested_nullable(spec_fixture):
    class Child(Schema):
        name = fields.Str()

    field = fields.Nested(Child, allow_none=True)
    res = spec_fixture.openapi.field2property(field)
    version = spec_fixture.openapi.openapi_version
    if version.major < 3:
        assert res == {"$ref": "#/definitions/Child", "x-nullable": True}
    elif version.major == 3 and version.minor < 1:
        assert res == {
            "nullable": True,
            "allOf": [{"$ref": "#/components/schemas/Child"}],
        }
    else:
        assert res == {
            "anyOf": [{"$ref": "#/components/schemas/Child"}, {"type": "null"}]
        }


@pytest.mark.parametrize("spec_fixture", ("2.0", "3.0.0", "3.1.0"), indirect=True)
def test_nullable_pluck(spec_fixture):
    class Example(Schema):
        name = fields.Str()

    field = fields.Pluck(Example, "name", allow_none=True)
    res = spec_fixture.openapi.field2property(field)
    version = spec_fixture.openapi.openapi_version
    if version.major < 3:
        assert res == {"type": "string", "x-nullable": True}
    elif version.major == 3 and version.minor < 1:
        assert res == {"type": "string", "nullable": True}
    else:
        assert res == {"type": ["string", "null"]}


def test_field_with_dump_only(spec_fixture):
    field = fields.Str(dump_only=True)
    res = spec_fixture.openapi.field2property(field)
    assert res["readOnly"] is True


@pytest.mark.parametrize("spec_fixture", ("2.0", "3.0.0", "3.1.0"), indirect=True)
def test_field_with_load_only(spec_fixture):
    field = fields.Str(load_only=True)
    res = spec_fixture.openapi.field2property(field)
    if spec_fixture.openapi.openapi_version.major < 3:
        assert "writeOnly" not in res
    else:
        assert res["writeOnly"] is True


def test_field_with_range_no_type(spec_fixture):
    field = fields.Field(validate=validate.Range(min=1, max=10))
    res = spec_fixture.openapi.field2property(field)
    assert res["x-minimum"] == 1
    assert res["x-maximum"] == 10
    assert "type" not in res


@pytest.mark.parametrize("field", (fields.Number, fields.Integer))
def test_field_with_range_string_type(spec_fixture, field):
    field = field(validate=validate.Range(min=1, max=10))
    res = spec_fixture.openapi.field2property(field)
    assert res["minimum"] == 1
    assert res["maximum"] == 10
    assert isinstance(res["type"], str)


@pytest.mark.parametrize("spec_fixture", ("3.1.0",), indirect=True)
def test_field_with_range_type_list_with_number(spec_fixture):
    class NullableInteger(fields.Field):
        """Nullable integer"""

    spec_fixture.openapi.map_to_openapi_type(NullableInteger, ["integer", "null"], None)

    field = NullableInteger(validate=validate.Range(min=1, max=10))
    res = spec_fixture.openapi.field2property(field)
    assert res["minimum"] == 1
    assert res["maximum"] == 10
    assert res["type"] == ["integer", "null"]


@pytest.mark.parametrize("spec_fixture", ("3.1.0",), indirect=True)
def test_field_with_range_type_list_without_number(spec_fixture):
    class NullableInteger(fields.Field):
        """Nullable integer"""

    spec_fixture.openapi.map_to_openapi_type(NullableInteger, ["string", "null"], None)

    field = NullableInteger(validate=validate.Range(min=1, max=10))
    res = spec_fixture.openapi.field2property(field)
    assert res["x-minimum"] == 1
    assert res["x-maximum"] == 10
    assert res["type"] == ["string", "null"]


def test_field_with_range_datetime_type(spec_fixture):
    field = fields.DateTime(
        validate=validate.Range(
            min=dt.datetime(1900, 1, 1),
            max=dt.datetime(2000, 1, 1),
        )
    )
    res = spec_fixture.openapi.field2property(field)
    assert res["x-minimum"] == "1900-01-01T00:00:00"
    assert res["x-maximum"] == "2000-01-01T00:00:00"
    assert isinstance(res["type"], str)


def test_field_with_str_regex(spec_fixture):
    regex_str = "^[a-zA-Z0-9]$"
    field = fields.Str(validate=validate.Regexp(regex_str))
    ret = spec_fixture.openapi.field2property(field)
    assert ret["pattern"] == regex_str


def test_field_with_pattern_obj_regex(spec_fixture):
    regex_str = "^[a-zA-Z0-9]$"
    field = fields.Str(validate=validate.Regexp(re.compile(regex_str)))
    ret = spec_fixture.openapi.field2property(field)
    assert ret["pattern"] == regex_str


def test_field_with_no_pattern(spec_fixture):
    field = fields.Str()
    ret = spec_fixture.openapi.field2property(field)
    assert "pattern" not in ret


def test_field_with_multiple_patterns(recwarn, spec_fixture):
    regex_validators = [validate.Regexp("winner"), validate.Regexp("loser")]
    field = fields.Str(validate=regex_validators)
    with pytest.warns(UserWarning, match="More than one regex validator"):
        ret = spec_fixture.openapi.field2property(field)
    assert ret["pattern"] == "winner"


def test_enum_symbol_field(spec_fixture):
    class MyEnum(Enum):
        one = 1
        two = 2

    field = fields.Enum(MyEnum)
    ret = spec_fixture.openapi.field2property(field)
    assert ret["type"] == "string"
    assert ret["enum"] == ["one", "two"]


@pytest.mark.parametrize("by_value", [fields.Integer, True])
def test_enum_value_field(spec_fixture, by_value):
    class MyEnum(Enum):
        one = 1
        two = 2

    field = fields.Enum(MyEnum, by_value=by_value)
    ret = spec_fixture.openapi.field2property(field)
    if by_value is True:
        assert "type" not in ret
    else:
        assert ret["type"] == "integer"
    assert ret["enum"] == [1, 2]


def test_nullable_enum(spec_fixture):
    class MyEnum(Enum):
        one = 1
        two = 2

    field = fields.Enum(MyEnum, allow_none=True, by_value=True)
    ret = spec_fixture.openapi.field2property(field)
    assert ret["enum"] == [1, 2, None]


def test_nullable_enum_returns_only_one_none(spec_fixture):
    class MyEnum(Enum):
        one = 1
        two = 2
        three = None

    field = fields.Enum(MyEnum, allow_none=True, by_value=True)
    ret = spec_fixture.openapi.field2property(field)
    assert ret["enum"] == [1, 2, None]


def test_field2property_nested_spec_metadatas(spec_fixture):
    spec_fixture.spec.components.schema("Category", schema=CategorySchema)
    category = fields.Nested(
        CategorySchema,
        metadata={
            "description": "A category",
            "invalid_property": "not in the result",
            "x_extension": "A great extension",
        },
    )
    result = spec_fixture.openapi.field2property(category)
    assert result == {
        "allOf": [build_ref(spec_fixture.spec, "schema", "Category")],
        "description": "A category",
        "x-extension": "A great extension",
    }


def test_field2property_nested_spec(spec_fixture):
    spec_fixture.spec.components.schema("Category", schema=CategorySchema)
    category = fields.Nested(CategorySchema)
    assert spec_fixture.openapi.field2property(category) == build_ref(
        spec_fixture.spec, "schema", "Category"
    )


def test_field2property_nested_many_spec(spec_fixture):
    spec_fixture.spec.components.schema("Category", schema=CategorySchema)
    category = fields.Nested(CategorySchema, many=True)
    ret = spec_fixture.openapi.field2property(category)
    assert ret["type"] == "array"
    assert ret["items"] == build_ref(spec_fixture.spec, "schema", "Category")


def test_field2property_nested_ref(spec_fixture):
    category = fields.Nested(CategorySchema)
    ref = spec_fixture.openapi.field2property(category)
    assert ref == build_ref(spec_fixture.spec, "schema", "Category")


def test_field2property_nested_many(spec_fixture):
    categories = fields.Nested(CategorySchema, many=True)
    res = spec_fixture.openapi.field2property(categories)
    assert res["type"] == "array"
    assert res["items"] == build_ref(spec_fixture.spec, "schema", "Category")


def test_nested_field_with_property(spec_fixture):
    category_1 = fields.Nested(CategorySchema)
    category_2 = fields.Nested(CategorySchema, dump_only=True)
    category_3 = fields.Nested(CategorySchema, many=True)
    category_4 = fields.Nested(CategorySchema, many=True, dump_only=True)
    spec_fixture.spec.components.schema("Category", schema=CategorySchema)

    assert spec_fixture.openapi.field2property(category_1) == build_ref(
        spec_fixture.spec, "schema", "Category"
    )
    assert spec_fixture.openapi.field2property(category_2) == {
        "allOf": [build_ref(spec_fixture.spec, "schema", "Category")],
        "readOnly": True,
    }
    assert spec_fixture.openapi.field2property(category_3) == {
        "items": build_ref(spec_fixture.spec, "schema", "Category"),
        "type": "array",
    }
    assert spec_fixture.openapi.field2property(category_4) == {
        "items": build_ref(spec_fixture.spec, "schema", "Category"),
        "readOnly": True,
        "type": "array",
    }


def test_datetime2property_iso(spec_fixture):
    field = fields.DateTime(format="iso")
    res = spec_fixture.openapi.field2property(field)
    assert res == {
        "type": "string",
        "format": "date-time",
    }


def test_datetime2property_rfc(spec_fixture):
    field = fields.DateTime(format="rfc")
    res = spec_fixture.openapi.field2property(field)
    assert res == {
        "type": "string",
        "format": None,
        "example": "Wed, 02 Oct 2002 13:00:00 GMT",
        "pattern": r"((Mon|Tue|Wed|Thu|Fri|Sat|Sun), ){0,1}\d{2} "
        + r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} \d{2}:\d{2}:\d{2} "
        + r"(UT|GMT|EST|EDT|CST|CDT|MST|MDT|PST|PDT|(Z|A|M|N)|(\+|-)\d{4})",
    }


def test_datetime2property_timestamp(spec_fixture):
    field = fields.DateTime(format="timestamp")
    res = spec_fixture.openapi.field2property(field)
    assert res == {
        "type": "number",
        "format": "float",
        "min": "0",
        "example": "1676451245.596",
    }


def test_datetime2property_timestamp_ms(spec_fixture):
    field = fields.DateTime(format="timestamp_ms")
    res = spec_fixture.openapi.field2property(field)
    assert res == {
        "type": "number",
        "format": "float",
        "min": "0",
        "example": "1676451277514.654",
    }


def test_datetime2property_custom_format(spec_fixture):
    field = fields.DateTime(
        format="%d-%m%Y %H:%M:%S",
        metadata={
            "pattern": r"^((?:(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2}(?:\.\d+)?))(Z|[\+-]\d{2}:\d{2})?)$"
        },
    )
    res = spec_fixture.openapi.field2property(field)
    assert res == {
        "type": "string",
        "format": None,
        "pattern": r"^((?:(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2}(?:\.\d+)?))(Z|[\+-]\d{2}:\d{2})?)$",
    }


def test_datetime2property_custom_format_missing_regex(spec_fixture):
    field = fields.DateTime(format="%d-%m%Y %H:%M:%S")
    res = spec_fixture.openapi.field2property(field)
    assert res == {
        "type": "string",
        "format": None,
        "pattern": None,
    }


class TestField2PropertyPluck:
    @pytest.fixture(autouse=True)
    def _setup(self, spec_fixture):
        self.field2property = spec_fixture.openapi.field2property

        self.spec = spec_fixture.spec
        self.spec.components.schema("Category", schema=CategorySchema)
        self.unplucked = get_schemas(self.spec)["Category"]["properties"]["breed"]

    def test_spec(self, spec_fixture):
        breed = fields.Pluck(CategorySchema, "breed")
        assert self.field2property(breed) == self.unplucked

    def test_with_property(self):
        breed = fields.Pluck(CategorySchema, "breed", dump_only=True)
        assert self.field2property(breed) == {**self.unplucked, "readOnly": True}

    def test_metadata(self):
        breed = fields.Pluck(
            CategorySchema,
            "breed",
            metadata={
                "description": "Category breed",
                "invalid_property": "not in the result",
                "x_extension": "A great extension",
            },
        )
        assert self.field2property(breed) == {
            **self.unplucked,
            "description": "Category breed",
            "x-extension": "A great extension",
        }

    def test_many(self):
        breed = fields.Pluck(CategorySchema, "breed", many=True)
        assert self.field2property(breed) == {"type": "array", "items": self.unplucked}

    def test_many_with_property(self):
        breed = fields.Pluck(CategorySchema, "breed", many=True, dump_only=True)
        assert self.field2property(breed) == {
            "items": self.unplucked,
            "type": "array",
            "readOnly": True,
        }


def test_custom_properties_for_custom_fields(spec_fixture):
    def custom_string2properties(self, field, **kwargs):
        ret = {}
        if isinstance(field, CustomStringField):
            if self.openapi_version.major == 2:
                ret["x-customString"] = True
            else:
                ret["x-customString"] = False
        return ret

    spec_fixture.marshmallow_plugin.converter.add_attribute_function(
        custom_string2properties
    )
    properties = spec_fixture.marshmallow_plugin.converter.field2property(
        CustomStringField()
    )
    assert properties["x-customString"] == (
        spec_fixture.openapi.openapi_version.major == 2
    )


def test_field2property_with_non_string_metadata_keys(spec_fixture):
    class _DesertSentinel:
        pass

    field = fields.Boolean(metadata={"description": "A description"})
    field.metadata[_DesertSentinel()] = "to be ignored"
    result = spec_fixture.openapi.field2property(field)
    assert result == {"description": "A description", "type": "boolean"}
