Using Plugins
=============

What is an apispec "plugin"?
----------------------------

An apispec *plugin* is an object that provides helper methods for generating OpenAPI entities from objects in your application.

A plugin may modify the behavior of `APISpec <apispec.APISpec>` methods so that they can take your application's objects as input.

Enabling Plugins
----------------

To enable a plugin, pass an instance to the constructor of `APISpec <apispec.APISpec>`.

.. code-block:: python
    :emphasize-lines: 11

    from apispec import APISpec
    from apispec.ext.marshmallow import MarshmallowPlugin

    spec = APISpec(
        title='Gisty',
        version='1.0.0',
        openapi_version='2.0',
        info=dict(
            description='A minimal gist API'
        ),
        plugins=[MarshmallowPlugin()]
    )


Example: Flask and Marshmallow Plugins
--------------------------------------

The bundled marshmallow plugin (`apispec.ext.marshmallow.MarshmallowPlugin`)
provides helpers for generating OpenAPI schema and parameter objects from `marshmallow <https://marshmallow.readthedocs.io/en/latest/>`_ schemas and fields.

The `apispec-webframeworks <https://github.com/marshmallow-code/apispec-webframeworks>`_
package includes a Flask plugin with helpers for generating path objects from view functions.

Let's recreate the spec from the :doc:`Quickstart guide <quickstart>` using these two plugins.

First, ensure that ``apispec-webframeworks`` is installed: ::

    $ pip install apispec-webframeworks

We can now use the marshmallow and Flask plugins.

.. code-block:: python

    from apispec import APISpec
    from apispec.ext.marshmallow import MarshmallowPlugin
    from apispec_webframeworks import FlaskPlugin

    spec = APISpec(
        title='Gisty',
        version='1.0.0',
        info=dict(
            description='A minimal gist API'
        ),
        plugins=[
            FlaskPlugin(),
            MarshmallowPlugin(),
        ]
    )


Our application will have a marshmallow `Schema <marshmallow.Schema>` for gists.

.. code-block:: python

    from marshmallow import Schema, fields

    class GistParameter(Schema):
        gist_id = fields.Int()

    class GistSchema(Schema):
        id = fields.Int()
        content = fields.Str()


The marshmallow plugin allows us to pass this `Schema` to
`spec.definition <apispec.APISpec.definition>`.


.. code-block:: python

    spec.definition('Gist', schema=GistSchema)

The definition is now added to the spec.

.. code-block:: python
    :emphasize-lines: 4,5,6,7

    from pprint import pprint

    pprint(spec.to_dict())
    # {'definitions': {'Gist': {'properties': {'content': {'type': 'string'},
    #                                         'id': {'format': 'int32',
    #                                                 'type': 'integer'}},
    #                         'type': 'object'}},
    # 'info': {'description': 'A minimal gist API',
    #         'title': 'Gisty',
    #         'version': '1.0.0'},
    # 'parameters': {},
    # 'paths': {},
    # 'swagger': '2.0',
    # 'tags': []}

Our application will have a Flask route for the gist detail endpoint.

We'll add some YAML in the docstring to add response information.

.. code-block:: python

    from flask import Flask

    app = Flask(__name__)

    # NOTE: Plugins may inspect docstrings to gather more information for the spec
    @app.route('/gists/<gist_id>')
    def gist_detail(gist_id):
        """Gist detail view.
        ---
        get:
            parameters:
                - in: path
                  schema: GistParameter
            responses:
                200:
                    schema: GistSchema
        """
        return 'details about gist {}'.format(gist_id)

The Flask plugin allows us to pass this view to `spec.add_path <apispec.APISpec.add_path>`.


.. code-block:: python

    # Since add_path inspects the view and its route,
    # we need to be in a Flask request context
    with app.test_request_context():
        spec.add_path(view=gist_detail)


Our OpenAPI spec now looks like this:

.. code-block:: python

    pprint(spec.to_dict())
    # {'definitions': {'Gist': {'properties': {'content': {'type': 'string'},
    #                                         'id': {'format': 'int32',
    #                                                 'type': 'integer'}},
    #                         'type': 'object'}},
    # 'info': {'description': 'A minimal gist API',
    #         'title': 'Gisty',
    #         'version': '1.0.0'},
    # 'parameters': {},
    # 'paths': {'/gists/{gist_id}': {'get': {'parameters': [{'format': 'int32',
    #                                                        'in': 'path',
    #                                                        'name': 'gist_id',
    #                                                        'required': True,
    #                                                        'type': 'integer'}],
    #                                        'responses': {200: {'schema': {'$ref': '#/definitions/Gist'}}}}}},
    # 'swagger': '2.0',
    # 'tags': []}

If your API uses `method-based dispatching <http://flask.pocoo.org/docs/0.12/views/#method-based-dispatching>`_, the process is similar. Note that the method no longer needs to be included in the docstring.

.. code-block:: python

    from flask.views import MethodView

    class GistApi(MethodView):
        def get(self):
            '''Gist view
            ---
            description: get a gist
            responses:
               200:
                   schema:
                       $ref: '#/definitions/Gist'
            '''
            pass

        def post(self):
            pass

    method_view = GistApi.as_view('gist')
    app.add_url_rule("/gist", view_func=method_view)
    with app.test_request_context():
        spec.add_path(view=method_view)
    print(spec.to_dict()['paths'])
    # {'/gist': {'get': {'description': 'get a gist',
    #                    'responses': {200: {'schema': {'$ref': '#/definitions/Gist'}}}},
    #            'post': {}}}
    #

By default, apispec only knows how to set the type of
built-in marshmallow fields. If you want to generate definitions for
schemas with custom fields, use the
`apispec.ext.marshmallow.MarshmallowPlugin.map_to_openapi_type` decorator.

.. code-block:: python

    from apispec import APISpec
    from apispec.ext.marshmallow import MarshmallowPlugin
    from marshmallow.fields import Integer

    ma_plugin = MarshmallowPlugin()

    spec = APISpec(
        title='Gisty',
        version='1.0.0',
        openapi_version='2.0',
        info=dict(
            description='A minimal gist API'
        ),
        plugins=[ma_plugin]
    )


    @ma_plugin.map_to_openapi_type('string', 'uuid')
    class MyCustomField(Integer):
        # ...

    @ma_plugin.map_to_openapi_type(Integer)  # will map to ('integer', 'int32')
    class MyCustomFieldThatsKindaLikeAnInteger(Integer):
        # ...



Next Steps
----------

You now know how to use plugins. The next section will show you how to write plugins: :doc:`Writing Plugins <writing_plugins>`.
