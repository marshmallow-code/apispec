from marshmallow import Schema, fields

class PetSchema(Schema):
    id = fields.Int()
    name = fields.Str()
