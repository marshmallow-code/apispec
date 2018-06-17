# -*- coding: utf-8 -*-
"""Operations helper that allows you to remove unusable configurations given the rules of OpenAPI and the rules of HTTP
This extension removes:

- Path parameters if the parameter is not in the path
- Body parameters if the method is entityless (bodyless)
- Response schemas if the method requires an answer without entity (body)

If you want exceptions, you can set to false, the boolean attribute named 'x-autoremove' to block its removal
For a parameter, place it along with the parameter itself. E.g.

def method(path_var):
    '''
    get:
        description: Getting a method
        parameters:
            - in: path
              name: path_var
              type: string
              x-autoremove: false
    '''

For a response, place it inside the response's status code. E.g.

def method(path_var):
    '''
    get:
        description: Getting a method
        responses:
            400:
                description: he may fail {f[x-400-suffix]}
                schema: PetSchema
                x-autoremove: false
    '''

Note: This extension is specially useful when used along with "decorated_crawler" extension

You may add or remove the methods which allow entities at request or at response at any time between ´add_path()´ calls
by calling
For requests. Defaults to: set({'get', 'head', 'options', 'delete'})
add_bodyless_request_method(method)
remove_bodyless_request_method(method)

For responses. Defaults to: set({'head'})
add_bodyless_response_to_method(method)
remove_bodyless_response_to_method(method)


"""
from __future__ import absolute_import
import re


BODYLESS_REQUEST_METHODS = {method for method in ['get', 'head', 'options', 'delete']}
BODYLESS_RESPONSE_METHODS = {method for method in ['head']}


def add_bodyless_request_method(method):
    BODYLESS_REQUEST_METHODS.add(method.lower())


def remove_bodyless_request_method(method):
    BODYLESS_RESPONSE_METHODS.discard(method.lower())


def add_bodyless_response_to_method(method):
    BODYLESS_REQUEST_METHODS.add(method.lower())


def remove_bodyless_response_to_method(method):
    BODYLESS_RESPONSE_METHODS.discard(method.lower())


PATH_VARS_FINDER = re.compile(r'{([^}]*)}')


def remove_unusable_parameters(method, path_vars, method_operations):
    removes = []
    for i, parameter in enumerate(method_operations['parameters']):
        if parameter['in'] == 'path' and \
                parameter['name'] not in path_vars and \
                not parameter.get('x-autoremove', True):
            removes.append(i)

        if parameter['in'] == 'body' and \
            method in BODYLESS_REQUEST_METHODS:
            removes.append(i)

    for i in sorted(removes, reverse=True):
        del method_operations['parameters'][i]


def remove_unusable_response_schemas(method, method_operations):
    if method in BODYLESS_RESPONSE_METHODS:
        for status, response in method_operations.get('responses', {}).items():
            if not response.get('x-autoremove', True):
                # Remove the schema for the answer format which will never happen, if it exists
                response.pop('schema', None)


def path_vars(path):
    return {path_vars_match.group(1) for path_vars_match in PATH_VARS_FINDER.finditer(path)}


def remove_unused_params(spec, path, operations, **kwargs):

    url_vars = path_vars(path)

    for method, method_operations in operations:
        remove_unusable_parameters(method, url_vars, method_operations)
        remove_unusable_response_schemas(method, method_operations)


def setup(spec):
    """Setup for the plugin."""
    spec.register_operation_helper(remove_unused_params)
