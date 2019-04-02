# -*- coding: utf-8 -*-
"""Utilities to get elements of generated spec"""

from apispec.utils import build_reference


def get_schemas(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict().get("definitions")
    return spec.to_dict()["components"].get("schemas")


def get_parameters(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict().get("parameters")
    return spec.to_dict()["components"].get("parameters")


def get_responses(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict().get("responses")
    return spec.to_dict()["components"].get("responses")


def get_security_schemes(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict().get("securityDefinitions")
    return spec.to_dict()["components"].get("securitySchemes")


def get_paths(spec):
    return spec.to_dict().get("paths")


def build_ref(spec, component_type, obj):
    return build_reference(component_type, spec.openapi_version.major, obj)
