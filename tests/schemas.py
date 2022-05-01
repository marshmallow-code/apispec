from marshmallow import Schema, fields


class PetSchema(Schema):
    description = dict(id="Pet id", name="Pet name", password="Password")
    id = fields.Int(dump_only=True, metadata={"description": description["id"]})
    name = fields.Str(
        required=True,
        metadata={
            "description": description["name"],
            "deprecated": False,
            "allowEmptyValue": False,
        },
    )
    password = fields.Str(
        load_only=True, metadata={"description": description["password"]}
    )


class SampleSchema(Schema):
    runs = fields.Nested("RunSchema", many=True)

    count = fields.Int()


class RunSchema(Schema):
    sample = fields.Nested(SampleSchema)


class AnalysisSchema(Schema):
    sample = fields.Nested(SampleSchema)


class AnalysisWithListSchema(Schema):
    samples = fields.List(fields.Nested(SampleSchema))


class PatternedObjectSchema(Schema):
    count = fields.Int(dump_only=True, metadata={"x-count": 1})
    count2 = fields.Int(dump_only=True, metadata={"x_count2": 2})


class SelfReferencingSchema(Schema):
    id = fields.Int()
    single = fields.Nested(lambda: SelfReferencingSchema())
    multiple = fields.Nested(lambda: SelfReferencingSchema(many=True))


class OrderedSchema(Schema):
    field1 = fields.Int()
    field2 = fields.Int()
    field3 = fields.Int()
    field4 = fields.Int()
    field5 = fields.Int()

    class Meta:
        ordered = True


class DefaultValuesSchema(Schema):
    number_auto_default = fields.Int(load_default=12)
    number_manual_default = fields.Int(load_default=12, metadata={"default": 42})
    string_callable_default = fields.Str(load_default=lambda: "Callable")
    string_manual_default = fields.Str(
        load_default=lambda: "Callable", metadata={"default": "Manual"}
    )
    numbers = fields.List(fields.Int, load_default=list)


class CategorySchema(Schema):
    id = fields.Int()
    name = fields.Str(required=True)
    breed = fields.Str(dump_only=True)


class CustomList(fields.List):
    pass


class CustomStringField(fields.String):
    pass


class CustomIntegerField(fields.Integer):
    pass
