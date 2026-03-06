import pytest

from apispec.exceptions import APISpecError

from .utils import build_ref, get_paths


@pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
class TestLinksInPath:
    def test_basic_two_element_tuple(self, spec):
        spec.path(
            path="/posts",
            operations={
                "post": {
                    "responses": {
                        "201": {
                            "description": "Created",
                        }
                    }
                }
            },
            links={
                "GetPost": ("/posts/{post_id}", "GET"),
            },
        )
        paths = get_paths(spec)
        post_response = paths["/posts"]["post"]["responses"]["201"]
        assert "links" in post_response
        assert "GetPost" in post_response["links"]
        link = post_response["links"]["GetPost"]
        assert link["operationRef"] == "#/paths/~1posts~1{post_id}/get"
        assert "parameters" not in link

    def test_three_element_tuple_with_parameters(self, spec):
        spec.path(
            path="/posts",
            operations={
                "post": {
                    "responses": {
                        "201": {
                            "description": "Created",
                        }
                    }
                }
            },
            links={
                "GetPost": (
                    "/posts/{post_id}",
                    "GET",
                    {"post_id": "$response.body#/postIdentifier"},
                ),
            },
        )
        paths = get_paths(spec)
        post_response = paths["/posts"]["post"]["responses"]["201"]
        link = post_response["links"]["GetPost"]
        assert link["operationRef"] == "#/paths/~1posts~1{post_id}/get"
        assert link["parameters"] == {"post_id": "$response.body#/postIdentifier"}

    def test_multiple_links_on_single_endpoint(self, spec):
        spec.path(
            path="/users",
            operations={
                "post": {
                    "responses": {
                        "201": {
                            "description": "Created",
                        }
                    }
                }
            },
            links={
                "GetUser": ("/users/{user_id}", "GET"),
                "UpdateUser": ("/users/{user_id}", "PUT"),
                "DeleteUser": ("/users/{user_id}", "DELETE"),
            },
        )
        paths = get_paths(spec)
        post_response = paths["/users"]["post"]["responses"]["201"]
        assert "links" in post_response
        assert len(post_response["links"]) == 3
        assert "GetUser" in post_response["links"]
        assert "UpdateUser" in post_response["links"]
        assert "DeleteUser" in post_response["links"]

    def test_links_added_to_multiple_operations(self, spec):
        spec.path(
            path="/posts",
            operations={
                "get": {
                    "responses": {
                        "200": {"description": "Success"},
                    }
                },
                "post": {
                    "responses": {
                        "201": {"description": "Created"},
                    }
                },
            },
            links={
                "GetPost": ("/posts/{post_id}", "GET"),
            },
        )
        paths = get_paths(spec)
        # Both operations should have the link in their responses
        assert "GetPost" in paths["/posts"]["get"]["responses"]["200"]["links"]
        assert "GetPost" in paths["/posts"]["post"]["responses"]["201"]["links"]

    def test_links_not_shared_between_paths(self, spec):
        spec.path(
            path="/users",
            operations={"post": {"responses": {"201": {"description": "Created"}}}},
            links={"GetUser": ("/users/{user_id}", "GET")},
        )
        spec.path(
            path="/posts",
            operations={"post": {"responses": {"201": {"description": "Created"}}}},
            links={"GetPost": ("/posts/{post_id}", "GET")},
        )
        paths = get_paths(spec)
        # Each path should only have its own links
        assert "GetPost" not in paths["/users"]["post"]["responses"]["201"]["links"]
        assert "GetUser" not in paths["/posts"]["post"]["responses"]["201"]["links"]

    def test_path_escaping_for_json_pointer(self, spec):
        spec.path(
            path="/posts",
            operations={
                "post": {
                    "responses": {
                        "201": {"description": "Created"},
                    }
                }
            },
            links={
                "GetPost": ("/posts/{id}", "GET"),
            },
        )
        paths = get_paths(spec)
        link = paths["/posts"]["post"]["responses"]["201"]["links"]["GetPost"]
        # Forward slashes should be escaped as ~1
        assert link["operationRef"] == "#/paths/~1posts~1{id}/get"

    def test_path_escaping_with_tilde(self, spec):
        spec.path(
            path="/posts",
            operations={
                "post": {
                    "responses": {
                        "201": {"description": "Created"},
                    }
                }
            },
            links={
                "GetItem": ("/items/~special", "GET"),
            },
        )
        paths = get_paths(spec)
        link = paths["/posts"]["post"]["responses"]["201"]["links"]["GetItem"]
        # Tildes should be escaped as ~0, then slashes as ~1
        assert link["operationRef"] == "#/paths/~1items~1~0special/get"

    def test_prefers_operationId_when_target_registered(self, spec):
        """If the target operation is already registered with an operationId,
        the link should use `operationId` instead of `operationRef`.
        """
        # Register the target operation first
        spec.path(
            path="/posts/{post_id}",
            operations={
                "get": {
                    "operationId": "getPost",
                    "responses": {"200": {"description": "Success"}},
                }
            },
        )

        # Add a different path that links to the registered operation
        spec.path(
            path="/comments",
            operations={"post": {"responses": {"201": {"description": "Created"}}}},
            links={"GetPost": ("/posts/{post_id}", "GET")},
        )

        paths = get_paths(spec)
        link = paths["/comments"]["post"]["responses"]["201"]["links"]["GetPost"]
        assert link == {"operationId": "getPost"}


