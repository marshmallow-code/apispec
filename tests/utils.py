"""Utilities to get elements of generated spec"""

import openapi_spec_validator
from openapi_spec_validator.exceptions import OpenAPISpecValidatorError

from apispec import exceptions
from apispec.core import APISpec
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

    :raise: apispec.exceptions.OpenAPIError if validation fails.
    """
    try:
        # Coerce to dict to satisfy Pyright
        openapi_spec_validator.validate(dict(spec.to_dict()))
    except OpenAPISpecValidatorError as err:
        raise exceptions.OpenAPIError(*err.args) from err
    else:
        return True
