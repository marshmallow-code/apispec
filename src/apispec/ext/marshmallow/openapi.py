# -*- coding: utf-8 -*-
"""Utilities for generating OpenAPI Specification (fka Swagger) entities from
marshmallow :class:`Schemas <marshmallow.Schema>` and :class:`Fields <marshmallow.fields.Field>`.

.. warning::

    This module is treated as private API.
    Users should not need to use this module directly.
"""
from __future__ import absolute_import, unicode_literals
import operator
import functools
import warnings
from collections import OrderedDict

import marshmallow
from marshmallow.utils import is_collection
from marshmallow.compat import iteritems
from marshmallow.orderedset import OrderedSet

from apispec.compat import RegexType
from apispec.utils import OpenAPIVersion, build_reference
from .common import (
    resolve_schema_cls,
    get_fields,
    make_schema_key,
    resolve_schema_instance,
    get_unique_schema_name,
)
from apispec.exceptions import APISpecError


MARSHMALLOW_VERSION_INFO = tuple(
    [int(part) for part in marshmallow.__version__.split(".") if part.isdigit()]
)

# marshmallow field => (JSON Schema type, format)
DEFAULT_FIELD_MAPPING = {
    marshmallow.fields.Integer: ("integer", "int32"),
    marshmallow.fields.Number: ("number", None),
    marshmallow.fields.Float: ("number", "float"),
    marshmallow.fields.Decimal: ("number", None),
    marshmallow.fields.String: ("string", None),
    marshmallow.fields.Boolean: ("boolean", None),
    marshmallow.fields.UUID: ("string", "uuid"),
    marshmallow.fields.DateTime: ("string", "date-time"),
    marshmallow.fields.Date: ("string", "date"),
    marshmallow.fields.Time: ("string", None),
    marshmallow.fields.Email: ("string", "email"),
    marshmallow.fields.URL: ("string", "url"),
    marshmallow.fields.Dict: ("object", None),
    # Assume base Field and Raw are strings
    marshmallow.fields.Field: ("string", None),
    marshmallow.fields.Raw: ("string", None),
    marshmallow.fields.List: ("array", None),
}


__location_map__ = {
    "query": "query",
    "querystring": "query",
    "json": "body",
    "headers": "header",
    "cookies": "cookie",
    "form": "formData",
    "files": "formData",
}


# Properties that may be defined in a field's metadata that will be added to the output
# of field2property
# https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#schemaObject
_VALID_PROPERTIES = {
    "format",
    "title",
    "description",
    "default",
    "multipleOf",
    "maximum",
    "exclusiveMaximum",
    "minimum",
    "exclusiveMinimum",
    "maxLength",
    "minLength",
    "pattern",
    "maxItems",
    "minItems",
    "uniqueItems",
    "maxProperties",
    "minProperties",
    "required",
    "enum",
    "type",
    "items",
    "allOf",
    "properties",
    "additionalProperties",
    "readOnly",
    "xml",
    "externalDocs",
    "example",
}

_VALID_PREFIX = "x-"


