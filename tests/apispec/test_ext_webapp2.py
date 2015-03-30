# -*- coding: utf-8 -*-
import pytest
import sys

PY2 = int(sys.version[0]) == 2

pytestmark = pytest.mark.skipif(not PY2, reason='webapp2 is only compatible with Python 2')

from smore.apispec import APISpec

if PY2:
    # everything should be skipped via `pytestmark` here so it is OK
    import webapp2
    from webapp2_extras import routes


    class MainPage(webapp2.RequestHandler):
        def get(self, *args, **kwargs):
            self.response.write('Hello from GET!')

        def post(self, *args, **kwargs):
            self.response.write('Hello from POST!')

        def put(self, *args, **kwargs):
            self.response.write('Hello from PUT!')

        def delete(self, *args, **kwargs):
            self.response.write('Hello from DELETE!')

        def patch(self, *args, **kwargs):
            self.response.write('Hello from PATCH!')

        def get_with_docstring(self, *args, **kwargs):
            """A greeting endpoint.

            ---
            get:
                description: get a greeting
                responses:
                    200:
                        description: Greets you

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
            self.response.write('Hello from GET docstring!')


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
            'smore.ext.webapp2'
        ]
    )


@pytest.fixture()
def app():
    _app = webapp2.WSGIApplication([
        routes.PathPrefixRoute('/prefix', [
            # all routes go here
            webapp2.Route(r'/path/<course_id>', MainPage, methods=['GET']),
            webapp2.Route(r'/users/<user_id:\d+>/setting/<setting_id:\w\d+>', MainPage),
        ]),
        webapp2.Route(r'/1', MainPage),
        webapp2.Route(r'/2', MainPage, methods=['POST']),
        webapp2.Route(r'/3', MainPage, methods=['DELETE', 'GET'])
    ], debug=True)
    # set up app and request for testing
    request = webapp2.Request.blank('/')
    _app.set_globals(app=_app, request=request)
    return _app


class TestPathHelpers:

    def test_path_from_view(self, app, spec):
        route = webapp2.Route(r'/hello', MainPage, methods=['GET'])
        spec.add_path(route=route)
        assert '/hello' in spec._paths
        assert 'get' in spec._paths['/hello']
        assert spec._paths['/hello']['get'] == {}

    def test_path_with_multiple_methods(self, app, spec):
        route = webapp2.Route(r'/hello', MainPage, methods=['GET', 'POST'])
        spec.add_path(route=route, operations=dict(
            get={'description': 'get a greeting', 'responses': {'200': '..params..'}},
            post={'description': 'post a greeting', 'responses': {'200': '..params..'}}
        ))

        get_op = spec._paths['/hello']['get']
        post_op = spec._paths['/hello']['post']
        assert get_op['description'] == 'get a greeting'
        assert post_op['description'] == 'post a greeting'

    def test_integration_with_docstring_introspection(self, app, spec):
        route = webapp2.Route(r'/hello', MainPage, methods=['GET', 'POST'], handler_method='get_with_docstring')
        spec.add_path(route=route)
        get_op = spec._paths['/hello']['get']
        post_op = spec._paths['/hello']['post']
        assert get_op['description'] == 'get a greeting'
        assert post_op['description'] == 'post a greeting'
        assert 'foo' not in spec._paths['/hello']

    def test_path_is_translated_to_swagger_template(self, app, spec):
        route = webapp2.Route(r'/hello/<name:\d+>', MainPage, methods=['GET', 'POST'])
        spec.add_path(route=route)

        assert '/hello/{name}' in spec._paths

    def test_route_types_can_be_translated(self, app, spec):
        routes = set(r for route in app.router.match_routes for r in route.get_routes())
        for route in routes:
            spec.add_path(route=route)
        assert len(spec._paths) == len(routes)
        assert '/prefix/path/{course_id}' in spec._paths
        assert '/prefix/users/{user_id}/setting/{setting_id}' in spec._paths
        assert '/1' in spec._paths
        assert '/2' in spec._paths
        assert '/3' in spec._paths
