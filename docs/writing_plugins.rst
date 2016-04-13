.. _writing_plugins:

Writing Plugins
===============

Helper Functions
----------------

Plugins are comprised of "helper" functions that augment the behavior of `apispec.APISpec` methods.

There are three types of helper functions:

* Definition helpers
* Path helpers
* Response helpers

Each helper function type modifies a different `apispec.APISpec` method. For example, path helpers modify `apispec.APISpec.add_path`.

A helper function may look something like this:

.. code-block:: python

    from apispec import Path
    from apispec.utils import load_operations_from_docstring

    def docstring_path_helper(spec, path, func, **kwargs):
        """Path helper that parses docstrings for operations. Adds a
        ``func`` parameter to `apispec.APISpec.add_path`.
        """
        operations = load_operations_from_docstring(func.__doc__)
        return Path(path=path, operations=operations)


The ``setup`` Function
----------------------

All plugins **must** define a ``setup`` function that receives an `apispec.APISpec` instance as its only argument. The ``setup`` function registers your plugin's helper functions with the ``spec``.


.. code-block:: python

    def setup(spec):
        spec.register_definition_helper(my_definition_helper)
        spec.register_path_helper(my_path_helper)

Example: Docstring-parsing Plugin
---------------------------------

Putting the helper and the ``setup`` functions together, our full plugin would look like this:

.. code-block:: python

    # docplugin.py

    from apispec import Path
    from apispec.utils import load_operations_from_docstring

    def docstring_path_helper(spec, path, func, **kwargs):
        """Path helper that parses docstrings for operations. Adds a
        ``func`` parameter to `apispec.APISpec.add_path`.
        """
        operations = load_operations_from_docstring(func.__doc__)
        return Path(path=path, operations=operations)

    def setup(spec):
        spec.register_path_helper(docstring_path_helper)

To use the plugin:

.. code-block:: python

    from apispec import APISpec

    spec = APISpec(
        title='Gisty',
        version='1.0.0',
        plugins=[
            'docplugin',
        ]
    )

    def gist_detail(gist_id):
        """Gist detail view.
        ---
        get:
            responses:
                200:
                    schema: '#/definitions/Gist'
        """
        pass

    spec.add_path(path='/gists/{gist_id}', func=gist_detail)
    print(spec.to_dict()['paths'])
    # {'/gists/{gist_id}': {'get': {'responses': {200: {'schema': '#/definitions/Gist'}}}}}


Next Steps
----------

* To learn more about how to write helper functions, consult the :ref:`Core API docs <core_api>` for `register_definition_helper <apispec.APISpec.register_definition_helper>`, `register_path_helper <apispec.APISpec.register_path_helper>`, and `register_response_helper <apispec.APISpec.register_response_helper>`
* View the source for apispec's bundled plugins, e.g. `apispec.ext.flask </_modules/apispec/ext/flask.html>`_
* Check out some projects using apispec: https://github.com/marshmallow-code/apispec/wiki/Ecosystem
