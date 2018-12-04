# -*- coding: utf-8 -*-
import pytest

from apispec.ext.marshmallow.common import make_schema_key
from .schemas import PetSchema, SampleSchema


class TestMakeSchemaKey:
    def test_raise_if_schema_class_passed(self):
        with pytest.raises(TypeError, match='based on a Schema instance'):
            make_schema_key(PetSchema)

    def test_same_schemas_instances_equal(self):
        assert make_schema_key(PetSchema()) == make_schema_key(PetSchema())

    def test_different_schemas_not_equal(self):
        assert make_schema_key(PetSchema()) != make_schema_key(SampleSchema())

    def test_instances_with_different_modifiers_not_equal(self):
        assert make_schema_key(PetSchema()) != make_schema_key(PetSchema(partial=True))
