*******
apispec
*******

Release v\ |version| (:doc:`Changelog <changelog>`)

A pluggable API specification generator. Currently supports the `OpenAPI Specification <https://github.com/OAI/OpenAPI-Specification>`_ (f.k.a. the Swagger specification).

Features
========

- Supports the OpenAPI Specification (versions 2 and 3)
- Framework-agnostic
- Built-in support for `marshmallow <https://marshmallow.readthedocs.io/>`_
- Utilities for parsing docstrings

Example Application
===================

.. code-block:: python

    from apispec import APISpec
    from apispec.ext.marshmallow import MarshmallowPlugin
    from apispec_webframeworks.flask import FlaskPlugin
    from flask import Flask, jsonify
    from marshmallow import Schema, fields


    # Create an APISpec
    spec = APISpec(
        title="Swagger Petstore",
        version="1.0.0",
        openapi_version="3.0.2",
        plugins=[FlaskPlugin(), MarshmallowPlugin()],
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


    @app.route("/random")
    def random_pet():
        """A cute furry animal endpoint.
        ---
        get:
          description: Get a random pet
          responses:
            200:
              content:
                application/json:
                  schema: PetSchema
        """
        pet = get_random_pet()
        return jsonify(PetSchema().dump(pet).data)


    # Register entities and paths
    spec.components.schema("Category", schema=CategorySchema)
    spec.components.schema("Pet", schema=PetSchema)
    with app.test_request_context():
        spec.path(view=random_pet)


Generated OpenAPI Spec
----------------------

.. code-block:: python

    import json

    print(json.dumps(spec.to_dict(), indent=2))
    # {
    #   "paths": {
    #     "/random": {
    #       "get": {
    #         "description": "Get a random pet",
    #         "responses": {
    #           "200": {
    #             "content": {
    #               "application/json": {
    #                 "schema": {
    #                   "$ref": "#/components/schemas/Pet"
    #                 }
    #               }
    #             }
    #           }
    #         }
    #       }
    #     }
    #   },
    #   "tags": [],
    #   "info": {
    #     "title": "Swagger Petstore",
    #     "version": "1.0.0"
    #   },
    #   "openapi": "3.0.2",
    #   "components": {
    #     "parameters": {},
    #     "responses": {},
    #     "schemas": {
    #       "Category": {
    #         "type": "object",
    #         "properties": {
    #           "name": {
    #             "type": "string"
    #           },
    #           "id": {
    #             "type": "integer",
    #             "format": "int32"
    #           }
    #         },
    #         "required": [
    #           "name"
    #         ]
    #       },
    #       "Pet": {
    #         "type": "object",
    #         "properties": {
    #           "name": {
    #             "type": "string"
    #           },
    #           "category": {
    #             "type": "array",
    #             "items": {
    #               "$ref": "#/components/schemas/Category"
    #             }
    #           }
    #         }
    #       }
    #     }
    #   }
    # }

    print(spec.to_yaml())
    # components:
    #   parameters: {}
    #   responses: {}
    #   schemas:
    #     Category:
    #       properties:
    #         id: {format: int32, type: integer}
    #         name: {type: string}
    #       required: [name]
    #       type: object
    #     Pet:
    #       properties:
    #         category:
    #           items: {$ref: '#/components/schemas/Category'}
    #           type: array
    #         name: {type: string}
    #       type: object
    # info: {title: Swagger Petstore, version: 1.0.0}
    # openapi: 3.0.2
    # paths:
    #   /random:
    #     get:
    #       description: Get a random pet
    #       responses:
    #         200:
    #           content:
    #             application/json:
    #               schema: {$ref: '#/components/schemas/Pet'}
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
   upgrading
   ecosystem
   authors
   contributing
   license
