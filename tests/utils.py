# -*- coding: utf-8 -*-
"""Utilities to get elements of generated spec"""

def get_definitions(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()['definitions']
    return spec.to_dict()['components']['schemas']

def get_paths(spec):
    return spec.to_dict()['paths']
