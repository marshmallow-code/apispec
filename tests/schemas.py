from marshmallow import Schema, fields

class PetSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
