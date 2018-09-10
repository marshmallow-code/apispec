Changelog
---------

1.0.0b2 (2018-09-09)
++++++++++++++++++++

- Drop deprecated plugin interface. Only plugin classes are now supported. This
  includes the removal of ``APISpec``'s ``register_*_helper`` methods, as well
  as its ``schema_name_resolver`` parameter. Also drop deprecated
  ``apispec.utils.validate_swagger``. (:pr:`259`)
- Use ``yaml.safe_load`` instead of ``yaml.load`` when reading
  docstrings (:issue:`278`). Thanks :user:`lbeaufort` for the suggestion
  and the PR.

1.0.0b1 (2018-07-29)
++++++++++++++++++++

Features:

- [apispec.core]: *Backwards-incompatible*: Remove `Path` class.
  Plugins' `path_helper` methods should now return a path as a string
  and optionally mutate the `operations` dictionary (:pr:`238`).
- [apispec.core]: *Backwards-incompatible*: YAML support is optional. To
  install with YAML support, use ``pip install 'apispec[yaml]'``. You
  will need to do this if you use ``FlaskPlugin``,
  ``BottlePlugin``, or ``TornadoPlugin``.
- [apispec.ext.marshmallow]: Allow overriding the documentation for
  a field's default. This is especially useful for documenting
  callable defaults (:issue:`196`).

0.39.0 (2018-06-28)
+++++++++++++++++++

Features:

- [apispec.core]: *Backwards-incompatible*: Change plugin interface. Plugins are
  now child classes of ``apispec.BasePlugin``. Built-in plugins are still usable
  with the deprecated legacy interface. However, the new class interface is
  mandatory to pass parameters to plugins or to access specific methods that used to be
  accessed as module level functions (typically in ``apispec.ext.marshmallow.swagger``).
  Also, ``schema_name_resolver`` is now a parameter of
  ``apispec.ext.marshmallow.MarshmallowPlugin``. It can still be passed to ``APISpec``
  while using the legacy interface. (:issue:`207`)
- [apispec.core]: *Backwards-incompatible*: ``APISpec.openapi_version`` is now an
  ``apispec.utils.OpenAPIVersion`` instance.

0.38.0 (2018-06-10)
+++++++++++++++++++

Features:

- [apispec.core]: *Backwards-incompatible*: Rename ``apispec.utils.validate_swagger``
  to ``apispec.utils.validate_spec`` and
  ``apispec.exceptions.SwaggerError`` to ``apispec.exceptions.OpenAPIError``.
  Using ``validate_swagger`` will raise a ``DeprecationWarning`` (:pr:`224`).
- [apispec.core]: ``apispec.utils.validate_spec`` no longer relies on
  the ``check_api`` NPM module. ``prance`` and
  ``openapi-spec-validator`` are required for validation, and can be
  installed using ``pip install 'apispec[validation]'`` (:pr:`224`).
- [apispec.core]: Deep update components instead of overwriting components
  for OpenAPI 3 (:pr:`222`). Thanks :user:`Guoli-Lyu`.

Bug fixes:

- [apispec.ext.marshmallow]: Fix description for parameters in OpenAPI 3
  (:pr:`223`). Thanks again :user:`Guoli-Lyu`.

Other changes:

- Drop official support for Python 3.4. Only Python 2.7 and >=3.5 are
  supported.


0.37.1 (2018-05-28)
+++++++++++++++++++

Features:

- [apispec.ext.marshmallow]: Fix OpenAPI 3 conversion of schemas in
  parameters (:issue:`217`). Thanks :user:`Guoli-Lyu` for the PR.

0.37.0 (2018-05-14)
+++++++++++++++++++

Features:

- [apispec.ext.marshmallow]: Resolve an array of schema objects in
  parameters (:issue:`209`). Thanks :user:`cvlong` for reporting and
  implementing this.

0.36.0 (2018-05-07)
+++++++++++++++++++

Features:

- [apispec.ext.marshmallow]: Document ``values`` parameter of ``Dict`` field
  as ``additionalProperties`` (:issue:`201`). Thanks :user:`UrKr`.

0.35.0 (2018-04-10)
+++++++++++++++++++

Features:

