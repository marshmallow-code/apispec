"""Utilities for generating OpenAPI Specification (fka Swagger) entities from
:class:`Fields <marshmallow.fields.Field>`.

.. warning::

    This module is treated as private API.
    Users should not need to use this module directly.
"""
import functools
import operator
import warnings

import marshmallow
from marshmallow.orderedset import OrderedSet

from apispec.utils import OpenAPIVersion
from apispec.compat import RegexType, iteritems


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


class FieldConverter(object):
    """Class to convert fields to an OpenAPI property

    :param str|OpenAPIVersion openapi_version: The OpenAPI version to use.
        Should be in the form '2.x' or '3.x.x' to comply with the OpenAPI standard.
    :param func resolve_nested_schema: callback function from OpenAPIConverter
        to call for nested fields
    """

    field_mapping = DEFAULT_FIELD_MAPPING

    def __init__(self, openapi_version, resolve_nested_schema):
        self.openapi_version = OpenAPIVersion(openapi_version)
        self.resolve_nested_schema = resolve_nested_schema

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
            # field.container was renamed to field.inner in marshmallow 3.0.0rc8
            inner_field = field.inner if hasattr(field, "inner") else field.container
            ret["items"] = self.field2property(inner_field)
        elif isinstance(field, marshmallow.fields.Dict):
            if MARSHMALLOW_VERSION_INFO[0] >= 3:
                # field.value_container was renamed to field.value_field in marshmallow 3.0.0rc8
                value_field = (
                    field.value_field
                    if hasattr(field, "value_field")
                    else field.value_container
                )
                if value_field:
                    ret["additionalProperties"] = self.field2property(value_field)

        return ret

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
        (e.g. "description", "enum", "example").

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
