*******
apispec
*******

.. image:: https://badgen.net/pypi/v/apispec
    :target: https://badge.fury.io/py/apispec
    :alt: PyPI version

.. image:: https://badgen.net/travis/marshmallow-code/apispec/dev
    :target: https://travis-ci.org/marshmallow-code/apispec
    :alt: TravisCI build status

.. image:: https://readthedocs.org/projects/apispec/badge/
   :target: https://apispec.readthedocs.io/
   :alt: Documentation

.. image:: https://badgen.net/badge/marshmallow/2,3?list=1
    :target: https://marshmallow.readthedocs.io/en/latest/upgrading.html
    :alt: marshmallow 2/3 compatible

A pluggable API specification generator. Currently supports the `OpenAPI Specification <https://github.com/OAI/OpenAPI-Specification>`_ (f.k.a. the Swagger specification).

Features
========

- Supports OpenAPI Specification version 2 (f.k.a. the Swagger specification)
  with limited support for version 3
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
        title='Swagger Petstore',
        version='1.0.0',
        openapi_version='2.0',
        plugins=[
            FlaskPlugin(),
            MarshmallowPlugin(),
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
        spec.path(view=random_pet)


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


Documentation
=============

Documentation is available at http://apispec.readthedocs.io/ .

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

License
=======

MIT licensed. See the bundled `LICENSE <https://github.com/marshmallow-code/apispec/blob/dev/LICENSE>`_ file for more details.
