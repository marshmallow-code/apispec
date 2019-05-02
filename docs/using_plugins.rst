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
    :emphasize-lines: 9

    from apispec import APISpec
    from apispec.ext.marshmallow import MarshmallowPlugin

    spec = APISpec(
        title="Gisty",
        version="1.0.0",
        openapi_version="3.0.2",
        info=dict(description="A minimal gist API"),
        plugins=[MarshmallowPlugin()],
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
    from apispec_webframeworks.flask import FlaskPlugin

    spec = APISpec(
        title="Gisty",
        version="1.0.0",
        openapi_version="3.0.2",
        info=dict(description="A minimal gist API"),
        plugins=[FlaskPlugin(), MarshmallowPlugin()],
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
`spec.components.schema <apispec.core.Components.schema>`.


.. code-block:: python

    spec.components.schema("Gist", schema=GistSchema)

The schema is now added to the spec.

.. code-block:: python

    from pprint import pprint

    pprint(spec.to_dict())
    # {'components': {'parameters': {}, 'responses': {}, 'schemas': {}},
    #  'info': {'description': 'A minimal gist API',
    #           'title': 'Gisty',
    #           'version': '1.0.0'},
    #  'openapi': '3.0.2',
    #  'paths': OrderedDict(),
    #  'tags': []}

Our application will have a Flask route for the gist detail endpoint.

We'll add some YAML in the docstring to add response information.

.. code-block:: python

    from flask import Flask

    app = Flask(__name__)

    # NOTE: Plugins may inspect docstrings to gather more information for the spec
    @app.route("/gists/<gist_id>")
    def gist_detail(gist_id):
        """Gist detail view.
        ---
        get:
          parameters:
          - in: path
            schema: GistParameter
          responses:
            200:
              content:
                application/json:
                  schema: GistSchema
        """
        return "details about gist {}".format(gist_id)

The Flask plugin allows us to pass this view to `spec.path <apispec.APISpec.path>`.


.. code-block:: python

    # Since path inspects the view and its route,
    # we need to be in a Flask request context
    with app.test_request_context():
        spec.path(view=gist_detail)


Our OpenAPI spec now looks like this:

.. code-block:: python

    pprint(spec.to_dict())
    # {'components': {'parameters': {},
    #                 'responses': {},
    #                 'schemas': {'Gist': {'properties': {'content': {'type': 'string'},
    #                                                     'id': {'format': 'int32',
    #                                                            'type': 'integer'}},
    #                                      'type': 'object'}}},
    #  'info': {'description': 'A minimal gist API',
    #           'title': 'Gisty',
    #           'version': '1.0.0'},
    #  'openapi': '3.0.2',
    #  'paths': OrderedDict([('/gists/{gist_id}',
    #                         OrderedDict([('get',
    #                                       {'parameters': [{'in': 'path',
    #                                                        'name': 'gist_id',
    #                                                        'required': True,
    #                                                        'schema': {'format': 'int32',
    #                                                                   'type': 'integer'}}],
    #                                        'responses': {200: {'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Gist'}}}}}})]))]),
    #  'tags': []}

If your API uses `method-based dispatching <http://flask.pocoo.org/docs/0.12/views/#method-based-dispatching>`_, the process is similar. Note that the method no longer needs to be included in the docstring.

.. code-block:: python

    from flask.views import MethodView


    class GistApi(MethodView):
        def get(self):
            """Gist view
            ---
            description: Get a gist
            responses:
              200:
                content:
                  application/json:
                    schema: GistSchema
            """
            pass

        def post(self):
            pass


    method_view = GistApi.as_view("gist")
    app.add_url_rule("/gist", view_func=method_view)
    with app.test_request_context():
        spec.path(view=method_view)
    pprint(dict(spec.to_dict()["paths"]["/gist"]))
    # {'get': {'description': 'get a gist',
    #          'responses': {200: {'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Gist'}}}}}},
    #  'post': {}}


Marshmallow Plugin
------------------

.. _marshmallow_nested_schemas:

Nested Schemas
**************

By default, Marshmallow `Nested` fields are represented by a `JSON Reference object
<https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#referenceObject>`_.
If the schema has been added to the spec via `spec.components.schema <apispec.core.Components.schema>`,
the user-supplied name will be used in the reference. Otherwise apispec will
add the nested schema to the spec using an automatically resolved name for the
nested schema. The default `resolver <apispec.ext.marshmallow.resolver>`
function will resolve a name based on the schema's class `__name__`, dropping a
trailing "Schema" so that `class PetSchema(Schema)` resolves to "Pet".

To change the behavior of the name resolution simply pass a
function accepting a `Schema` class and returning a string to the plugin's
constructor. If the `schema_name_resolver` function returns a value that
evaluates to `False` in a boolean context the nested schema will not be added to
the spec and instead defined in-line.

.. note::
    A `schema_name_resolver` function must return a string name when
    working with circular-referencing schemas in order to avoid infinite
    recursion.

Schema Modifiers
****************

apispec will respect schema modifiers such as ``exclude`` and ``partial`` in the generated schema definition. If a schema is initialized with modifiers, apispec will treat each combination of modifiers as a unique schema definition.

Custom Fields
*************

apispec maps standard marshmallow fields to OpenAPI types and formats. If your
custom field subclasses a standard marshmallow `Field` class then it will
inherit the default mapping. If you want to override the OpenAPI type and format
for custom fields, use the
`map_to_openapi_type <apispec.ext.marshmallow.MarshmallowPlugin.map_to_openapi_type>`
decorator. It can be invoked with either a pair of strings providing the
OpenAPI type and format, or a marshmallow `Field` that has the desired target mapping.

.. code-block:: python

    from apispec import APISpec
    from apispec.ext.marshmallow import MarshmallowPlugin
    from marshmallow.fields import Integer, Field

    ma_plugin = MarshmallowPlugin()


    # Inherits Integer mapping of ('integer', 'int32')
    class MyCustomInteger(Integer):
        pass


    # Override Integer mapping
    @ma_plugin.map_to_openapi_type("string", "uuid")
    class MyCustomField(Integer):
        pass


    @ma_plugin.map_to_openapi_type(Integer)  # will map to ('integer', 'int32')
    class MyCustomFieldThatsKindaLikeAnInteger(Field):
        pass



Next Steps
----------

You now know how to use plugins. The next section will show you how to write plugins: :doc:`Writing Plugins <writing_plugins>`.
