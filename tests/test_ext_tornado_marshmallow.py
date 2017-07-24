# -*- coding: utf-8 -*-
import pytest

from apispec import APISpec
from apispec.ext.marshmallow import swagger
from tornado.web import RequestHandler
from .schemas import PetSchema

@pytest.fixture()
def spec():
    return APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        description='This is a sample Petstore server.  You can find out more '
        'about Swagger at <a href=\"http://swagger.wordnik.com\">'
        'http://swagger.wordnik.com</a> or on irc.freenode.net, #swagger.'
        'For this sample, you can use the api key \"special-key\" to test the'
        'authorization filters',
        plugins=[
            'apispec.ext.tornado',
            'apispec.ext.marshmallow'
        ]
    )


class TestPathHelpers:

    def test_integration_with_docstring_introspection(self, spec):

        class HelloHandler(RequestHandler):
            def get(self):
                """Get a greeting endpoint.
                ---
                description: get a greeting
                responses:
                    200:
                        description: a pet to be returned
                        schema: tests.schemas.PetSchema
                """
                self.write("hello")

        urlspec = (r'/hello', HelloHandler)
        spec.add_path(urlspec=urlspec)
        get_op = spec._paths['/hello']['get']
        assert get_op['description'] == 'get a greeting'
        response = get_op['responses'][200]
        assert response['description'] == 'a pet to be returned'
        assert response['schema'] == swagger.schema2jsonschema(PetSchema)
