Writing Plugins
===============

A plugins is a subclass of `apispec.plugin.BasePlugin`.


Helper Methods
--------------

Plugins provide "helper" methods that augment the behavior of `apispec.APISpec` methods.

There are five types of helper methods:

* Schema helpers
* Parameter helpers
* Response helpers
* Path helpers
* Operation helpers

Helper functions modify `apispec.APISpec` methods. For example, path helpers modify `apispec.APISpec.path`.


A plugin with a path helper function may look something like this:

.. code-block:: python

    from apispec import Path, BasePlugin
    from apispec.utils import load_operations_from_docstring


    class MyPlugin(BasePlugin):
        def path_helper(self, path, func, **kwargs):
            """Path helper that parses docstrings for operations. Adds a
            ``func`` parameter to `apispec.APISpec.path`.
            """
            operations = load_operations_from_docstring(func.__doc__)
            return Path(path=path, operations=operations)


All plugin helpers must accept extra `**kwargs`, allowing custom plugins to define new arguments if required.

A plugin with an operation helper that adds `deprecated` flag may look like this

.. code-block:: python

   # deprecated_plugin.py

   from apispec import BasePlugin
   from apispec.compat import iteritems
   from apispec.yaml_utils import load_operations_from_docstring


   class DeprecatedPlugin(BasePlugin):
       def operation_helper(self, path, operations, **kwargs):
           """Operation helper that add `deprecated` flag if in `kwargs`
           """
           if kwargs.pop("deprecated", False) is True:
               for key, value in iteritems(operations):
                   value["deprecated"] = True


Using this plugin

.. code-block:: python

   import json
   from apispec import APISpec
   from deprecated_plugin import DeprecatedPlugin

   spec = APISpec(
       title="Gisty",
       version="1.0.0",
       openapi_version="3.0.2",
       plugins=[DeprecatedPlugin()],
   )

   # path will call operation_helper on operations
   spec.path(
       path="/gists/{gist_id}",
       operations={"get": {"responses": {"200": {"description": "standard response"}}}},
       deprecated=True,
   )
   print(json.dumps(spec.to_dict()["paths"]))
   # {"/gists/{gist_id}": {"get": {"responses": {"200": {"description": "standard response"}}, "deprecated": true}}}



The ``init_spec`` Method
------------------------

`BasePlugin` has an `init_spec` method that `APISpec` calls on each plugin at initialization with the spec object itself as parameter. It is no-op by default, but a plugin may override it to access and store useful information on the spec object.

A typical use case is conditional code depending on the OpenAPI version, which is stored as ``openapi_version`` on the `spec` object. See source code for `apispec.ext.marshmallow.MarshmallowPlugin </_modules/apispec/ext/marshmallow.html>`_ for an example.

Example: Docstring-parsing Plugin
---------------------------------

Here's a plugin example involving conditional processing depending on the OpenAPI version:

.. code-block:: python

    # docplugin.py

    from apispec import BasePlugin
    from apispec.yaml_utils import load_operations_from_docstring


    class DocPlugin(BasePlugin):
        def init_spec(self, spec):
            super(DocPlugin, self).init_spec(spec)
            self.openapi_major_version = spec.openapi_version.major

        def operation_helper(self, operations, func, **kwargs):
            """Operation helper that parses docstrings for operations. Adds a
            ``func`` parameter to `apispec.APISpec.path`.
            """
            doc_operations = load_operations_from_docstring(func.__doc__)
            # Apply conditional processing
            if self.openapi_major_version < 3:
                "...Mutating doc_operations for OpenAPI v2..."
            else:
                "...Mutating doc_operations for OpenAPI v3+..."
            operations.update(doc_operations)


To use the plugin:

.. code-block:: python

    from apispec import APISpec
    from docplugin import DocPlugin

    spec = APISpec(
        title="Gisty", version="1.0.0", openapi_version="3.0.2", plugins=[DocPlugin()]
    )


    def gist_detail(gist_id):
        """Gist detail view.
        ---
        get:
          responses:
            200:
              content:
                application/json:
                  schema: '#/definitions/Gist'
        """
        pass


    spec.path(path="/gists/{gist_id}", func=gist_detail)
    print(dict(spec.to_dict()["paths"]))
    # {'/gists/{gist_id}': OrderedDict([('get', {'responses': {200: {'content': {'application/json': {'schema': '#/definitions/Gist'}}}}})])}


Next Steps
----------

To learn more about how to write plugins:

* Consult the :doc:`Core API docs <api_core>` for `BasePlugin <apispec.BasePlugin>`
* View the source for an existing apispec plugin, e.g. `FlaskPlugin <https://github.com/marshmallow-code/apispec-webframeworks/blob/master/src/apispec_webframeworks/flask.py>`_.
* Check out some projects using apispec: https://github.com/marshmallow-code/apispec/wiki/Ecosystem
