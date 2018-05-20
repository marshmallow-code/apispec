# -*- coding: utf-8 -*-
import pytest

from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.scripting import prepare


from apispec import APISpec
from apispec.ext.pyramid import add_pyramid_paths

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
        plugins=[]
    )


class TestViewHelpers(object):

    def test_path_from_view(self, spec):
        def hi_request(request):
            return Response('Hi')

        with Configurator() as config:
            config.add_route('hi', '/hi')
            config.add_view(hi_request, route_name='hi')
            config.make_wsgi_app()
        with prepare(config.registry):
            add_pyramid_paths(spec, 'hi', operations={
                'get': {'parameters': [], 'responses': {'200': '..params..'}}})
        assert '/hi' in spec._paths
        assert 'get' in spec._paths['/hi']
        expected = {'parameters': [], 'responses': {'200': '..params..'}}
        assert spec._paths['/hi']['get'] == expected

    def test_path_from_method_view(self, spec):
        # Class Based Views
        class HelloApi(object):
            """Greeting API.
            ---
            x-extension: global metadata
            """
            def get(self):
                """A greeting endpoint.
                ---
                description: get a greeting
                responses:
                    200:
                        description: said hi
                """
                return 'hi'

            def post(self):
                return 'hi'

            def mixed(self):
                """Mixed endpoint.
                ---
                description: get a mixed greeting
                responses:
                    200:
                        description: said hi
                """
                return 'hi'

        with Configurator() as config:
            config.add_route('hi', '/hi')
            # normally this would be added via @view_config decorator
            config.add_view(
                HelloApi, attr='get', route_name='hi', request_method='get')
            config.add_view(
                HelloApi, attr='post', route_name='hi', request_method='post')
            config.add_view(
                HelloApi, attr='mixed', route_name='hi',
                request_method=['put', 'delete'], xhr=True)
            config.make_wsgi_app()

        with prepare(config.registry):
            add_pyramid_paths(spec, 'hi')
        import pprint
        pprint.pprint(spec._paths)
        expected = {'description': 'get a greeting',
                    'responses': {200: {'description': 'said hi'}}}
        assert spec._paths['/hi']['get'] == expected
        assert 'post' not in spec._paths['/hi']
        assert spec._paths['/hi']['x-extension'] == 'global metadata'
        assert 'mixed' in spec._paths['/hi']['put']['description']

    def test_path_with_multiple_methods(self, spec):

        def hi_request(request):
            return Response('Hi')

        with Configurator() as config:
            config.add_route('hi', '/hi')
            config.add_view(
                hi_request, route_name='hi', request_method=['get', 'post'])
            config.make_wsgi_app()

        with prepare(config.registry):
            add_pyramid_paths(spec, 'hi', operations=dict(
                get={'description': 'get a greeting', 'responses': {'200': '..params..'}},
                post={'description': 'post a greeting', 'responses': {'200': '..params..'}}
            ))

        get_op = spec._paths['/hi']['get']
        post_op = spec._paths['/hi']['post']
        assert get_op['description'] == 'get a greeting'
        assert post_op['description'] == 'post a greeting'

    def test_integration_with_docstring_introspection(self, spec):
        def hello():
            """A greeting endpoint.

            ---
            x-extension: value
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

        with Configurator() as config:
            config.add_route('hello', '/hello')
            config.add_view(hello, route_name='hello')
            config.make_wsgi_app()

        with prepare(config.registry):
            add_pyramid_paths(spec, 'hello')

        get_op = spec._paths['/hello']['get']
        post_op = spec._paths['/hello']['post']
        extension = spec._paths['/hello']['x-extension']
        assert get_op['description'] == 'get a greeting'
        assert post_op['description'] == 'post a greeting'
        assert 'foo' not in spec._paths['/hello']
        assert extension == 'value'

    def test_path_is_translated_to_swagger_template(self, spec):

        def get_pet(pet_id):
            return 'representation of pet {pet_id}'.format(pet_id=pet_id)

        with Configurator() as config:
            config.add_route('pet', '/pet/{pet_id}')
            config.add_view(
                get_pet, route_name='pet')
            config.make_wsgi_app()

        with prepare(config.registry):
            add_pyramid_paths(spec, 'pet')
        assert '/pet/{pet_id}' in spec._paths
