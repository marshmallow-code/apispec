import copy
from http import HTTPStatus

import pytest
import yaml

from apispec import APISpec, BasePlugin
from apispec.exceptions import (
    APISpecError,
    DuplicateComponentNameError,
    DuplicateParameterError,
    InvalidParameterError,
)

from .utils import (
    get_schemas,
    get_examples,
    get_paths,
    get_parameters,
    get_headers,
    get_responses,
    get_security_schemes,
    build_ref,
)


description = "This is a sample Petstore server.  You can find out more "
'about Swagger at <a href="http://swagger.wordnik.com">http://swagger.wordnik.com</a> '
"or on irc.freenode.net, #swagger.  For this sample, you can use the api "
'key "special-key" to test the authorization filters'


class RefsSchemaTestMixin:
    REFS_SCHEMA = {
        "properties": {
            "nested": "NestedSchema",
            "deep_nested": {"properties": {"nested": "NestedSchema"}},
            "nested_list": {"items": "DeepNestedSchema"},
            "deep_nested_list": {
                "items": {"properties": {"nested": "DeepNestedSchema"}}
            },
            "allof": {
                "allOf": [
                    "AllOfSchema",
                    {"properties": {"nested": "AllOfSchema"}},
                ]
            },
            "oneof": {
                "oneOf": [
                    "OneOfSchema",
                    {"properties": {"nested": "OneOfSchema"}},
                ]
            },
            "anyof": {
                "anyOf": [
                    "AnyOfSchema",
                    {"properties": {"nested": "AnyOfSchema"}},
                ]
            },
            "not": "NotSchema",
            "deep_not": {"properties": {"nested": "DeepNotSchema"}},
        }
    }

    @staticmethod
    def assert_schema_refs(spec, schema):
        props = schema["properties"]
        assert props["nested"] == build_ref(spec, "schema", "NestedSchema")
        assert props["deep_nested"]["properties"]["nested"] == build_ref(
            spec, "schema", "NestedSchema"
        )
        assert props["nested_list"]["items"] == build_ref(
            spec, "schema", "DeepNestedSchema"
        )
        assert props["deep_nested_list"]["items"]["properties"]["nested"] == build_ref(
            spec, "schema", "DeepNestedSchema"
        )
        assert props["allof"]["allOf"][0] == build_ref(spec, "schema", "AllOfSchema")
        assert props["allof"]["allOf"][1]["properties"]["nested"] == build_ref(
            spec, "schema", "AllOfSchema"
        )
        assert props["oneof"]["oneOf"][0] == build_ref(spec, "schema", "OneOfSchema")
        assert props["oneof"]["oneOf"][1]["properties"]["nested"] == build_ref(
            spec, "schema", "OneOfSchema"
        )
        assert props["anyof"]["anyOf"][0] == build_ref(spec, "schema", "AnyOfSchema")
        assert props["anyof"]["anyOf"][1]["properties"]["nested"] == build_ref(
            spec, "schema", "AnyOfSchema"
        )
        assert props["not"] == build_ref(spec, "schema", "NotSchema")
        assert props["deep_not"]["properties"]["nested"] == build_ref(
            spec, "schema", "DeepNotSchema"
        )


@pytest.fixture(params=("2.0", "3.0.0"))
def spec(request):
    openapi_version = request.param
    if openapi_version == "2.0":
        security_kwargs = {"security": [{"apiKey": []}]}
    else:
        security_kwargs = {
            "components": {
                "securitySchemes": {
                    "bearerAuth": dict(type="http", scheme="bearer", bearerFormat="JWT")
                },
                "schemas": {
                    "ErrorResponse": {
                        "type": "object",
                        "properties": {
                            "ok": {
                                "type": "boolean",
                                "description": "status indicator",
                                "example": False,
                            }
                        },
                        "required": ["ok"],
                    }
                },
            }
        }
    return APISpec(
        title="Swagger Petstore",
        version="1.0.0",
        openapi_version=openapi_version,
        info={"description": description},
        **security_kwargs,
    )


class TestAPISpecInit:
    def test_raises_wrong_apispec_version(self):
        message = "Not a valid OpenAPI version number:"
        with pytest.raises(APISpecError, match=message):
            APISpec(
                "Swagger Petstore",
                version="1.0.0",
                openapi_version="4.0",  # 4.0 is not supported
                info={"description": description},
                security=[{"apiKey": []}],
            )


class TestMetadata:
    def test_openapi_metadata(self, spec):
        metadata = spec.to_dict()
        assert metadata["info"]["title"] == "Swagger Petstore"
        assert metadata["info"]["version"] == "1.0.0"
        assert metadata["info"]["description"] == description
        if spec.openapi_version.major < 3:
            assert metadata["swagger"] == str(spec.openapi_version)
            assert metadata["security"] == [{"apiKey": []}]
        else:
            assert metadata["openapi"] == str(spec.openapi_version)
            security_schemes = {
                "bearerAuth": dict(type="http", scheme="bearer", bearerFormat="JWT")
            }
            assert metadata["components"]["securitySchemes"] == security_schemes
            assert metadata["components"]["schemas"].get("ErrorResponse", False)
            assert metadata["info"]["title"] == "Swagger Petstore"
            assert metadata["info"]["version"] == "1.0.0"
            assert metadata["info"]["description"] == description

    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_openapi_metadata_merge_v3(self, spec):
        properties = {
            "ok": {
                "type": "boolean",
                "description": "property description",
                "example": True,
            }
        }
        spec.components.schema(
            "definition", {"properties": properties, "description": "description"}
        )
        metadata = spec.to_dict()
        assert metadata["components"]["schemas"].get("ErrorResponse", False)
        assert metadata["components"]["schemas"].get("definition", False)


