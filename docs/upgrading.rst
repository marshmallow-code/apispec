Upgrading to Newer Releases
===========================

This section documents migration paths to new releases.

Upgrading to 2.0.0
------------------

plugin helpers must accept extra `**kwargs`
*******************************************

Since custom plugins helpers may define extra kwargs and those kwargs are passed
to all plugin helpers by :meth:`APISpec.path <APISpec.path>`, all plugins should
accept unknown kwargs.

The example plugin below defines an additional `func` argument and accepts extra
`**kwargs`.

.. code-block:: python
    :emphasize-lines: 2

    class MyPlugin(BasePlugin):
        def path_helper(self, path, func, **kwargs):
            """Path helper that parses docstrings for operations. Adds a
            ``func`` parameter to `apispec.APISpec.path`.
            """
            operations = load_operations_from_docstring(func.__doc__)
            return Path(path=path, operations=operations)

Components must be referenced by ID, not full path
**************************************************

While apispec 1.x would let the user reference components by path or ID,
apispec 2.x only accepts references by ID.

.. code-block:: python

    # apispec<2.0.0
    spec.path(
        path="/gist/{gist_id}",
        operations=dict(
            get=dict(
                responses={
                    "200": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/definitions/Gist"}}
                        }
                    }
                }
            )
        ),
    )

    # apispec>=2.0.0
    spec.path(
        path="/gist/{gist_id}",
        operations=dict(
            get=dict(
                responses={"200": {"content": {"application/json": {"schema": "Gist"}}}}
            )
        ),
    )

References by ID are accepted by both apispec 1.x ad 2.x and are a better
choice because they delegate the creation of the full component path to apispec.
This allows more flexibility as apispec creates the component path according to
the OpenAPI version.

Upgrading to 1.0.0
------------------

``openapi_version`` Is Required
*******************************

``openapi_version`` no longer defaults to ``"2.0"``. It is now a
required argument.

.. code-block:: python
    :emphasize-lines: 4

    spec = APISpec(
        title="Swagger Petstore",
        version="1.0.0",
        openapi_version="2.0",  # or "3.0.2"
        plugins=[MarshmallowPlugin()],
    )

Web Framework Plugins Packaged Separately
*****************************************

``apispec.ext.flask``, ``apispec.ext.bottle``, and
``apispec.ext.tornado`` have been moved to a a separate package,
`apispec-webframeworks <https://github.com/marshmallow-code/apispec-webframeworks>`_.

If you use these plugins, install ``apispec-webframeworks`` with
``pip``:

::

    $ pip install apispec-webframeworks

Then, update your imports:

.. code-block:: python

    # apispec<1.0.0
    from apispec.ext.flask import FlaskPlugin

    # apispec>=1.0.0
    from apispec_webframeworks.flask import FlaskPlugin


YAML Support Is Optional
************************

YAML functionality is now optional. To install with YAML support:

::

    $ pip install 'apispec[yaml]'

You will need to do this if you use ``apispec-webframeworks`` or call
`APISpec.to_yaml <apispec.APISpec.to_yaml>` in your code.


Registering Entities
********************

Methods for registering OAS entities are changed to the noun form
for internal consistency and for consistency with OAS v3 terminology.

.. code-block:: python

    # apispec<1.0.0
    spec.add_tag({"name": "Pet", "description": "Operations on pets"})
    spec.add_path("/pets/", operations={...})
    spec.definition("Pet", properties={...})
    spec.add_parameter("PetID", "path", {...})

    # apispec>=1.0.0
    spec.tag({"name": "Pet", "description": "Operations on pets"})
    spec.path("/pets/", operations={...})
    spec.components.schema("Pet", {"properties": {...}})
    spec.components.parameter("PetID", "path", {...})

Adding Additional Fields to Schemas
***********************************

The ``extra_fields`` parameter to ``schema`` is removed. It is no longer
necessary. Pass all fields in to the component ``dict``.

.. code-block:: python

    # <1.0.0
    spec.definition("Pet", schema=PetSchema, extra_fields={"discriminator": "name"})

    # >=1.0.0
    spec.components.schema("Pet", schema=PetSchema, component={"discriminator": "name"})


Nested Schemas Are Referenced
*****************************

When using the `MarshmallowPlugin
<apispec.ext.marshmallow.MarshmallowPlugin>`, nested `Schema
<marshmallow.Schema>` classes are referenced (with ``"$ref"``) in the output spec.
By default, the name in the spec will be the class name with the "Schema" suffix
removed, e.g. ``fields.Nested(PetSchema())`` -> ``"#components/schemas/Pet"``.

The `ref` argument to `fields.Nested <marshmallow.fields.Nested>`_ is no
longer respected.


.. code-block:: python

    # apispec<1.0.0
    class PetSchema(Schema):
        owner = fields.Nested(
            HumanSchema,
            # `ref` has no effect in 1.0.0. Remove.
            ref="#components/schemas/Human",
        )


    # apispec>=1.0.0
    class PetSchema(Schema):
        owner = fields.Nested(HumanSchema)


.. seealso::

    This behavior is customizable. See :ref:`marshmallow_nested_schemas`.
