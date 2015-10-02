# -*- coding: utf-8 -*-
import pytest

from flask import Flask
from apispec import APISpec

@pytest.fixture()
def spec():
    return APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        description='This is a sample Petstore server.  You can find out more '
        'about Swagger at <a href=\"http://swagger.wordnik.com\">http://swagger.wordnik.com</a> '
        'or on irc.freenode.net, #swagger.  For this sample, you can use the api '
        'key \"special-key\" to test the authorization filters',
        plugins=[
            'apispec.ext.flask'
        ]
    )


@pytest.yield_fixture()
def app():
    _app = Flask(__name__)
    ctx = _app.test_request_context()
    ctx.push()
    yield _app
    ctx.pop()


class TestPathHelpers:

    def test_path_from_view(self, app, spec):
        @app.route('/hello')
        def hello():
            return 'hi'

        spec.add_path(view=hello,
            operations={'get': {'parameters': [], 'responses': {'200': '..params..'}}})
        assert '/hello' in spec._paths
        assert 'get' in spec._paths['/hello']
        expected = {'parameters': [], 'responses': {'200': '..params..'}}
        assert spec._paths['/hello']['get'] == expected

    def test_path_with_multiple_methods(self, app, spec):

        @app.route('/hello', methods=['GET', 'POST'])
        def hello():
            return 'hi'

        spec.add_path(view=hello, operations=dict(
            get={'description': 'get a greeting', 'responses': {'200': '..params..'}},
            post={'description': 'post a greeting', 'responses': {'200': '..params..'}}
        ))
        get_op = spec._paths['/hello']['get']
        post_op = spec._paths['/hello']['post']
        assert get_op['description'] == 'get a greeting'
        assert post_op['description'] == 'post a greeting'

    def test_integration_with_docstring_introspection(self, app, spec):

        @app.route('/hello')
        def hello():
            """A greeting endpoint.

            ---
            get:
                description: get a greeting
                responses:
                    200:
                        description: a pet to be returned
                        schema:
                            $ref: #/definitions/Pet

            post:
                description: post a greeting
                responses:
                    200:
                        description:some data

            foo:
                description: not a valid operation
                responses:
                    200:
                        description:
                            more junk
            """
            return 'hi'

        spec.add_path(view=hello)
        get_op = spec._paths['/hello']['get']
        post_op = spec._paths['/hello']['post']
        assert get_op['description'] == 'get a greeting'
        assert post_op['description'] == 'post a greeting'
        assert 'foo' not in spec._paths['/hello']

    def test_path_is_translated_to_swagger_template(self, app, spec):

        @app.route('/pet/<pet_id>')
        def get_pet(pet_id):
            return 'representation of pet {pet_id}'.format(pet_id=pet_id)

        spec.add_path(view=get_pet)
        assert '/pet/{pet_id}' in spec._paths
