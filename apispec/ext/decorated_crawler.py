# -*- coding: utf-8 -*-
"""Operations helper that allows you to pass a decorated view and get the combined documentation of all decorator functions.
It required the view passed to `add_path`. Inspects view docstrings and its docd_wraps decorator functions and merges all the
documentation into a single document.
Useful if you use decorators to manage authentication or even if you have shared error pages and you do not
want to document common error states (status 400, status 500, etc...) individually on all views.

All documentation is merged from bottom-up, starting on the view function and ending on the topmost decorator.
Decorators can declare a special method called _ (underscore). That one is applied last for all methods,
also from bottom up, in a subsequent pass.

For example:

With this setup::

    from flask import Flask
    from apispec.ext.decorated_crawler import docd_wraps

    app = Flask(__name__)


    def decorates(func):
        @docd_wraps(func)
        def calling(*args, **kwargs):
            '''
            ---
            get:
                consumes:
                  - application/xml+dec1
                security:
                    - AlmostBasicAuth: []
                      BasicAuth: []
                    - ApiKeyAuth: []
                tags:
                    - down1
                    - up1
                responses:
                    400:
                        description: he may fail {f[x-400-suffix]}
                        schema: PetSchema
            _:
                responses:
                    400:
                        description: Global fail
                        schema: PetSchema
            '''
            return func(*args, **kwargs)

        return calling

    def decorates2(func):
        @docd_wraps(func)
        def calling(*args, **kwargs):
            '''
            ---
            get:
                tags:
                    - get2
                    - up1
                security:
                    - OAuth2: [scope1, scope2]
                responses:
                    402:
                        description: mefail
                        schema: PetSchema
            '''
            return func(*args, **kwargs)

        return calling


Passing a view function::

@app.route('/random/<kind>')
@decorates
@decorates2
def random_pet(kind):
    '''A cute furry animal endpoint.
    ---

    post:
        description: POST a pet
    get:
        description: Get a pet
        security:
            - ApiKeyAuth: []
        consumes:
          - application/json
          - application/xml
        produces:
          - application/json
          - application/xml
        parameters:
            - in: path
              name: kind
              required: true
              type: string
              description: Path Parameter description in Markdown.
            - in: query
              name: offset
              type: string
              description: Query Parameter description in Markdown.
        responses:
            200:
                description: A pet to be returned
                schema: PetSchema
            400:
                x-400-suffix: yeah yeah....
    '''
    pet = {
        "category": [{
            "id": 1,
            "name": "Named"
        }],
        "name": "woof"
    }
    return jsonify(PetSchema().dump(pet).data)


    with app.test_request_context():
        spec.add_path(view=gist_detail)


Passing a method view function::

    from flask.views import MethodView

    class PetApi(MethodView):
        @decorates
        @decorates2
        def get(kind):
            '''A cute furry animal endpoint.
            ---
            description: Get a pet
            security:
                - ApiKeyAuth: []
            consumes:
              - application/json
              - application/xml
            produces:
              - application/json
              - application/xml
            parameters:
                - in: path
                  name: kind
                  required: true
                  type: string
                  description: Path Parameter description in Markdown.
                - in: query
                  name: offset
                  type: string
                  description: Query Parameter description in Markdown.
            responses:
                200:
                    description: A pet to be returned
                    schema: PetSchema
                400:
                    x-400-suffix: yeah yeah....
            '''
            pet = {
                "category": [{
                    "id": 1,
                    "name": "Named"
                }],
                "name": "woof"
            }
            return jsonify(PetSchema().dump(pet).data)


        def post(self):
            '''A cute furry animal endpoint.
            ---

                description: POST a pet
            '''
           pass

    method_view = PetApi.as_view('randomPet')
    app.add_url_rule("/random/<kind>", view_func=method_view)
    with app.test_request_context():
        spec.add_path(view=method_view)

The result will be::

    print(spec.to_dict()['paths'])
    # OrderedDict([
        ('/random',
        OrderedDict([
            ('post',
              {'description': 'POST a pet',
              'responses': {400: {'description': 'Global fail', 'schema': {'$ref': '#/definitions/Pet'}}}}),
            ('get',
            {'description': 'Get a pet',
            'security': [{'ApiKeyAuth': []}, {'AlmostBasicAuth': [], 'BasicAuth': []}, {'OAuth2': ['scope1', 'scope2']}],
            'consumes': ['application/json', 'application/xml', 'application/xml+dec1'],
            'produces': ['application/json', 'application/xml'],
            'parameters': [{'in': 'path', 'name': 'kind', 'required': True, 'type': 'string', 'description': 'Path Parameter description in Markdown.'}, {'in': 'query', 'name': 'offset', 'type': 'string', 'description': 'Query Parameter description in Markdown.'}],
            'responses': {200: {'description': 'A pet to be returned', 'schema': {'$ref': '#/definitions/Pet'}},
            400: {'x-400-suffix': 'yeah yeah....', 'description': 'he may fail yeah yeah....'},
            402: {'description': 'mefail', 'schema': {'$ref': '#/definitions/Pet'}}}, 'tags': ['down1', 'up1', 'get2']})]))])



"""
from __future__ import absolute_import

import itertools
import re

from apispec.compat import iteritems
from apispec import Path
from apispec import utils

from contextlib import contextmanager
from collections import Mapping, OrderedDict


