from marshmallow import Schema, fields

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin


class UUIDListSchema(Schema):
    uuids = fields.List(fields.UUID(), data_key=None)


def _build_schema(list_as_array: bool):
    plugin = MarshmallowPlugin(list_as_array=list_as_array)
    spec = APISpec(
        title="Test",
        version="1.0.0",
        openapi_version="3.0.2",
        plugins=[plugin],
    )
    spec.path(
        path="/list",
        operations={
            "post": {
                "requestBody": {
                    "content": {"application/json": {"schema": UUIDListSchema()}}
                },
                "responses": {"200": {}},
            }
        },
    )
    schema = spec.to_dict()["paths"]["/list"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]

    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        schema = spec.to_dict()["components"]["schemas"][ref_name]

    return schema


def test_default_is_object():
    schema = _build_schema(list_as_array=False)
    assert schema["type"] == "object"


def test_list_as_array_flag():
    schema = _build_schema(list_as_array=True)
    assert schema["type"] == "array"
    assert "items" in schema
