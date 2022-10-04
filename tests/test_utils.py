from apispec import utils


def test_build_reference():
    assert utils.build_reference("schema", 2, "Test") == {"$ref": "#/definitions/Test"}
    assert utils.build_reference("parameter", 2, "Test") == {
        "$ref": "#/parameters/Test"
    }
    assert utils.build_reference("response", 2, "Test") == {"$ref": "#/responses/Test"}
    assert utils.build_reference("security_scheme", 2, "Test") == {
        "$ref": "#/securityDefinitions/Test"
    }
    assert utils.build_reference("schema", 3, "Test") == {
        "$ref": "#/components/schemas/Test"
    }
    assert utils.build_reference("parameter", 3, "Test") == {
        "$ref": "#/components/parameters/Test"
    }
    assert utils.build_reference("response", 3, "Test") == {
        "$ref": "#/components/responses/Test"
    }
    assert utils.build_reference("security_scheme", 3, "Test") == {
        "$ref": "#/components/securitySchemes/Test"
    }
