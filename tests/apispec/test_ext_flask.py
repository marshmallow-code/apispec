# -*- coding: utf-8 -*-
import pytest

from flask import Flask
from smore.apispec import APISpec

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
            'smore.ext.flask'
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

        spec.add_path(view=hello, operations={'get': {'parameters': '..params..'}})
        assert '/hello' in spec._paths
        assert 'get' in spec._paths['/hello']
        assert spec._paths['/hello']['get'] == {'parameters': '..params..'}

    def test_path_with_multiple_methods(self, app, spec):

        @app.route('/hello', methods=['GET', 'POST'])
        def hello():
            return 'hi'

        spec.add_path(view=hello, operations=dict(
            get={'description': 'get a greeting'},
            post={'description': 'post a greeting'}
        ))
        get_op = spec._paths['/hello']['get']
        post_op = spec._paths['/hello']['post']
        assert get_op['description'] == 'get a greeting'
        assert post_op['description'] == 'post a greeting'

    def test_integration_with_docstring_introspection(self, app, spec):

        @app.route('/hello')
        def hello():
            """Get a greeting.

            ---
            get:
                description: get a greeting
            post:
                description: post a greeting
            foo:
                description: not a valid operation
            """
            return 'hi'

        spec.add_path(view=hello)
        get_op = spec._paths['/hello']['get']
        post_op = spec._paths['/hello']['post']
        assert get_op['description'] == 'get a greeting'
        assert post_op['description'] == 'post a greeting'
        assert 'foo' not in spec._paths['/hello']