- [apispec.ext.marshmallow]: Recurse over properties when resolving
  schemas (:issue:`186`). Thanks :user:`lphuberdeau`.
- [apispec.ext.marshmallow]: Support ``writeOnly`` and ``nullable`` in
  OpenAPI 3 (fall back to ``x-nullable`` for OpenAPI 2) (:issue:`165`).
  Thanks :user:`lafrech`.

Bug fixes:

- [apispec.ext.marshmallow]: Always use `field.missing` instead of
  `field.default` when introspecting fields (:issue:`32`). Thanks
  :user:`lafrech`.

Other changes:

- [apispec.ext.marshmallow]: Refactor some of the internal functions in
  `apispec.ext.marshmallow.swagger` for consistent API (:issue:`199`).
  Thanks :user:`lafrech`.

0.34.0 (2018-04-04)
+++++++++++++++++++

Features:

- [apispec.core]: Maintain order in which methods are added to an
  endpoint (:issue:`189`). Thanks :user:`lafrech`.

Other changes:

- [apispec.core]: `Path` no longer inherits from `dict` (:issue:`190`).
  Thanks :user:`lafrech`.

0.33.0 (2018-04-01)
+++++++++++++++++++

Features:

- [apispec.ext.marshmallow]: Respect ``data_key`` argument on fields
  (in marshmallow 3). Thanks :user:`lafrech`.

0.32.0 (2018-03-24)
+++++++++++++++++++

Features:

- [apispec.ext.bottle]: Allow `app` to be passed to `spec.add_path`
  (:issue:`188`). Thanks :user:`dtaniwaki` for the PR.

Bug fixes:

- [apispec.ext.marshmallow]: Fix issue where "body" and "required" were
  getting overwritten when passing a ``Schema`` to a parameter
  (:issue:`168`, :issue:`184`).
  Thanks :user:`dlopuch` and :user:`mathewmarcus` for reporting and
  thanks :user:`mathewmarcus` for the PR.

0.31.0 (2018-01-30)
+++++++++++++++++++

- [apispec.ext.marshmallow]: Use ``dump_to`` for name even if
  ``load_from`` does not match it (:issue:`178`). Thanks :user:`LeonAgmonNacht`
  for reporting and thanks :user:`lafrech` for the fix.

0.30.0 (2018-01-12)
+++++++++++++++++++

Features:

- [apispec.core]: Add ``Spec.to_yaml`` method for serializing to YAML
  (:issue:`161`). Thanks :user:`jd`.

0.29.0 (2018-01-04)
+++++++++++++++++++

Features:

- [apispec.core and apispec.ext.marshmallow]: Add limited support for
  OpenAPI v3. Pass `openapi_version='3.0.0'` to `Spec` to use it
  (:issue:`165`). Thanks :user:`Bangertm`.

0.28.0 (2017-12-09)
+++++++++++++++++++

Features:

- [apispec.core and apispec.ext.marshmallow]: Add `schema_name_resolver`
  param to `APISpec` for resolving ref names for marshmallow Schemas.
  This is useful when a self-referencing schema is nested within another
  schema (:issue:`167`). Thanks :user:`buxx` for the PR.

0.27.1 (2017-12-06)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.flask]: Don't document view methods that aren't included
  in ``app.add_url_rule(..., methods=[...]))`` (:issue:`173`). Thanks :user:`ukaratay`.

0.27.0 (2017-10-30)
+++++++++++++++++++

Features:

* [apispec.core]: Add ``register_operation_helper``.

Bug fixes:

* Order of plugins does not matter (:issue:`136`).

Thanks :user:`yoichi` for these changes.

0.26.0 (2017-10-23)
+++++++++++++++++++

Features:

* [apispec.ext.marshmallow]: Generate "enum" property with single entry
  when the ``validate.Equal`` validator is used (:issue:`155`). Thanks
  :user:`Bangertm` for the suggestion and PR.

Bug fixes:

* Allow OPTIONS to be documented (:issue:`162`). Thanks :user:`buxx` for
  the PR.
* Fix regression from 0.25.3 that caused a ``KeyError`` (:issue:`163`). Thanks
  :user:`yoichi`.

