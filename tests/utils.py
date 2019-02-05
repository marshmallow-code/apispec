# -*- coding: utf-8 -*-
"""Utilities to get elements of generated spec"""


def get_schemas(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["definitions"]
    return spec.to_dict()["components"]["schemas"]


def get_parameters(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["parameters"]
    return spec.to_dict()["components"]["parameters"]


def get_responses(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["responses"]
    return spec.to_dict()["components"]["responses"]


def get_security_schemes(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["securityDefinitions"]
    return spec.to_dict()["components"]["securitySchemes"]


def get_paths(spec):
    return spec.to_dict()["paths"]


def ref_path(spec):
    if spec.openapi_version.version[0] < 3:
        return "#/definitions/"
    return "#/components/schemas/"