class TestTags:

    tag = {
        "name": "MyTag",
        "description": "This tag gathers all API endpoints which are mine.",
    }

    def test_tag(self, spec):
        spec.tag(self.tag)
        tags_json = spec.to_dict()["tags"]
        assert self.tag in tags_json

    def test_tag_is_chainable(self, spec):
        spec.tag({"name": "tag1"}).tag({"name": "tag2"})
        assert spec.to_dict()["tags"] == [{"name": "tag1"}, {"name": "tag2"}]


class TestComponents(RefsSchemaTestMixin):

    properties = {
        "id": {"type": "integer", "format": "int64"},
        "name": {"type": "string", "example": "doggie"},
    }

    def test_schema(self, spec):
        spec.components.schema("Pet", {"properties": self.properties})
        schemas = get_schemas(spec)
        assert "Pet" in schemas
        assert schemas["Pet"]["properties"] == self.properties

    def test_schema_is_chainable(self, spec):
        spec.components.schema("Pet", {"properties": {}}).schema(
            "Plant", {"properties": {}}
        )
        schemas = get_schemas(spec)
        assert "Pet" in schemas
        assert "Plant" in schemas

    def test_schema_description(self, spec):
        model_description = "An animal which lives with humans."
        spec.components.schema(
            "Pet", {"properties": self.properties, "description": model_description}
        )
        schemas = get_schemas(spec)
        assert schemas["Pet"]["description"] == model_description

    def test_schema_stores_enum(self, spec):
        enum = ["name", "photoUrls"]
        spec.components.schema("Pet", {"properties": self.properties, "enum": enum})
        schemas = get_schemas(spec)
        assert schemas["Pet"]["enum"] == enum

    def test_schema_discriminator(self, spec):
        spec.components.schema(
            "Pet", {"properties": self.properties, "discriminator": "name"}
        )
        schemas = get_schemas(spec)
        assert schemas["Pet"]["discriminator"] == "name"

    def test_schema_duplicate_name(self, spec):
        spec.components.schema("Pet", {"properties": self.properties})
        with pytest.raises(
            DuplicateComponentNameError,
            match='Another schema with name "Pet" is already registered.',
        ):
            spec.components.schema("Pet", properties=self.properties)

    def test_response(self, spec):
        response = {"description": "Pet not found"}
        spec.components.response("NotFound", response)
        responses = get_responses(spec)
        assert responses["NotFound"] == response

    def test_response_is_chainable(self, spec):
        spec.components.response("resp1").response("resp2")
        responses = get_responses(spec)
        assert "resp1" in responses
        assert "resp2" in responses

    def test_response_duplicate_name(self, spec):
        spec.components.response("test_response")
        with pytest.raises(
            DuplicateComponentNameError,
            match='Another response with name "test_response" is already registered.',
        ):
            spec.components.response("test_response")

    def test_parameter(self, spec):
        # Note: this is an OpenAPI v2 parameter header
        # but is does the job for the test even for OpenAPI v3
        parameter = {"format": "int64", "type": "integer"}
        spec.components.parameter("PetId", "path", parameter)
        params = get_parameters(spec)
        assert params["PetId"] == {
            "format": "int64",
            "type": "integer",
            "in": "path",
            "name": "PetId",
            "required": True,
        }

    def test_parameter_is_chainable(self, spec):
        spec.components.parameter("param1", "path").parameter("param2", "path")
        params = get_parameters(spec)
        assert "param1" in params
        assert "param2" in params

    def test_parameter_duplicate_name(self, spec):
        spec.components.parameter("test_parameter", "path")
        with pytest.raises(
            DuplicateComponentNameError,
            match='Another parameter with name "test_parameter" is already registered.',
        ):
            spec.components.parameter("test_parameter", "path")

    # Referenced headers are only supported in OAS 3.x
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_header(self, spec):
        header = {"schema": {"type": "string"}}
        spec.components.header("test_header", header.copy())
        headers = get_headers(spec)
        assert headers["test_header"] == header

    # Referenced headers are only supported in OAS 3.x
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_header_is_chainable(self, spec):
        header = {"schema": {"type": "string"}}
        spec.components.header("header1", header).header("header2", header)
        headers = get_headers(spec)
        assert "header1" in headers
        assert "header2" in headers

    # Referenced headers are only supported in OAS 3.x
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_header_duplicate_name(self, spec):
        spec.components.header("test_header", {"schema": {"type": "string"}})
        with pytest.raises(
            DuplicateComponentNameError,
            match='Another header with name "test_header" is already registered.',
        ):
            spec.components.header("test_header", {"schema": {"type": "integer"}})

    # Referenced examples are only supported in OAS 3.x
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_example(self, spec):
        spec.components.example("test_example", {"value": {"a": "b"}})
        examples = get_examples(spec)
        assert examples["test_example"]["value"] == {"a": "b"}

    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_example_is_chainable(self, spec):
        spec.components.example("test_example_1", {}).example("test_example_2", {})
        examples = get_examples(spec)
        assert "test_example_1" in examples
        assert "test_example_2" in examples

    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_example_duplicate_name(self, spec):
        spec.components.example("test_example", {})
        with pytest.raises(
            DuplicateComponentNameError,
            match='Another example with name "test_example" is already registered.',
        ):
            spec.components.example("test_example", {})

    def test_security_scheme(self, spec):
        sec_scheme = {"type": "apiKey", "in": "header", "name": "X-API-Key"}
        spec.components.security_scheme("ApiKeyAuth", sec_scheme)
        assert get_security_schemes(spec)["ApiKeyAuth"] == sec_scheme

    def test_security_scheme_is_chainable(self, spec):
        spec.components.security_scheme("sec_1", {}).security_scheme("sec_2", {})
        security_schemes = get_security_schemes(spec)
        assert "sec_1" in security_schemes
        assert "sec_2" in security_schemes

    def test_security_scheme_duplicate_name(self, spec):
        sec_scheme_1 = {"type": "apiKey", "in": "header", "name": "X-API-Key"}
        sec_scheme_2 = {"type": "apiKey", "in": "header", "name": "X-API-Key-2"}
        spec.components.security_scheme("ApiKeyAuth", sec_scheme_1)
        with pytest.raises(
            DuplicateComponentNameError,
            match='Another security scheme with name "ApiKeyAuth" is already registered.',
        ):
            spec.components.security_scheme("ApiKeyAuth", sec_scheme_2)

    def test_to_yaml(self, spec):
        enum = ["name", "photoUrls"]
        spec.components.schema("Pet", properties=self.properties, enum=enum)
        assert spec.to_dict() == yaml.safe_load(spec.to_yaml())

    def test_components_can_be_accessed_by_plugin_in_init_spec(self):
        class TestPlugin(BasePlugin):
            def init_spec(self, spec):
                spec.components.schema(
                    "TestSchema",
                    {"properties": {"key": {"type": "string"}}, "type": "object"},
                )

        spec = APISpec(
            "Test API", version="0.0.1", openapi_version="2.0", plugins=[TestPlugin()]
        )
        assert get_schemas(spec) == {
            "TestSchema": {"properties": {"key": {"type": "string"}}, "type": "object"}
        }

    def test_components_resolve_refs_in_schema(self, spec):
        spec.components.schema("refs_schema", copy.deepcopy(self.REFS_SCHEMA))
        self.assert_schema_refs(spec, get_schemas(spec)["refs_schema"])

    def test_components_resolve_response_schema(self, spec):
        schema = {"schema": "PetSchema"}
        if spec.openapi_version.major >= 3:
            schema = {"content": {"application/json": schema}}
        spec.components.response("Response", schema)
        resp = get_responses(spec)["Response"]
        if spec.openapi_version.major < 3:
            schema = resp["schema"]
        else:
            schema = resp["content"]["application/json"]["schema"]
        assert schema == build_ref(spec, "schema", "PetSchema")

    # "headers" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_components_resolve_response_header(self, spec):
        response = {"headers": {"header_1": "Header_1"}}
        spec.components.response("Response", response)
        resp = get_responses(spec)["Response"]
        header_1 = resp["headers"]["header_1"]
        assert header_1 == build_ref(spec, "header", "Header_1")

    # "headers" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_components_resolve_response_header_schema(self, spec):
        response = {"headers": {"header_1": {"name": "Pet", "schema": "PetSchema"}}}
        spec.components.response("Response", response)
        resp = get_responses(spec)["Response"]
        header_1 = resp["headers"]["header_1"]
        assert header_1["schema"] == build_ref(spec, "schema", "PetSchema")

    # "headers" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_components_resolve_response_header_examples(self, spec):
        response = {
            "headers": {
                "header_1": {"name": "Pet", "examples": {"example_1": "Example_1"}}
            }
        }
        spec.components.response("Response", response)
        resp = get_responses(spec)["Response"]
        header_1 = resp["headers"]["header_1"]
        assert header_1["examples"]["example_1"] == build_ref(
            spec, "example", "Example_1"
        )

    # "examples" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_components_resolve_response_examples(self, spec):
        response = {
            "content": {"application/json": {"examples": {"example_1": "Example_1"}}}
        }
        spec.components.response("Response", response)
        resp = get_responses(spec)["Response"]
        example_1 = resp["content"]["application/json"]["examples"]["example_1"]
        assert example_1 == build_ref(spec, "example", "Example_1")

    def test_components_resolve_refs_in_response_schema(self, spec):
        schema = copy.deepcopy(self.REFS_SCHEMA)
        if spec.openapi_version.major >= 3:
            response = {"content": {"application/json": {"schema": schema}}}
        else:
            response = {"schema": schema}
        spec.components.response("Response", response)
        resp = get_responses(spec)["Response"]
        if spec.openapi_version.major < 3:
            schema = resp["schema"]
        else:
            schema = resp["content"]["application/json"]["schema"]
        self.assert_schema_refs(spec, schema)

    # "headers" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_components_resolve_refs_in_response_header_schema(self, spec):
        header = {"schema": copy.deepcopy(self.REFS_SCHEMA)}
        response = {"headers": {"header": header}}
        spec.components.response("Response", response)
        resp = get_responses(spec)["Response"]
        self.assert_schema_refs(spec, resp["headers"]["header"]["schema"])

    # "examples" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_components_resolve_parameter_examples(self, spec):
        parameter = {
            "examples": {"example_1": "Example_1"},
        }
        spec.components.parameter("param", "path", parameter)
        param = get_parameters(spec)["param"]
        example_1 = param["examples"]["example_1"]
        assert example_1 == build_ref(spec, "example", "Example_1")

    def test_components_resolve_parameter_schemas(self, spec):
        parameter = {"schema": "PetSchema"}
        spec.components.parameter("param", "path", parameter)
        param = get_parameters(spec)["param"]
        assert param["schema"] == build_ref(spec, "schema", "PetSchema")

    def test_components_resolve_refs_in_parameter_schema(self, spec):
        parameter = {"schema": copy.deepcopy(self.REFS_SCHEMA)}
        spec.components.parameter("param", "path", parameter)
        self.assert_schema_refs(spec, get_parameters(spec)["param"]["schema"])

    # "headers" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_components_resolve_header_schema(self, spec):
        header = {"name": "Pet", "schema": "PetSchema"}
        spec.components.header("header", header)
        header = get_headers(spec)["header"]
        assert header["schema"] == build_ref(spec, "schema", "PetSchema")

    # "headers" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_components_resolve_header_examples(self, spec):
        header = {"name": "Pet", "examples": {"example_1": "Example_1"}}
        spec.components.header("header", header)
        header = get_headers(spec)["header"]
        assert header["examples"]["example_1"] == build_ref(
            spec, "example", "Example_1"
        )

    # "headers" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_components_resolve_refs_in_header_schema(self, spec):
        header = {"schema": copy.deepcopy(self.REFS_SCHEMA)}
        spec.components.header("header", header)
        self.assert_schema_refs(spec, get_headers(spec)["header"]["schema"])

    def test_schema_lazy(self, spec):
        spec.components.schema("Pet_1", {"properties": self.properties}, lazy=False)
        spec.components.schema("Pet_2", {"properties": self.properties}, lazy=True)
        schemas = get_schemas(spec)
        assert "Pet_1" in schemas
        assert "Pet_2" not in schemas
        spec.components.schema("PetFriend", {"oneOf": ["Pet_1", "Pet_2"]})
        schemas = get_schemas(spec)
        assert "Pet_2" in schemas
        assert schemas["Pet_2"]["properties"] == self.properties

    def test_response_lazy(self, spec):
        response_1 = {"description": "Reponse 1"}
        response_2 = {"description": "Reponse 2"}
        spec.components.response("Response_1", response_1, lazy=False)
        spec.components.response("Response_2", response_2, lazy=True)
        responses = get_responses(spec)
        assert "Response_1" in responses
        assert "Response_2" not in responses
        spec.path("/path", operations={"get": {"responses": {"200": "Response_2"}}})
        responses = get_responses(spec)
        assert "Response_2" in responses

    def test_parameter_lazy(self, spec):
        parameter = {"format": "int64", "type": "integer"}
        spec.components.parameter("Param_1", "path", parameter, lazy=False)
        spec.components.parameter("Param_2", "path", parameter, lazy=True)
        params = get_parameters(spec)
        assert "Param_1" in params
        assert "Param_2" not in params
        spec.path("/path", operations={"get": {"parameters": ["Param_1", "Param_2"]}})
        assert "Param_2" in params

    # Referenced headers are only supported in OAS 3.x
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_header_lazy(self, spec):
        header = {"schema": {"type": "string"}}
        spec.components.header("Header_1", header, lazy=False)
        spec.components.header("Header_2", header, lazy=True)
        headers = get_headers(spec)
        assert "Header_1" in headers
        assert "Header_2" not in headers
        spec.path(
            "/path",
            operations={
                "get": {"responses": {"200": {"headers": {"header_2": "Header_2"}}}}
            },
        )
        assert "Header_2" in headers

    # Referenced examples are only supported in OAS 3.x
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_example_lazy(self, spec):
        spec.components.example("Example_1", {"value": {"a": "b"}}, lazy=False)
        spec.components.example("Example_2", {"value": {"a": "b"}}, lazy=True)
        examples = get_examples(spec)
        assert "Example_1" in examples
        assert "Example_2" not in examples
        spec.path(
            "/path",
            operations={
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "examples": {"example_2": "Example_2"}
                                }
                            }
                        }
                    }
                }
            },
        )
        assert "Example_2" in examples


