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

`apispec` will only serialize your spec to a Python dictionary. Use an appropriate module to render your spec to YAML or JSON.

YAML
++++

::

    pip install PyYAML


.. code-block:: python

    import yaml

    yaml.dump(spec.to_dict())


JSON
++++

.. code-block:: python

    import json

    json.dumps(spec.to_dict())
