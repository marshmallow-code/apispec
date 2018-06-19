.. _writing_plugins:

Writing Plugins
===============

A plugins is a child class of `apispec.plugin.BasePlugin`.


Helper Methods
--------------

Plugins provide "helper" methods that augment the behavior of `apispec.APISpec` methods.

There are four types of helper methods:

* Definition helpers
* Path helpers
* Operation helpers
* Response helpers

Each helper function type modifies a different `apispec.APISpec` method. For example, path helpers modify `apispec.APISpec.add_path`.


A plugin with a path helper function may look something like this:

.. code-block:: python

    from apispec import Path, BasePlugin
    from apispec.utils import load_operations_from_docstring

    class MyPlugin(BasePlugin):

        def path_helper(self, path, func, **kwargs):
            """Path helper that parses docstrings for operations. Adds a
            ``func`` parameter to `apispec.APISpec.add_path`.
            """
            operations = load_operations_from_docstring(func.__doc__)
            return Path(path=path, operations=operations)


The ``init_spec`` Method
------------------------

`BasePlugin` has an `init_spec` method that is called by the `APISpec` object at initialization.

This method stores the APISpec object as attribute `spec` of the plugin object, so that every helper method has access to the spec object.

A typical use case is for conditional code depending on the OpenAPI version, which is stored in `spec` as an `apispec.utils.OpenAPIVersion` object providing shortcuts to version digits.


Example: Docstring-parsing Plugin
---------------------------------

Here's a plugin example involving conditional processing depending on the OpenAPI version:

.. code-block:: python

    # docplugin.py

    from apispec import Path, BasePlugin
    from apispec.utils import load_operations_from_docstring

    class DocPlugin(BasePlugin):

        def path_helper(self, path, func, **kwargs):
            """Path helper that parses docstrings for operations. Adds a
            ``func`` parameter to `apispec.APISpec.add_path`.
            """
            openapi_major_version = self.spec.openapi_version.major
            operations = load_operations_from_docstring(func.__doc__)
            # Apply conditional processing
            if openapi_major_version < 3:
                [...]
            else:
                [...]
            return Path(path=path, operations=operations)


To use the plugin:

.. code-block:: python

    from apispec import APISpec
    from docplugin import DocPlugin

    spec = APISpec(
        title='Gisty',
        version='1.0.0',
        plugins=[Docplugin()]
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

To learn more about how to write plugins

* Consult the :ref:`Core API docs <core_api>` for `BasePlugin <apispec.plugin.BasePlugin>`
* View the source for apispec's bundled plugins, e.g. `apispec.ext.flask.FlaskPlugin. </_modules/apispec/ext/flask.html>`_
* Check out some projects using apispec: https://github.com/marshmallow-code/apispec/wiki/Ecosystem
