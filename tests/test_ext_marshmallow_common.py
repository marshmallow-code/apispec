# -*- coding: utf-8 -*-
import pytest

from apispec.ext.marshmallow.common import make_schema_key, get_unique_schema_name
from .schemas import PetSchema, SampleSchema


class TestMakeSchemaKey:
    def test_raise_if_schema_class_passed(self):
        with pytest.raises(TypeError, match="based on a Schema instance"):
            make_schema_key(PetSchema)

    def test_same_schemas_instances_equal(self):
        assert make_schema_key(PetSchema()) == make_schema_key(PetSchema())

    def test_different_schemas_not_equal(self):
        assert make_schema_key(PetSchema()) != make_schema_key(SampleSchema())

    def test_instances_with_different_modifiers_not_equal(self):
        assert make_schema_key(PetSchema()) != make_schema_key(PetSchema(partial=True))


class TestUniqueName:
    def test_unique_name(self, spec):
        properties = {
            "id": {"type": "integer", "format": "int64"},
            "name": {"type": "string", "example": "doggie"},
        }

        name = get_unique_schema_name(spec.components, "Pet")
        assert name == "Pet"

        spec.components.schema("Pet", properties=properties)
        with pytest.warns(
            UserWarning, match="Multiple schemas resolved to the name Pet"
        ):
            name_1 = get_unique_schema_name(spec.components, "Pet")
        assert name_1 == "Pet1"

        spec.components.schema("Pet1", properties=properties)
        with pytest.warns(
            UserWarning, match="Multiple schemas resolved to the name Pet"
        ):
            name_2 = get_unique_schema_name(spec.components, "Pet")
        assert name_2 == "Pet2"
