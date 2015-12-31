from marshmallow import Schema, fields

class PetSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()


class SampleSchema(Schema):
    runs = fields.Nested('RunSchema', many=True, exclude=('sample',))

    count = fields.Int()


class RunSchema(Schema):
    sample = fields.Nested(SampleSchema, exclude=('runs',))


class AnalysisSchema(Schema):
    sample = fields.Nested(SampleSchema)