class OpenAPIConverter(object):
    """Converter generating OpenAPI specification from Marshmallow schemas and fields

    :param str|OpenAPIVersion openapi_version: The OpenAPI version to use.
        Should be in the form '2.x' or '3.x.x' to comply with the OpenAPI standard.
    """

    def __init__(self, openapi_version, schema_name_resolver, spec):
        self.openapi_version = OpenAPIVersion(openapi_version)
        self.schema_name_resolver = schema_name_resolver
        self.spec = spec
        # Schema references
        self.refs = {}
        #  Field mappings
        self.field_mapping = DEFAULT_FIELD_MAPPING

    @staticmethod
    def _observed_name(field, name):
        """Adjust field name to reflect `dump_to` and `load_from` attributes.

        :param Field field: A marshmallow field.
        :param str name: Field name
        :rtype: str
        """
        if MARSHMALLOW_VERSION_INFO[0] < 3:
            # use getattr in case we're running against older versions of marshmallow.
            dump_to = getattr(field, "dump_to", None)
            load_from = getattr(field, "load_from", None)
            return dump_to or load_from or name
        return field.data_key or name

    def map_to_openapi_type(self, *args):
        """Decorator to set mapping for custom fields.

        ``*args`` can be:

        - a pair of the form ``(type, format)``
        - a core marshmallow field type (in which case we reuse that type's mapping)
        """
        if len(args) == 1 and args[0] in self.field_mapping:
            openapi_type_field = self.field_mapping[args[0]]
        elif len(args) == 2:
            openapi_type_field = args
        else:
            raise TypeError("Pass core marshmallow field type or (type, fmt) pair.")

        def inner(field_type):
            self.field_mapping[field_type] = openapi_type_field
            return field_type

        return inner

    def field2type_and_format(self, field):
        """Return the dictionary of OpenAPI type and format based on the field
        type

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        # If this type isn't directly in the field mapping then check the
        # hierarchy until we find something that does.
        for field_class in type(field).__mro__:
            if field_class in self.field_mapping:
                type_, fmt = self.field_mapping[field_class]
                break
        else:
            warnings.warn(
                "Field of type {} does not inherit from marshmallow.Field.".format(
                    type(field)
                ),
                UserWarning,
            )
            type_, fmt = "string", None

        ret = {"type": type_}

        if fmt:
            ret["format"] = fmt

        return ret

    def field2default(self, field):
        """Return the dictionary containing the field's default value

        Will first look for a `doc_default` key in the field's metadata and then
        fall back on the field's `missing` parameter. A callable passed to the
        field's missing parameter will be ignored.

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        ret = {}
        if "doc_default" in field.metadata:
            ret["default"] = field.metadata["doc_default"]
        else:
            default = field.missing
            if default is not marshmallow.missing and not callable(default):
                ret["default"] = default

        return ret

    def field2choices(self, field, **kwargs):
        """Return the dictionary of OpenAPI field attributes for valid choices definition

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        attributes = {}

        comparable = [
            validator.comparable
            for validator in field.validators
            if hasattr(validator, "comparable")
        ]
        if comparable:
            attributes["enum"] = comparable
        else:
            choices = [
                OrderedSet(validator.choices)
                for validator in field.validators
                if hasattr(validator, "choices")
            ]
            if choices:
                attributes["enum"] = list(functools.reduce(operator.and_, choices))

        return attributes

    def field2read_only(self, field, **kwargs):
        """Return the dictionary of OpenAPI field attributes for a dump_only field.

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        attributes = {}
        if field.dump_only:
            attributes["readOnly"] = True
        return attributes

    def field2write_only(self, field, **kwargs):
        """Return the dictionary of OpenAPI field attributes for a load_only field.

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        attributes = {}
        if field.load_only and self.openapi_version.major >= 3:
            attributes["writeOnly"] = True
        return attributes

    def field2nullable(self, field, **kwargs):
        """Return the dictionary of OpenAPI field attributes for a nullable field.

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        attributes = {}
        if field.allow_none:
            attributes[
                "x-nullable" if self.openapi_version.major < 3 else "nullable"
            ] = True
        return attributes

    def field2range(self, field, **kwargs):
        """Return the dictionary of OpenAPI field attributes for a set of
        :class:`Range <marshmallow.validators.Range>` validators.

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        validators = [
            validator
            for validator in field.validators
            if (
                hasattr(validator, "min")
                and hasattr(validator, "max")
                and not hasattr(validator, "equal")
            )
        ]

        attributes = {}
        for validator in validators:
            if validator.min is not None:
                if hasattr(attributes, "minimum"):
                    attributes["minimum"] = max(attributes["minimum"], validator.min)
                else:
                    attributes["minimum"] = validator.min
            if validator.max is not None:
                if hasattr(attributes, "maximum"):
                    attributes["maximum"] = min(attributes["maximum"], validator.max)
                else:
                    attributes["maximum"] = validator.max
        return attributes

    def field2length(self, field, **kwargs):
        """Return the dictionary of OpenAPI field attributes for a set of
        :class:`Length <marshmallow.validators.Length>` validators.

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        attributes = {}

        validators = [
            validator
            for validator in field.validators
            if (
                hasattr(validator, "min")
                and hasattr(validator, "max")
                and hasattr(validator, "equal")
            )
        ]

        is_array = isinstance(
            field, (marshmallow.fields.Nested, marshmallow.fields.List)
        )
        min_attr = "minItems" if is_array else "minLength"
        max_attr = "maxItems" if is_array else "maxLength"

        for validator in validators:
            if validator.min is not None:
                if hasattr(attributes, min_attr):
                    attributes[min_attr] = max(attributes[min_attr], validator.min)
                else:
                    attributes[min_attr] = validator.min
            if validator.max is not None:
                if hasattr(attributes, max_attr):
                    attributes[max_attr] = min(attributes[max_attr], validator.max)
                else:
                    attributes[max_attr] = validator.max

        for validator in validators:
            if validator.equal is not None:
                attributes[min_attr] = validator.equal
                attributes[max_attr] = validator.equal
        return attributes

    def field2pattern(self, field, **kwargs):
        """Return the dictionary of OpenAPI field attributes for a set of
        :class:`Range <marshmallow.validators.Regexp>` validators.

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        regex_validators = (
            v
            for v in field.validators
            if isinstance(getattr(v, "regex", None), RegexType)
        )
        v = next(regex_validators, None)
        attributes = {} if v is None else {"pattern": v.regex.pattern}

        if next(regex_validators, None) is not None:
            warnings.warn(
                "More than one regex validator defined on {} field. Only the "
                "first one will be used in the output spec.".format(type(field)),
                UserWarning,
            )

        return attributes

    def metadata2properties(self, field):
        """Return a dictionary of properties extracted from field Metadata

        Will include field metadata that are valid properties of `OpenAPI schema
        objects
        <https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#schemaObject>`_
        (e.g. “description”, “enum”, “example”).

        In addition, `specification extensions
        <https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#specification-extensions>`_
        are supported.  Prefix `x_` to the desired extension when passing the
        keyword argument to the field constructor. apispec will convert `x_` to
        `x-` to comply with OpenAPI.

        :param Field field: A marshmallow field.
        :rtype: dict
        """
        # Dasherize metadata that starts with x_
        metadata = {
            key.replace("_", "-") if key.startswith("x_") else key: value
            for key, value in iteritems(field.metadata)
        }

        # Avoid validation error with "Additional properties not allowed"
        ret = {
            key: value
            for key, value in metadata.items()
            if key in _VALID_PROPERTIES or key.startswith(_VALID_PREFIX)
        }
        return ret

    def field2property(self, field):
        """Return the JSON Schema property definition given a marshmallow
        :class:`Field <marshmallow.fields.Field>`.

        Will include field metadata that are valid properties of OpenAPI schema objects
        (e.g. "description", "enum", "example").

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#schemaObject

        :param Field field: A marshmallow field.
        :rtype: dict, a Property Object
        """
        ret = {}

        for attr_func in (
            self.field2type_and_format,
            self.field2default,
            self.field2choices,
            self.field2read_only,
            self.field2write_only,
            self.field2nullable,
            self.field2range,
            self.field2length,
            self.field2pattern,
            self.metadata2properties,
        ):
            ret.update(attr_func(field))

        if isinstance(field, marshmallow.fields.Nested):
            del ret["type"]
            schema_dict = self.resolve_nested_schema(field.schema)
            if ret and "$ref" in schema_dict:
                ret.update({"allOf": [schema_dict]})
            else:
                ret.update(schema_dict)
        elif isinstance(field, marshmallow.fields.List):
            ret["items"] = self.field2property(field.container)
        elif isinstance(field, marshmallow.fields.Dict):
            if MARSHMALLOW_VERSION_INFO[0] >= 3:
                if field.value_container:
                    ret["additionalProperties"] = self.field2property(
                        field.value_container
                    )

        return ret

    def resolve_nested_schema(self, schema):
        """Return the Open API representation of a marshmallow Schema.

        Adds the schema to the spec if it isn't already present.

        Typically will return a dictionary with the reference to the schema's
        path in the spec unless the `schema_name_resolver` returns `None`, in
        which case the returned dictoinary will contain a JSON Schema Object
        representation of the schema.

        :param schema: schema to add to the spec
        """
        schema_instance = resolve_schema_instance(schema)
        schema_key = make_schema_key(schema_instance)
        if schema_key not in self.refs:
            schema_cls = self.resolve_schema_class(schema)
            name = self.schema_name_resolver(schema_cls)
            if not name:
                try:
                    json_schema = self.schema2jsonschema(schema)
                except RuntimeError:
                    raise APISpecError(
                        "Name resolver returned None for schema {schema} which is "
                        "part of a chain of circular referencing schemas. Please"
                        " ensure that the schema_name_resolver passed to"
                        " MarshmallowPlugin returns a string for all circular"
                        " referencing schemas.".format(schema=schema)
                    )
                if getattr(schema, "many", False):
                    return {"type": "array", "items": json_schema}
                return json_schema
            name = get_unique_schema_name(self.spec.components, name)
            self.spec.components.schema(name, schema=schema)
        return self.get_ref_dict(schema_instance)

    def schema2parameters(
        self, schema, default_in="body", name="body", required=False, description=None
    ):
        """Return an array of OpenAPI parameters given a given marshmallow
        :class:`Schema <marshmallow.Schema>`. If `default_in` is "body", then return an array
        of a single parameter; else return an array of a parameter for each included field in
        the :class:`Schema <marshmallow.Schema>`.

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#parameterObject
        """
        openapi_default_in = __location_map__.get(default_in, default_in)
        if self.openapi_version.major < 3 and openapi_default_in == "body":
            prop = self.resolve_schema_dict(schema)

            param = {
                "in": openapi_default_in,
                "required": required,
                "name": name,
                "schema": prop,
            }

            if description:
                param["description"] = description

            return [param]

        assert not getattr(
            schema, "many", False
        ), "Schemas with many=True are only supported for 'json' location (aka 'in: body')"

        fields = get_fields(schema, exclude_dump_only=True)

        return self.fields2parameters(fields, default_in=default_in)

    def fields2parameters(self, fields, default_in="body"):
        """Return an array of OpenAPI parameters given a mapping between field names and
        :class:`Field <marshmallow.Field>` objects. If `default_in` is "body", then return an array
        of a single parameter; else return an array of a parameter for each included field in
        the :class:`Schema <marshmallow.Schema>`.

        In OpenAPI3, only "query", "header", "path" or "cookie" are allowed for the location
        of parameters. In OpenAPI 3, "requestBody" is used when fields are in the body.

        This function always returns a list, with a parameter
        for each included field in the :class:`Schema <marshmallow.Schema>`.

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#parameterObject
        """
        parameters = []
        body_param = None
        for field_name, field_obj in iteritems(fields):
            if field_obj.dump_only:
                continue
            param = self.field2parameter(
                field_obj,
                name=self._observed_name(field_obj, field_name),
                default_in=default_in,
            )
            if (
                self.openapi_version.major < 3
                and param["in"] == "body"
                and body_param is not None
            ):
                body_param["schema"]["properties"].update(param["schema"]["properties"])
                required_fields = param["schema"].get("required", [])
                if required_fields:
                    body_param["schema"].setdefault("required", []).extend(
                        required_fields
                    )
            else:
                if self.openapi_version.major < 3 and param["in"] == "body":
                    body_param = param
                parameters.append(param)
        return parameters

    def field2parameter(self, field, name="body", default_in="body"):
        """Return an OpenAPI parameter as a `dict`, given a marshmallow
        :class:`Field <marshmallow.Field>`.

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#parameterObject
        """
        location = field.metadata.get("location", None)
        prop = self.field2property(field)
        return self.property2parameter(
            prop,
            name=name,
            required=field.required,
            multiple=isinstance(field, marshmallow.fields.List),
            location=location,
            default_in=default_in,
        )

    def property2parameter(
        self,
        prop,
        name="body",
        required=False,
        multiple=False,
        location=None,
        default_in="body",
    ):
        """Return the Parameter Object definition for a JSON Schema property.

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#parameterObject

        :param dict prop: JSON Schema property
        :param str name: Field name
        :param bool required: Parameter is required
        :param bool multiple: Parameter is repeated
        :param str location: Location to look for ``name``
        :param str default_in: Default location to look for ``name``
        :raise: TranslationError if arg object cannot be translated to a Parameter Object schema.
        :rtype: dict, a Parameter Object
        """
        openapi_default_in = __location_map__.get(default_in, default_in)
        openapi_location = __location_map__.get(location, openapi_default_in)
        ret = {"in": openapi_location, "name": name}

        if openapi_location == "body":
            ret["required"] = False
            ret["name"] = "body"
            ret["schema"] = {
                "type": "object",
                "properties": {name: prop} if name else {},
            }
            if name and required:
                ret["schema"]["required"] = [name]
        else:
            ret["required"] = required
            if self.openapi_version.major < 3:
                if multiple:
                    ret["collectionFormat"] = "multi"
                ret.update(prop)
            else:
                if multiple:
                    ret["explode"] = True
                    ret["style"] = "form"
                if prop.get("description", None):
                    ret["description"] = prop.pop("description")
                ret["schema"] = prop
        return ret

    def schema2jsonschema(self, schema):
        """Return the JSON Schema Object for a given marshmallow
        :class:`Schema <marshmallow.Schema>` instance. Schema may optionally
        provide the ``title`` and ``description`` class Meta options.

        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#schemaObject

        Example: ::

            class UserSchema(Schema):
                _id = fields.Int()
                email = fields.Email(description='email address of the user')
                name = fields.Str()

                class Meta:
                    title = 'User'
                    description = 'A registered user'

            oaic = OpenAPIConverter(openapi_version='3.0.2', schema_name_resolver=resolver, spec=spec)
            pprint(oaic.schema2jsonschema(UserSchema))
            # {'description': 'A registered user',
            #  'properties': {'_id': {'format': 'int32', 'type': 'integer'},
            #                 'email': {'description': 'email address of the user',
            #                           'format': 'email',
            #                           'type': 'string'},
            #                 'name': {'type': 'string'}},
            #  'title': 'User',
            #  'type': 'object'}

        :param Schema schema: A marshmallow Schema instance
        :rtype: dict, a JSON Schema Object
        """
        fields = get_fields(schema)
        Meta = getattr(schema, "Meta", None)
        partial = getattr(schema, "partial", None)
        ordered = getattr(schema, "ordered", False)

        jsonschema = self.fields2jsonschema(fields, partial=partial, ordered=ordered)

        if hasattr(Meta, "title"):
            jsonschema["title"] = Meta.title
        if hasattr(Meta, "description"):
            jsonschema["description"] = Meta.description

        return jsonschema

    def fields2jsonschema(self, fields, ordered=False, partial=None):
        """Return the JSON Schema Object given a mapping between field names and
        :class:`Field <marshmallow.Field>` objects.

        :param dict fields: A dictionary of field name field object pairs
        :param bool ordered: Whether to preserve the order in which fields were declared
        :param bool|tuple partial: Whether to override a field's required flag.
            If `True` no fields will be set as required. If an iterable fields
            in the iterable will not be marked as required.
        :rtype: dict, a JSON Schema Object
        """
        jsonschema = {"type": "object", "properties": OrderedDict() if ordered else {}}

        for field_name, field_obj in iteritems(fields):
            observed_field_name = self._observed_name(field_obj, field_name)
            property = self.field2property(field_obj)
            jsonschema["properties"][observed_field_name] = property

            if field_obj.required:
                if not partial or (
                    is_collection(partial) and field_name not in partial
                ):
                    jsonschema.setdefault("required", []).append(observed_field_name)

        if "required" in jsonschema:
            jsonschema["required"].sort()

        return jsonschema

    def get_ref_dict(self, schema):
        """Method to create a dictionary containing a JSON reference to the
        schema in the spec
        """
        schema_key = make_schema_key(schema)
        ref_schema = build_reference(
            "schema", self.openapi_version.major, self.refs[schema_key]
        )
        if getattr(schema, "many", False):
            return {"type": "array", "items": ref_schema}
        return ref_schema

    def resolve_schema_dict(self, schema):
        if isinstance(schema, dict):
            if schema.get("type") == "array" and "items" in schema:
                schema["items"] = self.resolve_schema_dict(schema["items"])
            if schema.get("type") == "object" and "properties" in schema:
                schema["properties"] = {
                    k: self.resolve_schema_dict(v)
                    for k, v in schema["properties"].items()
                }
            return schema

        return self.resolve_nested_schema(schema)

    def resolve_schema_class(self, schema):
        """Return schema class for given schema (instance or class)

        :param type|Schema|str: instance, class or class name of marshmallow.Schema
        :return: schema class of given schema (instance or class)
        """
        return resolve_schema_cls(schema)