0.25.4 (2017-10-09)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.marshmallow]: Fix swagger location mapping for ``default_in``
  param in fields2parameters (:issue:`156`). Thanks :user:`decaz`.

0.25.3 (2017-09-27)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.marshmallow]: Correctly handle multiple fields with
  ``location=json`` (:issue:`75`). Thanks :user:`shaicantor` for
  reporting and thanks :user:`yoichi` for the patch.


0.25.2 (2017-09-05)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.marshmallow]: Avoid AttributeError when passing non-dict
  items to path objects (:issue:`151`). Thanks :user:`yoichi`.

0.25.1 (2017-08-23)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.marshmallow]: Fix ``use_instances`` when ``many=True`` is
  set (:issue:`148`). Thanks :user:`theirix`.

0.25.0 (2017-08-15)
+++++++++++++++++++

Features:

* [apispec.ext.marshmallow]: Add ``use_instances`` parameter to
  ``fields2paramters`` (:issue:`144`). Thanks :user:`theirix`.

Other changes:

* Don't swallow ``YAMLError`` when YAML parsing fails
  (:issue:`135`). Thanks :user:`djanderson` for the suggestion
  and the PR.

0.24.0 (2017-08-15)
+++++++++++++++++++

Features:

* [apispec.ext.marshmallow]: Add ``swagger.map_to_swagger_field``
  decorator to support custom field classes (:issue:`120`). Thanks
  :user:`frol` for the suggestion and thanks :user:`dradetsky` for the
  PR.

0.23.1 (2017-08-08)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.marshmallow]: Fix swagger location mapping for
  ``default_in`` param in `property2parameter` (:issue:`142`). Thanks
  :user:`decaz`.

0.23.0 (2017-08-03)
+++++++++++++++++++

* Pass `operations` constructed by plugins to downstream marshmallow
  plugin (:issue:`138`). Thanks :user:`yoichi`.
* [apispec.ext.marshmallow] Generate parameter specification from marshmallow Schemas (:issue:`127`).
  Thanks :user:`ewalker11` for the suggestion thanks :user:`yoichi` for the PR.
* [apispec.ext.flask] Add support for Flask MethodViews (:issue:`85`,
  :issue:`125`). Thanks :user:`lafrech` and :user:`boosh` for the
  suggestion. Thanks :user:`djanderson` and :user:`yoichi` for the PRs.

0.22.3 (2017-07-16)
+++++++++++++++++++

* Release wheel distribution.

0.22.2 (2017-07-12)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.marshmallow]: Properly handle callable ``default`` values
  in output spec (:issue:`131`). Thanks :user:`NightBlues`.

0.22.1 (2017-06-25)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.marshmallow]: Include ``default`` in output spec when
  ``False`` is the default for a ``Boolean`` field (:issue:`130`).
  Thanks :user:`nebularazer`.

0.22.0 (2017-05-30)
+++++++++++++++++++

Features:

* [apispec.ext.bottle] Added bottle plugin (:issue:`128`). Thanks :user:`lucasrc`.

0.21.0 (2017-04-21)
+++++++++++++++++++

Features:

* [apispec.ext.marshmallow] Sort list of required field names in generated spec (:issue:`124`). Thanks :user:`dradetsky`.

0.20.1 (2017-04-18)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.tornado]: Fix compatibility with Tornado>=4.5.
* [apispec.ext.tornado]: Fix adding paths for handlers with coroutine methods in Python 2 (:issue:`99`).

0.20.0 (2017-03-19)
+++++++++++++++++++

Features:

* [apispec.core]: Definition helper functions receive the ``definition`` keyword argument, which is the current state of the definition (:issue:`122`). Thanks :user:`martinlatrille` for the PR.

Other changes:

* [apispec.ext.marshmallow] *Backwards-incompatible*: Remove ``dump`` parameter from ``schema2parameters``, ``fields2parameters``, and ``field2parameter`` (:issue:`114`). Thanks :user:`lafrech` and :user:`frol` for the feedback and :user:`lafrech` for the PR.

0.19.0 (2017-03-05)
+++++++++++++++++++

Features:

* [apispec.core]: Add ``extra_fields`` parameter to `APISpec.definition` (:issue:`110`). Thanks :user:`lafrech` for the PR.
* [apispec.ext.marshmallow]: Preserve the order of ``choices`` (:issue:`113`). Thanks :user:`frol` for the PR.