class TestPath(RefsSchemaTestMixin):
    paths = {
        "/pet/{petId}": {
            "get": {
                "parameters": [
                    {
                        "required": True,
                        "format": "int64",
                        "name": "petId",
                        "in": "path",
                        "type": "integer",
                        "description": "ID of pet that needs to be fetched",
                    }
                ],
                "responses": {
                    "200": {"description": "successful operation"},
                    "400": {"description": "Invalid ID supplied"},
                    "404": {"description": "Pet not found"},
                },
                "produces": ["application/json", "application/xml"],
                "operationId": "getPetById",
                "summary": "Find pet by ID",
                "description": (
                    "Returns a pet when ID < 10.  "
                    "ID > 10 or nonintegers will simulate API error conditions"
                ),
                "tags": ["pet"],
            }
        }
    }

    def test_path(self, spec):
        route_spec = self.paths["/pet/{petId}"]["get"]
        spec.path(
            path="/pet/{petId}",
            operations=dict(
                get=dict(
                    parameters=route_spec["parameters"],
                    responses=route_spec["responses"],
                    produces=route_spec["produces"],
                    operationId=route_spec["operationId"],
                    summary=route_spec["summary"],
                    description=route_spec["description"],
                    tags=route_spec["tags"],
                )
            ),
        )

        p = get_paths(spec)["/pet/{petId}"]["get"]
        assert p["parameters"] == route_spec["parameters"]
        assert p["responses"] == route_spec["responses"]
        assert p["operationId"] == route_spec["operationId"]
        assert p["summary"] == route_spec["summary"]
        assert p["description"] == route_spec["description"]
        assert p["tags"] == route_spec["tags"]

    def test_paths_maintain_order(self, spec):
        spec.path(path="/path1")
        spec.path(path="/path2")
        spec.path(path="/path3")
        spec.path(path="/path4")
        assert list(spec.to_dict()["paths"].keys()) == [
            "/path1",
            "/path2",
            "/path3",
            "/path4",
        ]

    def test_path_is_chainable(self, spec):
        spec.path(path="/path1").path("/path2")
        assert list(spec.to_dict()["paths"].keys()) == ["/path1", "/path2"]

    def test_path_methods_maintain_order(self, spec):
        methods = ["get", "post", "put", "patch", "delete", "head", "options"]
        for method in methods:
            spec.path(path="/path", operations={method: {}})
        assert list(spec.to_dict()["paths"]["/path"]) == methods

    def test_path_merges_paths(self, spec):
        """Test that adding a second HTTP method to an existing path performs
        a merge operation instead of an overwrite"""
        path = "/pet/{petId}"
        route_spec = self.paths[path]["get"]
        spec.path(path=path, operations=dict(get=route_spec))
        spec.path(
            path=path,
            operations=dict(
                put=dict(
                    parameters=route_spec["parameters"],
                    responses=route_spec["responses"],
                    produces=route_spec["produces"],
                    operationId="updatePet",
                    summary="Updates an existing Pet",
                    description="Use this method to make changes to Pet `petId`",
                    tags=route_spec["tags"],
                )
            ),
        )

        p = get_paths(spec)[path]
        assert "get" in p
        assert "put" in p

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.0"))
    def test_path_called_twice_with_same_operations_parameters(self, openapi_version):
        """Test calling path twice with same operations or parameters

        operations and parameters being mutated by clean_operations and plugin helpers
        should not make path fail on second call
        """

        class TestPlugin(BasePlugin):
            def path_helper(self, path, operations, parameters, **kwargs):
                """Mutate operations and parameters"""
                operations.update({"post": {"responses": {"201": "201ResponseRef"}}})
                parameters.append("ParamRef_3")
                return path

        spec = APISpec(
            title="Swagger Petstore",
            version="1.0.0",
            openapi_version=openapi_version,
            plugins=[TestPlugin()],
        )

        path = "/pet/{petId}"
        parameters = ["ParamRef_1"]
        operation = {
            "parameters": ["ParamRef_2"],
            "responses": {"200": "200ResponseRef"},
        }

        spec.path(path=path, operations={"get": operation}, parameters=parameters)
        spec.path(path=path, operations={"put": operation}, parameters=parameters)
        operations = (get_paths(spec))[path]
        assert (
            operations["get"]
            == operations["put"]
            == {
                "parameters": [build_ref(spec, "parameter", "ParamRef_2")],
                "responses": {"200": build_ref(spec, "response", "200ResponseRef")},
            }
        )
        assert operations["parameters"] == [
            build_ref(spec, "parameter", "ParamRef_1"),
            build_ref(spec, "parameter", "ParamRef_3"),
        ]

    def test_path_ensures_path_parameters_required(self, spec):
        path = "/pet/{petId}"
        spec.path(
            path=path,
            operations=dict(put=dict(parameters=[{"name": "petId", "in": "path"}])),
        )
        assert get_paths(spec)[path]["put"]["parameters"][0]["required"] is True

    def test_path_with_no_path_raises_error(self, spec):
        message = "Path template is not specified"
        with pytest.raises(APISpecError, match=message):
            spec.path()

    def test_path_summary_description(self, spec):
        summary = "Operations on a Pet"
        description = "Operations on a Pet identified by its ID"
        spec.path(path="/pet/{petId}", summary=summary, description=description)

        p = get_paths(spec)["/pet/{petId}"]
        assert p["summary"] == summary
        assert p["description"] == description

    def test_path_resolves_parameter(self, spec):
        route_spec = self.paths["/pet/{petId}"]["get"]
        spec.components.parameter("test_parameter", "path", route_spec["parameters"][0])
        spec.path(
            path="/pet/{petId}", operations={"get": {"parameters": ["test_parameter"]}}
        )
        p = get_paths(spec)["/pet/{petId}"]["get"]
        assert p["parameters"][0] == build_ref(spec, "parameter", "test_parameter")

    @pytest.mark.parametrize(
        "parameters",
        ([{"name": "petId"}], [{"in": "path"}]),  # missing "in"  # missing "name"
    )
    def test_path_invalid_parameter(self, spec, parameters):
        path = "/pet/{petId}"

        with pytest.raises(InvalidParameterError):
            spec.path(path=path, operations=dict(put={}, get={}), parameters=parameters)

    def test_parameter_duplicate(self, spec):
        spec.path(
            path="/pet/{petId}",
            operations={
                "get": {
                    "parameters": [
                        {"name": "petId", "in": "path"},
                        {"name": "petId", "in": "query"},
                    ]
                }
            },
        )

        with pytest.raises(DuplicateParameterError):
            spec.path(
                path="/pet/{petId}",
                operations={
                    "get": {
                        "parameters": [
                            {"name": "petId", "in": "path"},
                            {"name": "petId", "in": "path"},
                        ]
                    }
                },
            )

    def test_global_parameters(self, spec):
        path = "/pet/{petId}"
        route_spec = self.paths["/pet/{petId}"]["get"]

        spec.components.parameter("test_parameter", "path", route_spec["parameters"][0])
        spec.path(
            path=path,
            operations=dict(put={}, get={}),
            parameters=[{"name": "petId", "in": "path"}, "test_parameter"],
        )

        assert get_paths(spec)[path]["parameters"] == [
            {"name": "petId", "in": "path", "required": True},
            build_ref(spec, "parameter", "test_parameter"),
        ]

    def test_global_parameter_duplicate(self, spec):
        path = "/pet/{petId}"
        spec.path(
            path=path,
            operations=dict(put={}, get={}),
            parameters=[
                {"name": "petId", "in": "path"},
                {"name": "petId", "in": "query"},
            ],
        )

        assert get_paths(spec)[path]["parameters"] == [
            {"name": "petId", "in": "path", "required": True},
            {"name": "petId", "in": "query"},
        ]

        with pytest.raises(DuplicateParameterError):
            spec.path(
                path=path,
                operations=dict(put={}, get={}),
                parameters=[
                    {"name": "petId", "in": "path"},
                    {"name": "petId", "in": "path"},
                    "test_parameter",
                ],
            )

    def test_path_resolves_response(self, spec):
        route_spec = self.paths["/pet/{petId}"]["get"]
        spec.components.response("test_response", route_spec["responses"]["200"])
        spec.path(
            path="/pet/{petId}",
            operations={"get": {"responses": {"200": "test_response"}}},
        )
        p = get_paths(spec)["/pet/{petId}"]["get"]
        assert p["responses"]["200"] == build_ref(spec, "response", "test_response")

    def test_path_response_with_HTTPStatus_code(self, spec):
        code = HTTPStatus(200)
        spec.path(
            path="/pet/{petId}",
            operations={"get": {"responses": {code: "test_response"}}},
        )

        assert "200" in get_paths(spec)["/pet/{petId}"]["get"]["responses"]

    def test_path_response_with_status_code_range(self, spec, recwarn):
        status_code = "2XX"

        spec.path(
            path="/pet/{petId}",
            operations={"get": {"responses": {status_code: "test_response"}}},
        )

        if spec.openapi_version.major < 3:
            assert len(recwarn) == 1
            assert recwarn.pop(UserWarning)

        assert status_code in get_paths(spec)["/pet/{petId}"]["get"]["responses"]

    def test_path_check_invalid_http_method(self, spec):
        spec.path("/pet/{petId}", operations={"get": {}})
        spec.path("/pet/{petId}", operations={"x-dummy": {}})
        message = "One or more HTTP methods are invalid"
        with pytest.raises(APISpecError, match=message):
            spec.path("/pet/{petId}", operations={"dummy": {}})

    def test_path_resolve_response_schema(self, spec):
        schema = {"schema": "PetSchema"}
        if spec.openapi_version.major >= 3:
            schema = {"content": {"application/json": schema}}
        spec.path("/pet/{petId}", operations={"get": {"responses": {"200": schema}}})
        resp = get_paths(spec)["/pet/{petId}"]["get"]["responses"]["200"]
        if spec.openapi_version.major < 3:
            schema = resp["schema"]
        else:
            schema = resp["content"]["application/json"]["schema"]
        assert schema == build_ref(spec, "schema", "PetSchema")

    # requestBody only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_path_resolve_request_body(self, spec):
        spec.path(
            "/pet/{petId}",
            operations={
                "get": {
                    "requestBody": {
                        "content": {"application/json": {"schema": "PetSchema"}}
                    }
                }
            },
        )
        assert get_paths(spec)["/pet/{petId}"]["get"]["requestBody"]["content"][
            "application/json"
        ]["schema"] == build_ref(spec, "schema", "PetSchema")

    # "headers" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_path_resolve_response_header(self, spec):
        response = {"headers": {"header_1": "Header_1"}}
        spec.path("/pet/{petId}", operations={"get": {"responses": {"200": response}}})
        resp = get_paths(spec)["/pet/{petId}"]["get"]["responses"]["200"]
        header_1 = resp["headers"]["header_1"]
        assert header_1 == build_ref(spec, "header", "Header_1")

    # "headers" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_path_resolve_response_header_schema(self, spec):
        response = {"headers": {"header_1": {"name": "Pet", "schema": "PetSchema"}}}
        spec.path("/pet/{petId}", operations={"get": {"responses": {"200": response}}})
        resp = get_paths(spec)["/pet/{petId}"]["get"]["responses"]["200"]
        header_1 = resp["headers"]["header_1"]
        assert header_1["schema"] == build_ref(spec, "schema", "PetSchema")

    # "headers" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_path_resolve_response_header_examples(self, spec):
        response = {
            "headers": {
                "header_1": {"name": "Pet", "examples": {"example_1": "Example_1"}}
            }
        }
        spec.path("/pet/{petId}", operations={"get": {"responses": {"200": response}}})
        resp = get_paths(spec)["/pet/{petId}"]["get"]["responses"]["200"]
        header_1 = resp["headers"]["header_1"]
        assert header_1["examples"]["example_1"] == build_ref(
            spec, "example", "Example_1"
        )

    # "examples" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_path_resolve_response_examples(self, spec):
        response = {
            "content": {"application/json": {"examples": {"example_1": "Example_1"}}}
        }
        spec.path("/pet/{petId}", operations={"get": {"responses": {"200": response}}})
        resp = get_paths(spec)["/pet/{petId}"]["get"]["responses"]["200"]
        example_1 = resp["content"]["application/json"]["examples"]["example_1"]
        assert example_1 == build_ref(spec, "example", "Example_1")

    # "examples" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_path_resolve_request_body_examples(self, spec):
        request_body = {
            "content": {"application/json": {"examples": {"example_1": "Example_1"}}}
        }
        spec.path("/pet/{petId}", operations={"get": {"requestBody": request_body}})
        reqbdy = get_paths(spec)["/pet/{petId}"]["get"]["requestBody"]
        example_1 = reqbdy["content"]["application/json"]["examples"]["example_1"]
        assert example_1 == build_ref(spec, "example", "Example_1")

    # "examples" components section only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_path_resolve_parameter_examples(self, spec):
        parameter = {
            "name": "test",
            "in": "query",
            "examples": {"example_1": "Example_1"},
        }
        spec.path("/pet/{petId}", operations={"get": {"parameters": [parameter]}})
        param = get_paths(spec)["/pet/{petId}"]["get"]["parameters"][0]
        example_1 = param["examples"]["example_1"]
        assert example_1 == build_ref(spec, "example", "Example_1")

    def test_path_resolve_parameter_schemas(self, spec):
        parameter = {"name": "test", "in": "query", "schema": "PetSchema"}
        spec.path("/pet/{petId}", operations={"get": {"parameters": [parameter]}})
        param = get_paths(spec)["/pet/{petId}"]["get"]["parameters"][0]
        assert param["schema"] == build_ref(spec, "schema", "PetSchema")

    def test_path_resolve_refs_in_response_schema(self, spec):
        if spec.openapi_version.major >= 3:
            schema = {"content": {"application/json": {"schema": self.REFS_SCHEMA}}}
        else:
            schema = {"schema": self.REFS_SCHEMA}
        spec.path("/pet/{petId}", operations={"get": {"responses": {"200": schema}}})
        resp = get_paths(spec)["/pet/{petId}"]["get"]["responses"]["200"]
        if spec.openapi_version.major < 3:
            schema = resp["schema"]
        else:
            schema = resp["content"]["application/json"]["schema"]
        self.assert_schema_refs(spec, schema)

    def test_path_resolve_refs_in_parameter_schema(self, spec):
        schema = copy.copy({"schema": self.REFS_SCHEMA})
        schema["in"] = "query"
        schema["name"] = "test"
        spec.path("/pet/{petId}", operations={"get": {"parameters": [schema]}})
        schema = get_paths(spec)["/pet/{petId}"]["get"]["parameters"][0]["schema"]
        self.assert_schema_refs(spec, schema)

    # requestBody only exists in OAS 3
    @pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
    def test_path_resolve_refs_in_request_body_schema(self, spec):
        schema = {"content": {"application/json": {"schema": self.REFS_SCHEMA}}}
        spec.path("/pet/{petId}", operations={"get": {"responses": {"200": schema}}})
        resp = get_paths(spec)["/pet/{petId}"]["get"]["responses"]["200"]
        schema = resp["content"]["application/json"]["schema"]
        self.assert_schema_refs(spec, schema)


