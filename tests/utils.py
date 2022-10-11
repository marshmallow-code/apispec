"""Utilities to get elements of generated spec"""
import json

from apispec.core import APISpec
from apispec import exceptions
from apispec.utils import build_reference


def get_schemas(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["definitions"]
    return spec.to_dict()["components"]["schemas"]


def get_responses(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["responses"]
    return spec.to_dict()["components"]["responses"]


def get_parameters(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["parameters"]
    return spec.to_dict()["components"]["parameters"]


def get_headers(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["headers"]
    return spec.to_dict()["components"]["headers"]


def get_examples(spec):
    return spec.to_dict()["components"]["examples"]


def get_security_schemes(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["securityDefinitions"]
    return spec.to_dict()["components"]["securitySchemes"]


def get_paths(spec):
    return spec.to_dict()["paths"]


def build_ref(spec, component_type, obj):
    return build_reference(component_type, spec.openapi_version.major, obj)


def validate_spec(spec: APISpec) -> bool:
    """Validate the output of an :class:`APISpec` object against the
    OpenAPI specification.

    Note: Requires installing apispec with the ``[validation]`` extras.
    ::

        pip install 'apispec[validation]'

    :raise: apispec.exceptions.OpenAPIError if validation fails.
    """
    try:
        import prance
    except ImportError as error:  # re-raise with a more verbose message
        exc_class = type(error)
        raise exc_class(
            "validate_spec requires prance to be installed. "
            "You can install all validation requirements using:\n"
            "    pip install 'apispec[validation]'"
        ) from error
    parser_kwargs = {}
    if spec.openapi_version.major == 3:
        parser_kwargs["backend"] = "openapi-spec-validator"
    try:
        prance.BaseParser(spec_string=json.dumps(spec.to_dict()), **parser_kwargs)
    except prance.ValidationError as err:
        raise exceptions.OpenAPIError(*err.args) from err
    else:
        return True