def docd_wraps(wrapped, *args, **kwargs):
    """Decorator factory to apply update_wrapper() to a wrapper function while backing up the original pydoc

       Note: this is used in the exact same way as functools.wraps() as in
        https://docs.python.org/3/library/functools.html#functools.wraps
       Returns a decorator that invokes update_wrapper() with the decorated
       function as the wrapper argument and the arguments to docd_wraps() as the
       remaining arguments. Default arguments are as for update_wrapper().
       This is a convenience function to simplify applying partial() to
       update_wrapper().

       Keep in mind that __orig_doc__ and  __wrapped__ are used internally and should not be overridden.
       The original document is stored in the parameter __orig_doc__ and the underlying system uses __wrapped__ to store
       the whole call tree until the original ran function

    :param wrapped: The original function that decorates. See:
    :param args: arguments to be proxied directly to update_wrapper()
    :param kwargs: arguments to be proxied directly to update_wrapper()
    :return: The wrapped function that looks like the wrapper function
    """
    from functools import update_wrapper

    def wrap(wrapper):
        doc = wrapper.__doc__
        update_wrapper(wrapper, wrapped, *args, **kwargs)
        wrapper.__orig_doc__ = doc
        return wrapper
    return wrap

class IncompleteParameterSetting(Exception):
    pass


class DictDefaultWrap(Mapping):
    def __init__(self):
        self.dict = None

    def __getitem__(self, item):
        return self.dict.get(item, '')

    def __getattr__(self, item):
        return self.dict.__getattr__(item)
    def __iter__(self):
        return self.dict.__iter__()
    def __len__(self):
        return self.dict.__len__()
    def __str__(self):
        return "DictDefaultWrap:" + str(self.dict)


def temp_dict_missing(dict_wrapper):
    @contextmanager
    def call(for_miss):
        dict_wrapper.dict = for_miss
        yield dict_wrapper
    return call


def operations_merging(spec, path, operations, view, **kwargs):
    """operations helper that allows passing an annotated function."""

    dict_of_missing = temp_dict_missing(DictDefaultWrap())

    hierarchy_docs = []
    hierarchy_func = view
    while hierarchy_func:
        doc = getattr(hierarchy_func, '__orig_doc__', None)
        if doc:
            doc_yaml = utils.load_yaml_from_docstring(doc)
            if doc_yaml:
                hierarchy_docs.append(doc_yaml)
        hierarchy_func = getattr(hierarchy_func, '__wrapped__', None)


    def parameters_merging(o_parameters, d_parameters, yaml_doc):
        o_parameter_ids = {}
        for parameter in o_parameters:
            try:
                o_parameter_ids[(parameter['in'], parameter['name'])] = parameter
            except KeyError as e:
                raise IncompleteParameterSetting(
                    "While solving parameter {}, with yaml document {}, related to view with doc {},"
                    "the parameter attribute '{}' was missing".format(parameter, yaml_doc, view, e.args[0]))

        for parameter in d_parameters['parameters']:
            try:
                param_in = parameter['in']
                param_name = parameter['name']
            except KeyError as e:
                raise IncompleteParameterSetting(
                    "While solving parameter {}, with yaml document {}, related to view with doc {},"
                    "the parameter attribute '{}' was missing".format(parameter, yaml_doc, view, e.args[0]))

            o_parameter = o_parameter_ids.pop((param_in, param_name), None)
            if not o_parameter:
                o_parameter = {}
                o_parameters.append(o_parameter)

    def merge_with_default(original, defaults, yaml_doc=None):
        for operation_name, d_operation_content in defaults.items():
            o_operation_content = original.setdefault(operation_name, d_operation_content)
            if o_operation_content is d_operation_content:
                if isinstance(o_operation_content, str):
                    # This allows making placeholders for the string that were never set and not raising as a result.
                    with dict_of_missing(original) as defaulted_dict:
                        original[operation_name] = o_operation_content.format(f=defaulted_dict)
                continue
            if isinstance(o_operation_content, dict):
                merge_with_default(o_operation_content, d_operation_content, yaml_doc)
            elif isinstance(o_operation_content, list):
                if operation_name == "parameters":
                    parameters_merging(o_operation_content, d_operation_content, yaml_doc)
                elif operation_name == 'security':
                    o_security_methods = {tuple(security_rule.keys()) for security_rule in o_operation_content}
                    new_auth_methods = [security_rule for security_rule in d_operation_content
                                       if tuple(security_rule.keys()) not in o_security_methods]
                    o_operation_content.extend(new_auth_methods)

                    pass
                elif operation_name in ('produces', 'consumes', 'tags'):
                    o_operation_content[:] = list(OrderedDict.fromkeys(
                            itertools.chain(o_operation_content, d_operation_content)).keys())

    fallover_defaults = []
    for hierarchy_doc in hierarchy_docs:
        try:
            fallover_defaults.append(hierarchy_doc.pop('_'))
        except KeyError:
            pass
        merge_with_default(path.operations, hierarchy_doc, view.__doc__)
    if fallover_defaults:
        underscore_default = fallover_defaults.pop(0)
        # Algorithmically, it is faster O(_n) if I merge all operations for all methods first than if I
        # run the same defaults sequence for all methods
        for default in fallover_defaults:
            merge_with_default(underscore_default, default, view.__doc__)
        for method, method_operations in path.operations.items():
            merge_with_default(method_operations, underscore_default, view.__doc__)

    return path

def setup(spec):
    """Setup for the plugin."""
    spec.register_operation_helper(operations_merging)
