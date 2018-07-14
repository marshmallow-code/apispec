Writing Plugins
===============

A plugins is a subclass of `apispec.plugin.BasePlugin`.


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

`BasePlugin` has an `init_spec` method that `APISpec` calls on each plugin at initialization with the spec object itself as parameter. It is no-op by default, but a plugin may override it to access and store useful information from the spec object.

A typical use case is conditional code depending on the OpenAPI version, which is stored as ``openapi_version`` attribute of the spec object. See source code for `apispec.ext.marshmallow.MarshmallowPlugin </_modules/apispec/ext/marshmallow.html>`_ for an example.

Note that the OpenAPI version is stored in the spec object as an `apispec.utils.OpenAPIVersion`. An ``OpenAPIVersion`` instance provides the version as string as well as shortcuts to version digits.


Example: Docstring-parsing Plugin
---------------------------------

Here's a plugin example involving conditional processing depending on the OpenAPI version:

.. code-block:: python

    # docplugin.py

    from apispec import Path, BasePlugin
    from apispec.utils import load_operations_from_docstring

    class DocPlugin(BasePlugin):

        def init_spec(self, spec):
            super(DocPlugin, self).init_spec(spec)
            self.openapi_major_version = spec.openapi_version.major

        def path_helper(self, path, func, **kwargs):
            """Path helper that parses docstrings for operations. Adds a
            ``func`` parameter to `apispec.APISpec.add_path`.
            """
            operations = load_operations_from_docstring(func.__doc__)
            # Apply conditional processing
            if self.openapi_major_version < 3:
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

* Consult the :doc:`Core API docs <api_core>` for `BasePlugin <apispec.plugin.BasePlugin>`
* View the source for apispec's bundled plugins, e.g. `apispec.ext.flask.FlaskPlugin. </_modules/apispec/ext/flask.html>`_
* Check out some projects using apispec: https://github.com/marshmallow-code/apispec/wiki/Ecosystem
