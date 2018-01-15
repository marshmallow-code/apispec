*******
apispec
*******

Release v\ |version| (:ref:`Changelog <changelog>`)

A pluggable API specification generator. Currently supports the `OpenAPI specification <http://swagger.io/specification/>`_ (f.k.a. Swagger 2.0).

Features
========

- Supports OpenAPI 2.0 specification (f.k.a. Swagger)
- Framework-agnostic
- Includes plugins for `marshmallow <https://marshmallow.readthedocs.io/>`_, `Flask <http://flask.pocoo.org/>`_, `Tornado <http://www.tornadoweb.org/>`_, and `bottle <http://bottlepy.org/docs/dev/>`_.
- Utilities for parsing docstrings

Example Application
===================

.. code-block:: python

    from apispec import APISpec
    from flask import Flask, jsonify
    from marshmallow import Schema, fields

    # Create an APISpec
    spec = APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        plugins=[
            'apispec.ext.flask',
            'apispec.ext.marshmallow',
        ],
    )

    # Optional marshmallow support
    class CategorySchema(Schema):
        id = fields.Int()
        name = fields.Str(required=True)

    class PetSchema(Schema):
        category = fields.Nested(CategorySchema, many=True)
        name = fields.Str()

    # Optional Flask support
    app = Flask(__name__)

    @app.route('/random')
    def random_pet():
        """A cute furry animal endpoint.
        ---
        get:
            description: Get a random pet
            responses:
                200:
                    description: A pet to be returned
                    schema: PetSchema
        """
        pet = get_random_pet()
        return jsonify(PetSchema().dump(pet).data)

    # Register entities and paths
    spec.definition('Category', schema=CategorySchema)
    spec.definition('Pet', schema=PetSchema)
    with app.test_request_context():
        spec.add_path(view=random_pet)


Generated OpenAPI Spec
----------------------

.. code-block:: python

    spec.to_dict()
    # {
    #   "info": {
    #     "title": "Swagger Petstore",
    #     "version": "1.0.0"
    #   },
    #   "swagger": "2.0",
    #   "paths": {
    #     "/random": {
    #       "get": {
    #         "description": "A cute furry animal endpoint.",
    #         "responses": {
    #           "200": {
    #             "schema": {
    #               "$ref": "#/definitions/Pet"
    #             },
    #             "description": "A pet to be returned"
    #           }
    #         },
    #       }
    #     }
    #   },
    #   "definitions": {
    #     "Pet": {
    #       "properties": {
    #         "category": {
    #           "type": "array",
    #           "items": {
    #             "$ref": "#/definitions/Category"
    #           }
    #         },
    #         "name": {
    #           "type": "string"
    #         }
    #       }
    #     },
    #     "Category": {
    #       "required": [
    #         "name"
    #       ],
    #       "properties": {
    #         "name": {
    #           "type": "string"
    #         },
    #         "id": {
    #           "type": "integer",
    #           "format": "int32"
    #         }
    #       }
    #     }
    #   },
    # }

    spec.to_yaml()
    # definitions:
    #   Pet:
    #     enum: [name, photoUrls]
    #     properties:
    #       id: {format: int64, type: integer}
    #       name: {example: doggie, type: string}
    # info: {description: 'This is a sample Petstore server.  You can find out more ', title: Swagger Petstore, version: 1.0.0}
    # parameters: {}
    # paths: {}
    # security:
    # - apiKey: []
    # swagger: '2.0'
    # tags: []

User Guide
==========

.. toctree::
    :maxdepth: 2

    install
    quickstart
    using_plugins
    writing_plugins
    special_topics

API Reference
=============

.. toctree::
    :maxdepth: 2

    api_core
    api_ext

Project Links
=============

- `apispec @ GitHub <https://github.com/marshmallow-code/apispec>`_
- `Issue Tracker <https://github.com/marshmallow-code/apispec/issues>`_

Project Info
============

.. toctree::
   :maxdepth: 1

   changelog
   ecosystem
   authors
   contributing
   license
