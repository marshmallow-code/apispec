# -*- coding: utf-8 -*-
import pytest

from apispec import APISpec
from aiohttp import web


@pytest.fixture()
def spec():
    return APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        description='This is a sample server.  You can find out more '
        'about Swagger at <a href=\"http://swagger.wordnik.com\">'
        'http://swagger.wordnik.com</a> or on irc.freenode.net, #swagger.'
        'For this sample, you can use the api key \"special-key\" to test the'
        'authorization filters',
        plugins=[
            'apispec.ext.aiohttp'
        ]
    )


@pytest.fixture()
def app():
    app = web.Application()
    return app


class TestPathHelpers:
    def test_path_from_view_class(self, app, spec):
        class GistView(web.View):
            async def get(self):
                """Gist view
                ---
                responses:
                    200: OK
                """
                return web.json_response(data={'data': 'Hello, world'})

            async def post(self):
                """Without documentation"""
                return web.Response(text="POST method")

        # Config app routing
        app.router.add_route('*', '/gist', GistView)

        spec.add_path(view=GistView, app=app)

        paths = dict(spec.to_dict())['paths']
        assert '/gist' in paths
        assert 'get' in paths['/gist']
        assert 'post' not in paths['/gist']
        expected = {'responses': {200: 'OK'}}
        assert paths['/gist']['get'] == expected

    def test_path_from_view_function(self, app, spec):
        async def index_view(request):
            """Index view
            ---
            responses:
                200:
                    schema:
                        $ref: '#/definitions/Index'
            """
            return web.json_response(data={'data': 'Hello, world'})

        # Config app routing
        app.router.add_get('/', index_view)

        spec.add_path(view=index_view, app=app)

        paths = dict(spec.to_dict())['paths']
        expected = {
            'responses': {200: {'schema': {'$ref': '#/definitions/Index'}}}
        }
        assert paths['/']['get'] == expected
        assert sorted(paths['/'].keys()) == sorted(['get', 'head'])

    def test_path_with_multiple_methods(self, app, spec):
        async def get_example_view(request):
            """
            ---
            description: get method
            """
            return web.json_response(data={'data': 'Hello, world'})

        async def post_example_view(request):
            """
            ---
            description: post method
            """
            return web.json_response(data={'data': 'Hello, world'})

        # Config app routing
        app.router.add_route('GET', '/example', get_example_view)
        app.router.add_route('POST', '/example', post_example_view)

        spec.add_path(view=get_example_view, app=app)
        spec.add_path(view=post_example_view, app=app)

        paths = dict(spec.to_dict())['paths']
        get_op = paths['/example']['get']
        post_op = paths['/example']['post']
        assert get_op['description'] == 'get method'
        assert post_op['description'] == 'post method'

    def test_path_is_translated_to_swagger_template(self, app, spec):
        async def example_view(request):
            """Index view
            ---
            responses:
                200:
                    schema:
                        $ref: '#/definitions/Example'
            """
            return web.json_response(
                data={'example_id': request.match_info['example_id']}
            )

        # Config app routing
        app.router.add_get('/example/{example_id}', example_view)

        spec.add_path(view=example_view, app=app)

        paths = dict(spec.to_dict())['paths']
        assert '/example/{example_id}' in paths
