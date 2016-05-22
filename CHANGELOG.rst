Changelog
---------

0.12.0 (2016-05-22)
+++++++++++++++++++

Features:

* [apispec.ext.marshmallow]: Inspect validators to set additional attributes (:issue:`66`). Thanks :user:`deckar01` for the PR.

Bug fixes:

* [apispec.ext.marshmallow]: Respect ``partial`` parameters on ``Schemas`` (:issue:`74`). Thanks :user:`incognick` for reporting.

0.11.1 (2016-05-02)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.flask]: Flask plugin respects ``APPLICATION_ROOT`` from app's config (:issue:`69`). Thanks :user:`deckar01` for the catch and patch.
* [apispec.ext.marshmallow]: Fix support for plural schema instances (:issue:`71`). Thanks again :user:`deckar01`.

0.11.0 (2016-04-12)
+++++++++++++++++++

Features:

* Support vendor extensions on paths (:issue:`65`). Thanks :user:`lucascosta` for the PR.
* *Backwards-incompatible*: Remove support for old versions (<=0.15.0) of webargs.

Bug fixes:

* Fix error message when plugin does not have a ``setup()`` function.
* [apispec.ext.marshmallow] Fix bug in introspecting self-referencing marshmallow fields, i.e. ``fields.Nested('self')`` (:issue:`55`). Thanks :user:`whoiswes` for reporting.
* [apispec.ext.marshmallow] ``field2property`` no longer pops off ``location`` from a field's metadata (:issue:`67`).

Support:

* Lots of new docs, including a User Guide and improved extension docs.

0.10.1 (2016-04-09)
+++++++++++++++++++

Note: This version is a re-upload of 0.10.0. There is no 0.10.0 release on PyPI.

Features:

* Add Tornado extension (:issue:`62`).

Bug fixes:

* Compatibility fix with marshmallow>=2.7.0 (:issue:`64`).
* Fix bug that raised error for Swagger parameters that didn't include the ``in`` key (:issue:`63`).

Big thanks :user:`lucascosta` for all these changes.

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
