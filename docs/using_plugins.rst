.. _using_plugins:

Using Plugins
=============

What is an apispec "plugin"?
----------------------------

An apispec *plugin* is a Python module that provides helpers for generating OpenAPI entities from objects in your application.

A plugin may modify the behavior of `APISpec <apispec.APISpec>` methods so that they can take your application's objects as input.

Enabling Plugins
----------------

To enable a plugin, pass its import path to the constructor of `APISpec <apispec.APISpec>`.

.. code-block:: python
    :emphasize-lines: 9

    from apispec import APISpec

    spec = APISpec(
        title='Gisty',
        version='1.0.0',
        info=dict(
            description='A minimal gist API'
        ),
        plugins=['apispec.ext.marshmallow']
    )


Alternatively, you can use `setup_plugin <apispec.APISpec.setup_plugin>`.

.. code-block:: python

    spec.setup_plugin('apispec.ext.marshmallow')

Example: Flask and Marshmallow Plugins
--------------------------------------

The bundled marshmallow plugin (`apispec.ext.marshmallow`) provides helpers for generating OpenAPI schema and parameter objects from `marshmallow <https://marshmallow.readthedocs.io/en/latest/>`_ schemas and fields.

The bundled Flask plugin (`apispec.ext.flask`) provides helpers for generating path objects from view functions.

Let's recreate the spec from the :ref:`Quickstart guide <quickstart>` using these two plugins.

.. code-block:: python

    from apispec import APISpec

    spec = APISpec(
        title='Gisty',
        version='1.0.0',
        info=dict(
            description='A minimal gist API'
        ),
        plugins=[
            'apispec.ext.flask',
            'apispec.ext.marshmallow'
        ]
    )


Our application will have a marshmallow `Schema <marshmallow.Schema>` for gists.

.. code-block:: python

    from marshmallow import Schema, fields

    class GistSchema(Schema):
        id = fields.Int()
        content = fields.Str()


The marshmallow plugin allows us to pass this `Schema` to `spec.definition <apispec.APISpec.definition>`.


.. code-block:: python

    spec.definition('Gist', schema=GistSchema)

The definition is now added to the spec.

.. code-block:: python
    :emphasize-lines: 4,5

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
            responses:
                200:
                    schema: GistSchema
        """
        return 'details about gist {}'.format(gist_id)

The Flask plugin allows us to pass this view to `spec.add_path <apispec.APISpec.add_path>`.


.. code-block:: python

    # Since add_path inspects the view and its route,
    # we need to be in a Flask request context
    ctx = app.test_request_context()
    ctx.push()

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
    # 'paths': {'/gists/{gist_id}': {'get': {'responses': {200: {'schema': {'$ref': '#/definitions/Gist'}}}}}},
    # 'swagger': '2.0',
    # 'tags': []}

Next Steps
----------

You now know how to use plugins. The next section will show you how to write plugins: :ref:`Writing Plugins <writing_plugins>`
