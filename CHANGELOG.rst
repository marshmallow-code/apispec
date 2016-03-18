Changelog
---------

0.9.1 (2016-03-17)
++++++++++++++++++

Bug fixes:

* Fix generation of metadata for ``Nested`` fields (:issue:`61`). Thanks :user:`martinlatrille`.

0.9.0 (2016-03-13)
++++++++++++++++++

Features:

* Add ``APISpec.add_tags`` method for adding Swagger tags. Thanks :user:`martinlatrille`.

Bug fixes:

* Fix bug in marshmallow extension where metadata was being lost when converting marshmallow ``Schemas`` when ``many=False``. Thanks again :user:`martinlatrille`.

Other changes:

* Remove duplicate ``SWAGGER_VERSION`` from ``api.ext.marshmallow.swagger``.

Support:

* Update docs to reflect rename of Swagger to OpenAPI.


0.8.0 (2016-03-06)
++++++++++++++++++

Features:

* ``apispec.ext.marshmallow.swagger.schema2jsonschema`` properly introspects ``Schema`` instances when ``many=True`` (:issue:`53`). Thanks :user:`frol` for the PR.

Bug fixes:

* Fix error reporting when an invalid object is passed to ``schema2jsonschema`` or ``schema2parameters`` (:issue:`52`). Thanks again :user:`frol`.

0.7.0 (2016-02-11)
++++++++++++++++++

Features:

* ``APISpec.add_path`` accepts ``Path`` objects (:issue:`49`). Thanks :user:`Trii` for the suggestion and the implementation.

Bug fixes:

* Use correct field name in "required" array when ``load_from`` and ``dump_to`` are used (:issue:`48`). Thanks :user:`benbeadle` for the catch and patch.

0.6.0 (2016-01-04)
++++++++++++++++++

Features:

* Add ``APISpec#add_parameter`` for adding common Swagger parameter objects. Thanks :user:`jta`.
* The field name in a spec will be adjusted if a ``Field's`` ``load_from`` and ``dump_to`` attributes are the same. :issue:`43`. Thanks again :user:`jta`.

Bug fixes:

* Fix bug that caused a stack overflow when adding nested Schemas to an ``APISpec`` (:issue:`31`, :issue:`41`). Thanks :user:`alapshin` and :user:`itajaja` for reporting. Thanks :user:`itajaja` for the patch.

0.5.0 (2015-12-13)
++++++++++++++++++

* ``schema2jsonschema`` and ``schema2parameters`` can introspect a marshmallow ``Schema`` instance as well as a ``Schema`` class (:issue:`37`). Thanks :user:`frol`.
* *Backwards-incompatible*: The first argument to ``schema2jsonschema`` and ``schema2parameters`` was changed from ``schema_cls`` to ``schema``.

Bug fixes:

* Handle conflicting signatures for plugin helpers. Thanks :user:`AndrewPashkin` for the catch and patch.

0.4.2 (2015-11-23)
++++++++++++++++++

* Skip dump-only fields when ``dump=False`` is passed to ``schema2parameters`` and ``fields2parameters``. Thanks :user:`frol`.

Bug fixes:

* Raise ``SwaggerError`` when ``validate_swagger`` fails. Thanks :user:`frol`.

0.4.1 (2015-10-19)
++++++++++++++++++

* Correctly pass ``dump`` parameter to ``field2parameters``.

0.4.0 (2015-10-18)
++++++++++++++++++

* Add ``dump`` parameter to ``field2property`` (:issue:`32`).

0.3.0 (2015-10-02)
++++++++++++++++++

* Rename and repackage as "apispec".
* Support ``enum`` field of JSON Schema based on ``OneOf`` and ``ContainsOnly`` validators.

0.2.0 (2015-09-27)
++++++++++++++++++

* Add ``schema2parameters``, ``fields2parameters``, and ``field2parameters``.
* Removed ``Fixed`` from ``swagger.FIELD_MAPPING`` for compatibility with marshmallow>=2.0.0.

0.1.0 (2015-09-13)
++++++++++++++++++

* First release.