Bug fixes:

* [apispec.ext.marshmallow]: 'discriminator' is no longer valid as field metadata. It should be defined by passing ``extra_fields={'discriminator': '...'}`` to `APISpec.definition`. Thanks for reporting, :user:`lafrech`.
* [apispec.ext.marshmallow]: Allow additional properties when translating ``Nested`` fields using ``allOf`` (:issue:`108`). Thanks :user:`lafrech` for the suggestion and the PR.
* [apispec.ext.marshmallow]: Respect ``dump_only`` and ``load_only`` specified in ``class Meta`` (:issue:`84`). Thanks :user:`lafrech` for the fix.

Other changes:

* Drop support for Python 3.3.


0.18.0 (2017-02-19)
+++++++++++++++++++

Features:

* [apispec.ext.marshmallow]: Translate ``allow_none`` on ``Fields`` to ``x-nullable`` (:issue:`66`). Thanks :user:`lafrech`.

0.17.4 (2017-02-16)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.marshmallow]: Fix corruption of ``Schema._declared_fields`` when serializing an APISpec (:issue:`107`). Thanks :user:`serebrov` for the catch and patch.

0.17.3 (2017-01-21)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.marshmallow]: Fix behavior when passing `Schema` instances to `APISpec.definition`. The `Schema's` class will correctly be registered as a an available `ref` (:issue:`84`). Thanks :user:`lafrech` for reporting and for the PR.

0.17.2 (2017-01-03)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.tornado]: Remove usage of ``inspect.getargspec`` for Python >= 3.3 (:issue:`102`). Thanks :user:`matijabesednik`.

0.17.1 (2016-11-19)
+++++++++++++++++++

Bug fixes:

* [apispec.ext.marshmallow]: Prevent unnecessary warning when generating specs for marshmallow Schema's with autogenerated fields (:issue:`95`). Thanks :user:`khorolets` reporting and for the PR.
* [apispec.ext.marshmallow]: Correctly translate ``Length`` validator to `minItems` and `maxItems` for array-type fields (``Nested`` and ``List``) (:issue:`97`). Thanks :user:`YuriHeupa` for reporting and for the PR.

0.17.0 (2016-10-30)
+++++++++++++++++++

Features:

* [apispec.ext.marshmallow]: Add support for properties that start with `x-`. Thanks :user:`martinlatrille` for the PR.

0.16.0 (2016-10-12)
+++++++++++++++++++

Features:

* [apispec.core]: Allow ``description`` to be passed to ``APISpec.definition`` (:issue:`93`). Thanks :user:`martinlatrille`.

0.15.0 (2016-10-02)
+++++++++++++++++++

Features:

* [apispec.ext.marshmallow]: Allow ``'query'`` to be passed as a field location (:issue:`89`). Thanks :user:`lafrech`.

Bug fixes:

* [apispec.ext.flask]: Properly strip off ``basePath`` when ``APPLICATION_ROOT`` is set on a Flask app's config (:issue:`78`). Thanks :user:`deckar01` for reporting and :user:`asteinlein` for the PR.

0.14.0 (2016-08-14)
+++++++++++++++++++

Features:

* [apispec.core]: Maintain order in which paths are added to a spec (:issue:`87`). Thanks :user:`ranjanashish` for the PR.
* [apispec.ext.marshmallow]: Maintain order of fields when ``ordered=True`` on Schema. Thanks again :user:`ranjanashish`.

0.13.0 (2016-07-03)
+++++++++++++++++++

Features:

* [apispec.ext.marshmallow]: Add support for ``Dict`` field (:issue:`80`). Thanks :user:`ericb` for the PR.
* [apispec.ext.marshmallow]: ``dump_only`` fields add ``readOnly`` flag in OpenAPI spec (:issue:`79`). Thanks :user:`itajaja` for the suggestion and PR.

Bug fixes:

* [apispec.ext.marshmallow]: Properly exclude nested dump-only fields from parameters (:issue:`82`). Thanks :user:`incognick` for the catch and patch.

Support:

* Update tasks.py for compatibility with invoke>=0.13.0.

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