@pytest.mark.parametrize("spec", ("2.0",), indirect=True)
class TestLinksOpenAPI2:
    def test_links_ignored_in_openapi_2(self, spec):
        spec.path(
            path="/posts",
            operations={
                "post": {
                    "responses": {
                        "201": {"description": "Created"},
                    }
                }
            },
            links={
                "GetPost": ("/posts/{post_id}", "GET"),
            },
        )
        paths = get_paths(spec)
        post_response = paths["/posts"]["post"]["responses"]["201"]
        assert "links" not in post_response


@pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
class TestLinksErrorHandling:
    @pytest.mark.parametrize(
        "invalid_tuple",
        [
            ("/posts/{id}",),
            ("/posts/{id}", "GET", {}, "extra"),
        ],
    )
    def test_invalid_tuple_length(self, spec, invalid_tuple):
        with pytest.raises(APISpecError, match="must be a tuple of"):
            spec.path(
                path="/posts",
                operations={"post": {"responses": {"201": {"description": "Created"}}}},
                links={
                    "GetPost": invalid_tuple,
                },
            )

    def test_invalid_tuple_type(self, spec):
        with pytest.raises(APISpecError, match="must be a tuple of"):
            spec.path(
                path="/posts",
                operations={"post": {"responses": {"201": {"description": "Created"}}}},
                links={
                    "GetPost": "/posts/{id}",  # String instead of tuple
                },
            )

    def test_invalid_route_type(self, spec):
        with pytest.raises(APISpecError, match="route must be a string"):
            spec.path(
                path="/posts",
                operations={"post": {"responses": {"201": {"description": "Created"}}}},
                links={
                    "GetPost": (123, "GET"),  # Route is not a string
                },
            )

    def test_invalid_http_method(self, spec):
        with pytest.raises(APISpecError, match="invalid HTTP method"):
            spec.path(
                path="/posts",
                operations={"post": {"responses": {"201": {"description": "Created"}}}},
                links={
                    "GetPost": ("/posts/{id}", "INVALID"),
                },
            )

    def test_case_insensitive_method(self, spec):
        spec.path(
            path="/posts",
            operations={"post": {"responses": {"201": {"description": "Created"}}}},
            links={
                "GetPost": ("/posts/{id}", "GeT"),  # Mixed case
            },
        )
        paths = get_paths(spec)
        link = paths["/posts"]["post"]["responses"]["201"]["links"]["GetPost"]
        # Method should be lowercased in the operationRef
        assert link["operationRef"] == "#/paths/~1posts~1{id}/get"


@pytest.mark.parametrize("spec", ("3.0.0",), indirect=True)
class TestLinksWithReferences:
    def test_link_component_reference_in_response(self, spec):
        # Register a link component
        link_def = {
            "operationRef": "#/paths/~1users~1{user_id}/get",
            "parameters": {"user_id": "$response.body#/id"},
        }
        spec.components.link("GetUserLink", link_def)

        # Use the link as a reference in a response
        spec.path(
            path="/posts",
            operations={
                "post": {
                    "responses": {
                        "201": {
                            "description": "Created",
                            "links": {
                                "GetUser": "GetUserLink",
                            },
                        }
                    }
                }
            },
        )

        paths = get_paths(spec)
        post_response = paths["/posts"]["post"]["responses"]["201"]
        # The reference should be resolved to $ref
        assert post_response["links"]["GetUser"] == build_ref(
            spec, "link", "GetUserLink"
        )

    def test_mixed_direct_and_reference_links(self, spec):
        # Register a link component
        spec.components.link(
            "GetUserLink", {"operationRef": "#/paths/~1users~1{user_id}/get"}
        )

        expected_operation_ref = "#/paths/~1posts~1{id}/get"
        # Use both direct links and references
        spec.path(
            path="/posts",
            operations={
                "post": {
                    "responses": {
                        "201": {
                            "description": "Created",
                            "links": {
                                "GetUser": "GetUserLink",  # Reference
                                "DirectLink": {  # Direct object
                                    "operationRef": expected_operation_ref
                                },
                            },
                        }
                    }
                }
            },
        )

        paths = get_paths(spec)
        post_response = paths["/posts"]["post"]["responses"]["201"]
        # Reference should be $ref
        assert post_response["links"]["GetUser"] == build_ref(
            spec, "link", "GetUserLink"
        )
        # Direct object should remain as is
        assert (
            post_response["links"]["DirectLink"]["operationRef"]
            == expected_operation_ref
        )
