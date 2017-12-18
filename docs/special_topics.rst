.. _special_topics:

Special Topics
==============

Solutions to specific problems are documented here.


Adding Additional Fields To Schema Objects
------------------------------------------

To add additional fields (e.g. ``"discriminator"``) to Schema objects generated from `APISpec.definition <apispec.APISpec.definition>` , pass the ``extra_fields`` argument.

.. code-block:: python

    properties = {
        'id': {'type': 'integer', 'format': 'int64'},
        'name': {'type': 'string', 'example': 'doggie'},
    }

    spec.definition('Pet', properties=properties, extra_fields={'discriminator': 'petType'})


.. note::
    Be careful about the input that you pass to ``extra_fields``. ``apispec`` will not guarantee that the passed fields are valid against the OpenAPI spec.

Rendering to YAML or JSON
-------------------------

YAML
++++

`apispec` provides proper a YAML dumper so you can serialize directly your spec
in YAML.

::

    pip install PyYAML


.. code-block:: python

    spec.to_yaml()


JSON
++++

You can directly serialize the to JSON the dictionary provided by `apispec` for
your spec.

.. code-block:: python

    import json

    json.dumps(spec.to_dict())
