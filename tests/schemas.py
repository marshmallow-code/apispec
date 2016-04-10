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


class SelfReferencingSchema(Schema):
    id = fields.Int()
    single = fields.Nested('self')
    single_with_ref = fields.Nested('self', ref='#/definitions/Self')
    many = fields.Nested('self', many=True)
    many_with_ref = fields.Nested('self', many=True, ref='#/definitions/Selves')
