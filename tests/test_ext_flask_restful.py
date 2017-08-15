# -*- coding: utf-8 -*-
import pytest

from apispec import APISpec
from flask import Flask, Blueprint
from flask_restful import Api, Resource


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
            'apispec.ext.flask_restful'
        ]
    )

@pytest.yield_fixture()
def app():
    _app = Flask(__name__)
    ctx = _app.test_request_context()
    ctx.push()
    yield _app
    ctx.pop()


@pytest.yield_fixture()
def api():
    _app = Flask(__name__)
    _api = Api(_app)
    ctx = _app.test_request_context()
    ctx.push()
    yield _api
    ctx.pop()


class TestPathHelpers:
    def test_path_from_view(self, api, spec):
        class HelloResource(Resource):
            def get(self, hello_id):
                return 'hi'

        api.add_resource(HelloResource, '/hello')

        spec.add_path(resource=HelloResource, api=api,
                      operations={'get': {'parameters': [], 'responses': {'200': '..params..'}}})
        assert '/hello' in spec._paths
        assert 'get' in spec._paths['/hello']
        expected = {'parameters': [], 'responses': {'200': '..params..'}}
        assert spec._paths['/hello']['get'] == expected

    def test_path_from_view_added_via_path(self, api, spec):
        class HelloResource(Resource):
            def get(self, hello_id):
                return 'hi'

        api.add_resource(HelloResource, '/hello')

        spec.add_path(resource=HelloResource, path='/hello',
                      operations={'get': {'parameters': [], 'responses': {'200': '..params..'}}})
        assert '/hello' in spec._paths
        assert 'get' in spec._paths['/hello']
        expected = {'parameters': [], 'responses': {'200': '..params..'}}
        assert spec._paths['/hello']['get'] == expected

    def test_path_with_multiple_methods(self, api, spec):
        class HelloResource(Resource):
            def get(self, hello_id):
                return 'hi'

            def post(self, hello_id):
                pass

        api.add_resource(HelloResource, '/hello')

        spec.add_path(resource=HelloResource, api=api, operations=dict(
            get={'description': 'get a greeting', 'responses': {'200': '..params..'}},
            post={'description': 'post a greeting', 'responses': {'200': '..params..'}}
        ))
        get_op = spec._paths['/hello']['get']
        post_op = spec._paths['/hello']['post']
        assert get_op['description'] == 'get a greeting'
        assert post_op['description'] == 'post a greeting'

    def test_integration_with_docstring_introspection(self, api, spec):
        class HelloResource(Resource):
            def get(self, hello_id):
                """A greeting endpoint.
                       ---
                       x-extension: value
                       description: get a greeting
                       responses:
                           200:
                               description: a pet to be returned
                               schema:
                                   $ref: #/definitions/Pet
                 """

            pass

            def post(self, hello_id):
                """A greeting endpoint.
                   ---
                   x-extension: value
                   description: post a greeting
                   responses:
                       200:
                           description:some data
                   """
            pass

        api.add_resource(HelloResource, '/hello')

        spec.add_path(resource=HelloResource, api=api)
        get_op = spec._paths['/hello']['get']
        post_op = spec._paths['/hello']['post']
        extension = spec._paths['/hello']['get']['x-extension']
        assert get_op['description'] == 'get a greeting'
        assert post_op['description'] == 'post a greeting'
        assert extension == 'value'

    def test_integration_invalid_docstring(self, api, spec):
        class HelloResource(Resource):
            def get(self, hello_id):
                """A greeting endpoint.
                       ---
                    description: it is an invalid string in YAML
                       responses:
                           200:
                               description: a pet to be returned
                               schema:
                                   $ref: #/definitions/Pet
                 """

            pass

        api.add_resource(HelloResource, '/hello')

        spec.add_path(resource=HelloResource, api=api)
        get_op = spec._paths['/hello']['get']
        assert not get_op

    def test_path_is_translated_to_swagger_template(self, api, spec):
        class HelloResource(Resource):
            def get(self, hello_id):
                pass

        api.add_resource(HelloResource, '/pet/<pet_id>')

        spec.add_path(resource=HelloResource, api=api)
        assert '/pet/{pet_id}' in spec._paths

    def test_path_blueprint(self, app, spec):
        class HelloResource(Resource):
            def get(self, hello_id):
                return 'hi'

        bp = Blueprint(app, __name__)
        api = Api(bp)
        app.register_blueprint(bp, url_prefix='/v1')
        api.add_resource(HelloResource, '/hello')

        spec.add_path(resource=HelloResource, api=api, app=app,
                      operations={'get': {'parameters': [], 'responses': {'200': '..params..'}}})
        assert '/v1/hello' in spec._paths
        assert 'get' in spec._paths['/v1/hello']
        expected = {'parameters': [], 'responses': {'200': '..params..'}}
        assert spec._paths['/v1/hello']['get'] == expected

    def test_path_blueprint_no_app_fallback(self, app, spec):
        class HelloResource(Resource):
            def get(self, hello_id):
                return 'hi'

        bp = Blueprint(app, __name__)
        api = Api(bp)
        app.register_blueprint(bp, url_prefix='/v1')
        api.add_resource(HelloResource, '/hello')

        spec.add_path(resource=HelloResource, api=api, app=None,
                      path='/v1/hello',
                      operations={'get': {'parameters': [], 'responses': {'200': '..params..'}}})
        assert '/v1/hello' in spec._paths
        assert 'get' in spec._paths['/v1/hello']
        expected = {'parameters': [], 'responses': {'200': '..params..'}}
        assert spec._paths['/v1/hello']['get'] == expected
