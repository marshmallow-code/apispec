# -*- coding: utf-8 -*-
"""Flask-RESTful plugin. Includes a path helper that allows you to pass a resource
object to `add_path`.
::

    from pprint import pprint

    from flask_restful import Api, Resource
    from flask import Flask

    class HelloResource(Resource):
        def get(self, hello_id):
            '''A greeting endpoint.
                   ---
                   description: get a greeting
                   responses:
                       200:
                           description: a pet to be returned
                           schema:
                               $ref: #/definitions/Pet
            '''
            pass

    app = Flask(__name__)
    api = Api(app)
    api.add_resource(HelloResource, '/hello')

    spec.add_path(resource=HelloResource, api=api)
    pprint(spec.to_dict()['paths'])

    # {'/hello': {'get': {'description': 'Get a greeting',
    #                     'responses': {200: {'description': 'a pet to be returned',
    #                                         'schema': {'$ref': '#/definitions/Pet'}}}}}}

    Method `add_path` can be invoked with a resource path in a `path` parameter instead of `api` parameter:

        spec.add_path(resource=HelloResource, path='/hello')

    Flask blueprints are supported too by passing Flask app in `app` parameter:

        spec.add_path(resource=HelloResource, api=api, app=app)
"""

import logging
import re

from apispec import Path, utils
from apispec.exceptions import APISpecError


def deduce_path(resource, **kwargs):
    """Find resource path using provided API or path itself"""
    api = kwargs.get('api', None)
    if not api:
        # flask-restful resource url passed
        return kwargs.get('path').path

    # flask-restful API passed
    # Require MethodView
    if not getattr(resource, 'endpoint', None):
        raise APISpecError('Flask-RESTful resource needed')

    if api.blueprint:
        # it is required to have Flask app to be able enumerate routes
        app = kwargs.get('app')
        if app:
            for rule in app.url_map.iter_rules():
                if rule.endpoint.endswith('.' + resource.endpoint):
                    break
            else:
                raise APISpecError('Cannot find blueprint resource {}'.format(resource.endpoint))
        else:
            # Application not initialized yet, fallback to path
            return kwargs.get('path').path

    else:
        for rule in api.app.url_map.iter_rules():
            if rule.endpoint == resource.endpoint:
                rule.endpoint.endswith('.' + resource.endpoint)
                break
        else:
            raise APISpecError('Cannot find resource {}'.format(resource.endpoint))

    return rule.rule


def parse_operations(resource):
    """Parse operations for each method in a flask-restful resource"""
    operations = {}
    for method in resource.methods:
        docstring = getattr(resource, method.lower()).__doc__
        if docstring:
            operation = utils.load_yaml_from_docstring(docstring)
            if not operation:
                logging.getLogger(__name__).warning(
                    'Cannot load docstring for {}/{}'.format(resource, method))
            operations[method.lower()] = operation or dict()
    return operations


def path_helper(_spec, **kwargs):
    """Extracts swagger spec from `flask-restful` methods."""
    try:
        resource = kwargs.pop('resource')

        path = deduce_path(resource, **kwargs)

        # normalize path
        path = re.sub(r'<(?:[^:<>]+:)?([^<>]+)>', r'{\1}', path)

        operations = parse_operations(resource)

        return Path(path=path, operations=operations)
    except Exception as e:
        logging.getLogger(__name__).exception("Exception parsing APISpec %s", e)
        raise


def setup(spec):
    spec.register_path_helper(path_helper)
