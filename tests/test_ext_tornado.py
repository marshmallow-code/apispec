# -*- coding: utf-8 -*-
import pytest

from tornado.web import RequestHandler
import tornado.gen

from apispec import APISpec
from apispec.ext.tornado import TornadoPlugin

from .utils import get_paths


@pytest.fixture(params=('2.0', '3.0.0'))
def spec(request):
    return APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        openapi_version=request.param,
        plugins=(TornadoPlugin(), ),
    )


class TestPathHelpers:

    def test_path_from_urlspec(self, spec):
        class HelloHandler(RequestHandler):
            def get(self):
                self.write('hello')

        urlspec = (r'/hello', HelloHandler)
        operations = (
            {'get': {'parameters': [], 'responses': {'200': {}}}}
        )

        spec.add_path(urlspec=urlspec, operations=operations)
        paths = get_paths(spec)
        assert '/hello' in paths
        assert 'get' in paths['/hello']
        expected = {'parameters': [], 'responses': {'200': {}}}
        assert paths['/hello']['get'] == expected

    def test_path_with_multiple_methods(self, spec):

        class HelloHandler(RequestHandler):
            def get(self):
                self.write('hello')

            def post(self):
                self.write('hello')

        urlspec = (r'/hello', HelloHandler)
        operations = {
            'get': {
                'description': 'get a greeting',
                'responses': {'200': {}},
            },
            'post': {
                'description': 'post a greeting',
                'responses': {'200': {}},
            },
        }
        spec.add_path(urlspec=urlspec, operations=operations)
        paths = get_paths(spec)
        get_op = paths['/hello']['get']
        post_op = paths['/hello']['post']
        assert get_op['description'] == 'get a greeting'
        assert post_op['description'] == 'post a greeting'

    def test_integration_with_docstring_introspection(self, spec):

        class HelloHandler(RequestHandler):
            """
            ---
            x-extension: value
            """
            def get(self):
                """Get a greeting endpoint.
                ---
                description: get a greeting
                responses:
                    200:
                        description: a pet to be returned
                        schema:
                            $ref: #/definitions/Pet
                """
                self.write('hello')

            def post(self):
                """Post a greeting endpoint.
                ---
                description: post a greeting
                responses:
                    200:
                        description: some data
                """
                self.write('hello')

        urlspec = (r'/hello', HelloHandler)
        spec.add_path(urlspec=urlspec)
        paths = get_paths(spec)
        get_op = paths['/hello']['get']
        post_op = paths['/hello']['post']
        extension = paths['/hello']['x-extension']
        assert get_op['description'] == 'get a greeting'
        assert post_op['description'] == 'post a greeting'
        assert extension == 'value'

    def test_path_removing_trailing_or_optional_slash(self, spec):

        class HelloHandler(RequestHandler):
            def get(self):
                self.write('hello world')

        urlspec = (r'/hello/world/*', HelloHandler)
        operations = (
            {'get': {'parameters': [], 'responses': {'200': {}}}}
        )

        spec.add_path(urlspec=urlspec, operations=operations)
        assert '/hello/world' in get_paths(spec)

    class HelloWorldHandler(RequestHandler):
        def get(self, param1, param2):
            self.write('hello')

    class HelloWorldHandler2(RequestHandler):
        @tornado.gen.coroutine
        def get(self, param1, param2):
            self.write('hello')

    @pytest.mark.parametrize(
        'Handler',
        [
            HelloWorldHandler,
            HelloWorldHandler2,
        ],
    )
    def test_path_with_params(self, spec, Handler):
        urlspec = (r'/hello/([^/]+)/world/([^/]+)', Handler)
        operations = (
            {'get': {'parameters': [], 'responses': {'200': {}}}}
        )

        spec.add_path(urlspec=urlspec, operations=operations)
        path = '/hello/{param1}/world/{param2}'
        paths = get_paths(spec)
        assert path in paths
        assert 'get' in paths[path]
        expected = {'parameters': [], 'responses': {'200': {}}}
        assert paths[path]['get'] == expected
