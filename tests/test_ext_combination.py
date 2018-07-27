# -*- coding: utf-8 -*-
from bottle import route
from flask import Flask
from flask.views import MethodView
from tornado.web import RequestHandler
from apispec import APISpec
from apispec.ext.bottle import BottlePlugin
from apispec.ext.flask import FlaskPlugin
from apispec.ext.tornado import TornadoPlugin
from apispec.ext.marshmallow import MarshmallowPlugin


def check_web_framework_and_marshmallow_plugin(web_framework_plugin, **kwargs_for_add_path):
    """Check schemas passed in web framework view function docstring are parsed by MarshmallowPlugin"""
    spec = APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        plugins=[web_framework_plugin(), MarshmallowPlugin()],
        openapi_version='2.0',
    )
    spec.add_path(**kwargs_for_add_path)
    expected = {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'format': 'int32', 'description': 'Pet id', 'readOnly': True},
            'name': {'type': 'string', 'description': 'Pet name'},
        },
        'required': ['name'],
    }
    assert spec.to_dict()['paths']['/hello']['get']['responses'][200]['schema'] == expected


class TestWebFrameworkAndMarshmallowPlugin:
    def test_bottle(self):
        @route('/hello')
        def hello():
            """A greeting endpoint.

            ---
            get:
                responses:
                    200:
                        schema: tests.schemas.PetSchema
            """
            return 'hi'

        check_web_framework_and_marshmallow_plugin(BottlePlugin, view=hello)

    def test_flask(self):
        app = Flask(__name__)

        @app.route('/hello')
        def hello():
            """A greeting endpoint.

            ---
            get:
                responses:
                    200:
                        schema: tests.schemas.PetSchema
            """
            return 'hi'

        with app.test_request_context():
            check_web_framework_and_marshmallow_plugin(FlaskPlugin, view=hello)

    def test_flask_method_view(self):
        app = Flask(__name__)

        class HelloApi(MethodView):
            def get(self_):
                """A greeting endpoint.

                ---
                responses:
                    200:
                        schema: tests.schemas.PetSchema
                """
                return 'hi'

        method_view = HelloApi.as_view('hi')
        app.add_url_rule('/hello', view_func=method_view)
        with app.test_request_context():
            check_web_framework_and_marshmallow_plugin(FlaskPlugin, view=method_view)

    def test_tornado(self):
        class TornadoHelloHandler(RequestHandler):
            def get(self_):
                """A greeting endpoint.

                ---
                responses:
                    200:
                        schema: tests.schemas.PetSchema
                """
                self_.write('hi')

        urlspec = (r'/hello', TornadoHelloHandler)
        check_web_framework_and_marshmallow_plugin(TornadoPlugin, urlspec=urlspec)
