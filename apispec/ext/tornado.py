# -*- coding: utf-8 -*-
"""Tornado plugin. Includes a path helper that allows you to pass an urlspec (path-handler pair)
object to `add_path`.
::

    from pprint import pprint

    from tornado.web import RequestHandler

    class HelloHandler(RequestHandler):
        def get(self):
            '''Get a greeting endpoint.
            ---
            description: Get a greeting
            responses:
                200:
                    description: A greeting to the client
                    schema:
                        $ref: '#/definitions/Greeting'
            '''
            self.write("hello")

    urlspec = (r'/hello', HelloHandler)
    spec.add_path(urlspec=urlspec)
    pprint(spec.to_dict()['paths'])
    # {'/hello': {'get': {'description': 'Get a greeting',
    #                     'responses': {200: {'description': 'A greeting to the '
    #                                                     'client',
    #                                         'schema': {'$ref': '#/definitions/Greeting'}}}}}}

"""
from __future__ import absolute_import
import inspect
import sys
from tornado.web import URLSpec

from apispec import Path
from apispec import utils
from apispec.exceptions import APISpecError


def setup(spec):
    """Setup for the plugin."""
    spec.register_path_helper(path_from_urlspec)

def path_from_urlspec(spec, urlspec, operations, **kwargs):
    """Path helper that allows passing a Tornado URLSpec or tuple."""
    if not isinstance(urlspec, URLSpec):
        urlspec = URLSpec(*urlspec)
    if operations is None:
        operations = {}
        for operation in _operations_from_methods(urlspec.handler_class):
            operations.update(operation)
    if not operations:
        raise APISpecError(
            'Could not find endpoint for urlspec {0}'.format(urlspec))
    params_method = getattr(urlspec.handler_class, list(operations.keys())[0])
    path = tornadopath2swagger(urlspec, params_method)
    extensions = _extensions_from_handler(urlspec.handler_class)
    operations.update(extensions)
    return Path(path=path, operations=operations)

def _operations_from_methods(handler_class):
    """Generator of operations described in handler's http methods

    :param handler_class:
    :type handler_class: RequestHandler descendant
    """
    for httpmethod in utils.PATH_KEYS:
        method = getattr(handler_class, httpmethod)
        operation_data = utils.load_yaml_from_docstring(method.__doc__)
        if operation_data:
            operation = {httpmethod: operation_data}
            yield operation

def tornadopath2swagger(urlspec, method):
    """Convert Tornado URLSpec to OpenAPI-compliant path.

    :param urlspec:
    :type urlspec: URLSpec
    :param method: Handler http method
    :type method: function
    """
    if sys.version_info >= (3, 3):
        args = list(inspect.signature(method).parameters.keys())[1:]
    else:
        if getattr(method, '__tornado_coroutine__', False):
            method = method.__wrapped__
        args = inspect.getargspec(method).args[1:]
    valid_args = []
        for arg in args:
            if arg != 'args' and arg != 'kwargs':
                valid_args.append(arg)
        args = set(valid_args)
    params = tuple('{{{}}}'.format(arg) for arg in args)
    try:
        path_tpl = urlspec.matcher._path
    except AttributeError:  # tornado<4.5
        path_tpl = urlspec._path
    path = (path_tpl % params)
    if path.count('/') > 1:
        path = path.rstrip('/?*')
    return path

def _extensions_from_handler(handler_class):
    """Returns extensions dict from handler docstring

    :param handler_class:
    :type handler_class: RequestHandler descendant
    """
    extensions = utils.load_yaml_from_docstring(handler_class.__doc__) or {}
    return extensions
