*******
apispec
*******

.. image:: https://badgen.net/pypi/v/apispec
    :target: https://pypi.org/project/apispec/
    :alt: PyPI version

.. image:: https://dev.azure.com/sloria/sloria/_apis/build/status/marshmallow-code.apispec?branchName=dev
    :target: https://dev.azure.com/sloria/sloria/_build/latest?definitionId=8&branchName=dev
    :alt: Build status

.. image:: https://readthedocs.org/projects/apispec/badge/
   :target: https://apispec.readthedocs.io/
   :alt: Documentation

.. image:: https://badgen.net/badge/marshmallow/2,3?list=1
    :target: https://marshmallow.readthedocs.io/en/latest/upgrading.html
    :alt: marshmallow 2/3 compatible

.. image:: https://badgen.net/badge/OAS/2,3?list=1&color=cyan
    :target: https://github.com/OAI/OpenAPI-Specification
    :alt: OpenAPI Specification 2/3 compatible

.. image:: https://badgen.net/badge/code%20style/black/000
    :target: https://github.com/ambv/black
    :alt: code style: black

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
        category = fields.List(fields.Nested(CategorySchema))
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
        return PetSchema().dump(pet)


    # Register the path and the entities within it
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


Documentation
=============

Documentation is available at https://apispec.readthedocs.io/ .

Ecosystem
=========

A list of apispec-related libraries can be found at the GitHub wiki here:

https://github.com/marshmallow-code/apispec/wiki/Ecosystem

Support apispec
===============

apispec is maintained by a group of
`volunteers <https://apispec.readthedocs.io/en/latest/authors.html>`_.
If you'd like to support the future of the project, please consider
contributing to our Open Collective:

.. image:: https://opencollective.com/marshmallow/donate/button.png
    :target: https://opencollective.com/marshmallow
    :width: 200
    :alt: Donate to our collective

Professional Support
====================

Professionally-supported apispec is available through the
`Tidelift Subscription <https://tidelift.com/subscription/pkg/pypi-apispec?utm_source=pypi-apispec&utm_medium=referral&utm_campaign=readme>`_.

Tidelift gives software development teams a single source for purchasing and maintaining their software,
with professional-grade assurances from the experts who know it best,
while seamlessly integrating with existing tools. [`Get professional support`_]

.. _`Get professional support`: https://tidelift.com/subscription/pkg/pypi-apispec?utm_source=pypi-apispec&utm_medium=referral&utm_campaign=readme

.. image:: https://user-images.githubusercontent.com/2379650/45126032-50b69880-b13f-11e8-9c2c-abd16c433495.png
    :target: https://tidelift.com/subscription/pkg/pypi-apispec?utm_source=pypi-apispec&utm_medium=referral&utm_campaign=readme
    :alt: Get supported apispec with Tidelift

Security Contact Information
============================

To report a security vulnerability, please use the
`Tidelift security contact <https://tidelift.com/security>`_.
Tidelift will coordinate the fix and disclosure.

Project Links
=============

- Docs: https://apispec.readthedocs.io/
- Changelog: https://apispec.readthedocs.io/en/latest/changelog.html
- Contributing Guidelines: https://apispec.readthedocs.io/en/latest/contributing.html
- PyPI: https://pypi.python.org/pypi/apispec
- Issues: https://github.com/marshmallow-code/apispec/issues


License
=======

MIT licensed. See the bundled `LICENSE <https://github.com/marshmallow-code/apispec/blob/dev/LICENSE>`_ file for more details.
