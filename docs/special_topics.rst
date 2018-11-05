Special Topics
==============

Solutions to specific problems are documented here.


Adding Additional Fields To Schema Objects
------------------------------------------

To add additional fields (e.g. ``"discriminator"``) to Schema objects generated from `spec.components.schema <apispec.core.Components.schema>` , pass the ``extra_fields`` argument.

.. code-block:: python

    properties = {
        'id': {'type': 'integer', 'format': 'int64'},
        'name': {'type': 'string', 'example': 'doggie'},
    }

    spec.components.schema('Pet', properties=properties, extra_fields={'discriminator': 'petType'})


.. note::
    Be careful about the input that you pass to ``extra_fields``. ``apispec`` will not guarantee that the passed fields are valid against the OpenAPI spec.

Rendering to YAML or JSON
-------------------------

YAML
++++

.. code-block:: python

    spec.to_yaml()


.. note::
    `to_yaml <apispec.APISpec.to_yaml>` requires `PyYAML` to be installed. You can install
    apispec with YAML support using: ::

        pip install 'apispec[yaml]'


JSON
++++

.. code-block:: python

    import json

    json.dumps(spec.to_dict())

Documenting Top-level Components
--------------------------------

The ``APISpec`` object contains helpers to add top-level components.

To add a schema (a.k.a. "definition" in OpenAPI v2 termionology), use
`spec.components.schema <apispec.core.Components.schema>`.

Likewise, parameters and responses can be added using
`spec.components.parameter <apispec.core.Components.parameter>` and
`spec.components.response <apispec.core.Components.response>`.

To add other top-level objects, pass them to the ``APISpec`` as keyword arguments.

Here is an example that includes a `Security Scheme Object <https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.1.md#securitySchemeObject>`_.

.. code-block:: python

    import yaml
    from apispec import APISpec
    from apispec.ext.marshmallow import MarshmallowPlugin
    from apispec.utils import validate_swagger

    OPENAPI_SPEC = """
    openapi: 3.0.1
    info:
      description: Server API document
      title: Server API
      version: 1.0.0
    servers:
    - url: http://localhost:{port}/
      description: The development API server
      variables:
        port:
          enum:
          - '3000'
          - '8888'
          default: '3000'
    components:
      securitySchemes:
        bearerAuth:
          type: http
          scheme: bearer
          bearerFormat: JWT
    """

    settings = yaml.safe_load(OPENAPI_SPEC)
    # retrieve  title, version, and openapi version
    title = settings['info'].pop('title')
    spec_version = settings['info'].pop('version')
    openapi_version = settings.pop('openapi')

    spec = APISpec(
        title=title,
        version=spec_version,
        openapi_version=openapi_version,
        plugins=(
            MarshmallowPlugin(),
        ),
        **settings
    )

    validate_swagger(spec)


When adding components, the main advantage of using dedicated methods over
passing them as kwargs is the ability to use plugin helpers. For instance,
`MarshmallowPlugin <apispec.ext.marshmallow.MarshmallowPlugin>` has helpers to
resolve schemas in parameters and responses.