class TestPlugins:
    @staticmethod
    def test_plugin_factory(return_none=False):
        class TestPlugin(BasePlugin):
            """Test Plugin

            return_none allows to check plugin helpers returning ``None``
            Inputs are mutated to allow testing only a copy is passed.
            """

            def schema_helper(self, name, definition, **kwargs):
                definition.pop("dummy", None)
                if not return_none:
                    return {"properties": {"name": {"type": "string"}}}

            def parameter_helper(self, parameter, **kwargs):
                parameter.pop("dummy", None)
                if not return_none:
                    return {"description": "some parameter"}

            def response_helper(self, response, **kwargs):
                response.pop("dummy", None)
                if not return_none:
                    return {"description": "42"}

            def header_helper(self, header, **kwargs):
                header.pop("dummy", None)
                if not return_none:
                    return {"description": "some header"}

            def path_helper(self, path, operations, parameters, **kwargs):
                if not return_none:
                    if path == "/path_1":
                        operations.update({"get": {"responses": {"200": {}}}})
                        parameters.append({"name": "page", "in": "query"})
                        return "/path_1_modified"

            def operation_helper(self, path, operations, **kwargs):
                if path == "/path_2":
                    operations["post"] = {"responses": {"201": {}}}

        return TestPlugin()

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.0"))
    @pytest.mark.parametrize("return_none", (True, False))
    def test_plugin_schema_helper_is_used(self, openapi_version, return_none):
        spec = APISpec(
            title="Swagger Petstore",
            version="1.0.0",
            openapi_version=openapi_version,
            plugins=(self.test_plugin_factory(return_none),),
        )
        schema = {"dummy": "dummy"}
        spec.components.schema("Pet", schema)
        definitions = get_schemas(spec)
        if return_none:
            assert definitions["Pet"] == {}
        else:
            assert definitions["Pet"] == {"properties": {"name": {"type": "string"}}}
        # Check original schema is not modified
        assert schema == {"dummy": "dummy"}

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.0"))
    @pytest.mark.parametrize("return_none", (True, False))
    def test_plugin_parameter_helper_is_used(self, openapi_version, return_none):
        spec = APISpec(
            title="Swagger Petstore",
            version="1.0.0",
            openapi_version=openapi_version,
            plugins=(self.test_plugin_factory(return_none),),
        )
        parameter = {"dummy": "dummy"}
        spec.components.parameter("Pet", "body", parameter)
        parameters = get_parameters(spec)
        if return_none:
            assert parameters["Pet"] == {"in": "body", "name": "Pet"}
        else:
            assert parameters["Pet"] == {
                "in": "body",
                "name": "Pet",
                "description": "some parameter",
            }
        # Check original parameter is not modified
        assert parameter == {"dummy": "dummy"}

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.0"))
    @pytest.mark.parametrize("return_none", (True, False))
    def test_plugin_response_helper_is_used(self, openapi_version, return_none):
        spec = APISpec(
            title="Swagger Petstore",
            version="1.0.0",
            openapi_version=openapi_version,
            plugins=(self.test_plugin_factory(return_none),),
        )
        response = {"dummy": "dummy"}
        spec.components.response("Pet", response)
        responses = get_responses(spec)
        if return_none:
            assert responses["Pet"] == {}
        else:
            assert responses["Pet"] == {"description": "42"}
        # Check original response is not modified
        assert response == {"dummy": "dummy"}

    @pytest.mark.parametrize("openapi_version", ("3.0.0",))
    @pytest.mark.parametrize("return_none", (True, False))
    def test_plugin_header_helper_is_used(self, openapi_version, return_none):
        spec = APISpec(
            title="Swagger Petstore",
            version="1.0.0",
            openapi_version=openapi_version,
            plugins=(self.test_plugin_factory(return_none),),
        )
        header = {"dummy": "dummy"}
        spec.components.header("Pet", header)
        headers = get_headers(spec)
        if return_none:
            assert headers["Pet"] == {}
        else:
            assert headers["Pet"] == {
                "description": "some header",
            }
        # Check original header is not modified
        assert header == {"dummy": "dummy"}

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.0"))
    @pytest.mark.parametrize("return_none", (True, False))
    def test_plugin_path_helper_is_used(self, openapi_version, return_none):
        spec = APISpec(
            title="Swagger Petstore",
            version="1.0.0",
            openapi_version=openapi_version,
            plugins=(self.test_plugin_factory(return_none),),
        )
        spec.path("/path_1")
        paths = get_paths(spec)
        assert len(paths) == 1
        if return_none:
            assert paths["/path_1"] == {}
        else:
            assert paths["/path_1_modified"] == {
                "get": {"responses": {"200": {}}},
                "parameters": [{"in": "query", "name": "page"}],
            }

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.0"))
    def test_plugin_operation_helper_is_used(self, openapi_version):
        spec = APISpec(
            title="Swagger Petstore",
            version="1.0.0",
            openapi_version=openapi_version,
            plugins=(self.test_plugin_factory(),),
        )
        spec.path("/path_2", operations={"post": {"responses": {"200": {}}}})
        paths = get_paths(spec)
        assert len(paths) == 1
        assert paths["/path_2"] == {"post": {"responses": {"201": {}}}}


class TestPluginsOrder:
    class OrderedPlugin(BasePlugin):
        def __init__(self, index, output):
            super(TestPluginsOrder.OrderedPlugin, self).__init__()
            self.index = index
            self.output = output

        def path_helper(self, path, operations, **kwargs):
            self.output.append(f"plugin_{self.index}_path")

        def operation_helper(self, path, operations, **kwargs):
            self.output.append(f"plugin_{self.index}_operations")

    def test_plugins_order(self):
        """Test plugins execution order in APISpec.path

        - All path helpers are called, then all operation helpers, then all response helpers.
        - At each step, helpers are executed in the order the plugins are passed to APISpec.
        """
        output = []
        spec = APISpec(
            title="Swagger Petstore",
            version="1.0.0",
            openapi_version="3.0.0",
            plugins=(self.OrderedPlugin(1, output), self.OrderedPlugin(2, output)),
        )
        spec.path("/path", operations={"get": {"responses": {200: {}}}})
        assert output == [
            "plugin_1_path",
            "plugin_2_path",
            "plugin_1_operations",
            "plugin_2_operations",
        ]
