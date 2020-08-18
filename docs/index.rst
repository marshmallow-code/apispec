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

    import uuid

    from apispec import APISpec
    from apispec.ext.marshmallow import MarshmallowPlugin
    from apispec_webframeworks.flask import FlaskPlugin
    from flask import Flask
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
        categories = fields.List(fields.Nested(CategorySchema))
        name = fields.Str()


    # Optional security scheme support
    api_key_scheme = {"type": "apiKey", "in": "header", "name": "X-API-Key"}
    spec.components.security_scheme("ApiKeyAuth", api_key_scheme)


    # Optional Flask support
    app = Flask(__name__)


    @app.route("/random")
    def random_pet():
        """A cute furry animal endpoint.
        ---
        get:
          description: Get a random pet
          security:
            - ApiKeyAuth: []
          responses:
            200:
              description: Return a pet
              content:
                application/json:
                  schema: PetSchema
        """
        # Hardcoded example data
        pet_data = {
            "name": "sample_pet_" + str(uuid.uuid1()),
            "categories": [{"id": 1, "name": "sample_category"}],
        }
        return PetSchema().dump(pet_data)


    # Register the path and the entities within it
    with app.test_request_context():
        spec.path(view=random_pet)


Generated OpenAPI Spec
----------------------

.. code-block:: python

    import json

    print(json.dumps(spec.to_dict(), indent=2))
    # {
    #   "info": {
    #     "title": "Swagger Petstore",
    #     "version": "1.0.0"
    #   },
    #   "openapi": "3.0.2",
    #   "components": {
    #     "schemas": {
    #       "Category": {
    #         "type": "object",
    #         "properties": {
    #           "id": {
    #             "type": "integer",
    #             "format": "int32"
    #           },
    #           "name": {
    #             "type": "string"
    #           }
    #         },
    #         "required": [
    #           "name"
    #         ]
    #       },
    #       "Pet": {
    #         "type": "object",
    #         "properties": {
    #           "categories": {
    #             "type": "array",
    #             "items": {
    #               "$ref": "#/components/schemas/Category"
    #             }
    #           },
    #           "name": {
    #             "type": "string"
    #           }
    #         }
    #       },
    #     }
    #   },
    #   "securitySchemes": {
    #      "ApiKeyAuth": {
    #        "type": "apiKey",
    #        "in": "header",
    #        "name": "X-API-Key"
    #     }
    #   },
    #   "paths": {
    #     "/random": {
    #       "get": {
    #         "description": "Get a random pet",
    #         "security": [
    #           {
    #             "ApiKeyAuth": []
    #           }
    #         ],
    #         "responses": {
    #           "200": {
    #             "description": "Return a pet",
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
    # }

    print(spec.to_yaml())
    # info:
    #   title: Swagger Petstore
    #   version: 1.0.0
    # openapi: 3.0.2
    # components:
    #   schemas:
    #     Category:
    #       properties:
    #         id:
    #           format: int32
    #           type: integer
    #         name:
    #           type: string
    #       required:
    #       - name
    #       type: object
    #     Pet:
    #       properties:
    #         categories:
    #           items:
    #             $ref: '#/components/schemas/Category'
    #           type: array
    #         name:
    #           type: string
    #       type: object
    #   securitySchemes:
    #     ApiKeyAuth:
    #       in: header
    #       name: X-API-KEY
    #       type: apiKey
    # paths:
    #   /random:
    #     get:
    #       description: Get a random pet
    #       responses:
    #         '200':
    #           content:
    #             application/json:
    #               schema:
    #                 $ref: '#/components/schemas/Pet'
    #           description: Return a pet
    #       security:
    #       - ApiKeyAuth: []

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
