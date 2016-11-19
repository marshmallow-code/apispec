# -*- coding: utf-8 -*-
"""Utilities for generating OpenAPI spec (fka Swagger) entities from
marshmallow :class:`Schemas <marshmallow.Schema>` and :class:`Fields <marshmallow.fields.Field>`.

OpenAPI 2.0 spec: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md
"""
from __future__ import absolute_import, unicode_literals
import operator
import warnings
import functools
from collections import OrderedDict

import marshmallow
from marshmallow.utils import is_collection
from marshmallow.compat import text_type, binary_type, iteritems

from apispec.lazy_dict import LazyDict

##### marshmallow #####

# marshmallow field => (JSON Schema type, format)
FIELD_MAPPING = {
    marshmallow.fields.Integer: ('integer', 'int32'),
    marshmallow.fields.Number: ('number', None),
    marshmallow.fields.Float: ('number', 'float'),
    marshmallow.fields.Decimal: ('number', None),
    marshmallow.fields.String: ('string', None),
    marshmallow.fields.Boolean: ('boolean', None),
    marshmallow.fields.UUID: ('string', 'uuid'),
    marshmallow.fields.DateTime: ('string', 'date-time'),
    marshmallow.fields.Date: ('string', 'date'),
    marshmallow.fields.Time: ('string', None),
    marshmallow.fields.Email: ('string', 'email'),
    marshmallow.fields.URL: ('string', 'url'),
    marshmallow.fields.Dict: ('object', None),
    # Assume base Field and Raw are strings
    marshmallow.fields.Field: ('string', None),
    marshmallow.fields.Raw: ('string', None),
    marshmallow.fields.List: ('array', None),
}


class OrderedLazyDict(LazyDict, OrderedDict):
    pass


def _observed_name(field, name):
    """Adjust field name to reflect `dump_to` and `load_from` attributes.

    :param Field field: A marshmallow field.
    :param str name: Field name
    :rtype: str
    """
    # use getattr in case we're running against older versions of marshmallow.
    dump_to = getattr(field, 'dump_to', None)
    load_from = getattr(field, 'load_from', None)
    if load_from != dump_to:
        return name
    return dump_to or name


def _get_json_type_for_field(field):
    json_type, fmt = FIELD_MAPPING.get(type(field), ('string', None))
    return json_type, fmt


def field2choices(field):
    """Return the set of valid choices for a :class:`Field <marshmallow.fields.Field>`,
    or ``None`` if no choices are specified.

    :param Field field: A marshmallow field.
    :rtype: set
    """
    validators = [
        set(validator.choices) for validator in field.validators
        if hasattr(validator, 'choices')
    ]
    return (
        functools.reduce(operator.and_, validators)
        if validators
        else None
    )

def field2range(field):
    """Return the dictionary of swagger field attributes for a set of
    :class:`Range <marshmallow.validators.Range>` validators.

    :param Field field: A marshmallow field.
    :rtype: dict
    """
    validators = [
        validator for validator in field.validators
        if (
            hasattr(validator, 'min') and
            hasattr(validator, 'max') and
            not hasattr(validator, 'equal')
        )
    ]

    attributes = {}
    for validator in validators:
        if not validator.min is None:
            if hasattr(attributes, 'minimum'):
                attributes['minimum'] = max(
                    attributes['minimum'],
                    validator.min
                )
            else:
                attributes['minimum'] = validator.min
        if not validator.max is None:
            if hasattr(attributes, 'maximum'):
                attributes['maximum'] = min(
                    attributes['maximum'],
                    validator.max
                )
            else:
                attributes['maximum'] = validator.max
    return attributes

def field2length(field):
    """Return the dictionary of swagger field attributes for a set of
    :class:`Length <marshmallow.validators.Length>` validators.

    :param Field field: A marshmallow field.
    :rtype: dict
    """
    attributes = {}

    validators = [
        validator for validator in field.validators
        if (
            hasattr(validator, 'min') and
            hasattr(validator, 'max') and
            hasattr(validator, 'equal')
        )
    ]

    is_array = isinstance(field, (marshmallow.fields.Nested,
                                  marshmallow.fields.List))
    min_attr = 'minItems' if is_array else 'minLength'
    max_attr = 'maxItems' if is_array else 'maxLength'

    for validator in validators:
        if not validator.min is None:
            if hasattr(attributes, min_attr):
                attributes[min_attr] = max(
                    attributes[min_attr],
                    validator.min
                )
            else:
                attributes[min_attr] = validator.min
        if not validator.max is None:
            if hasattr(attributes, max_attr):
                attributes[max_attr] = min(
                    attributes[max_attr],
                    validator.max
                )
            else:
                attributes[max_attr] = validator.max

    for validator in validators:
        if not validator.equal is None:
            attributes[min_attr] = validator.equal
            attributes[max_attr] = validator.equal
    return attributes


# Properties that may be defined in a field's metadata that will be added to the output
# of field2property
# https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#schemaObject
_VALID_PROPERTIES = {
    'format',
    'title',
    'description',
    'default',
    'multipleOf',
    'maximum',
    'exclusiveMaximum',
    'minimum',
    'exclusiveMinimum',
    'maxLength',
    'minLength',
    'pattern',
    'maxItems',
    'minItems',
    'uniqueItems',
    'maxProperties',
    'minProperties',
    'required',
    'enum',
    'type',
    'items',
    'allOf',
    'properties',
    'additionalProperties',
    'discriminator',
    'readOnly',
    'xml',
    'externalDocs',
    'example',
}

_VALID_PREFIX = 'x-'


def field2property(field, spec=None, use_refs=True, dump=True, name=None):
    """Return the JSON Schema property definition given a marshmallow
    :class:`Field <marshmallow.fields.Field>`.

    Will include field metadata that are valid properties of OpenAPI schema objects
    (e.g. "description", "enum", "example").

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#schemaObject

    :param Field field: A marshmallow field.
    :param APISpec spec: Optional `APISpec` containing refs.
    :param bool use_refs: Use JSONSchema ``refs``.
    :param bool dump: Introspect dump logic.
    :param str name: The definition name, if applicable, used to construct the $ref value.
    :rtype: dict, a Property Object
    """
    from apispec.ext.marshmallow import resolve_schema_dict
    type_, fmt = _get_json_type_for_field(field)

    ret = {
        'type': type_,
    }

    if fmt:
        ret['format'] = fmt

    default = field.default if dump else field.missing
    if default:
        ret['default'] = default

    choices = field2choices(field)
    if choices:
        ret['enum'] = list(choices)

    if field.dump_only:
        ret['readOnly'] = True

    ret.update(field2range(field))
    ret.update(field2length(field))

    if isinstance(field, marshmallow.fields.Nested):
        del ret['type']
        # marshmallow>=2.7.0 compat
        field.metadata.pop('many', None)

        is_unbound_self_referencing = not getattr(field, 'parent', None) and field.nested == 'self'
        if (use_refs and 'ref' in field.metadata) or is_unbound_self_referencing:
            if 'ref' in field.metadata:
                ref_name = field.metadata['ref']
            else:
                if not name:
                    raise ValueError('Must pass `name` argument for self-referencing Nested fields.')
                # We need to use the `name` argument when the field is self-referencing and
                # unbound (doesn't have `parent` set) because we can't access field.schema
                ref_name =  '#/definitions/{name}'.format(name=name)
            ref_schema = {'$ref': ref_name}
            if field.many:
                ret['type'] = 'array'
                ret['items'] = ref_schema
            else:
                ret.update(ref_schema)
        elif spec:
            ret.update(resolve_schema_dict(spec, field.schema, dump=dump))
        else:
            ret.update(schema2jsonschema(field.schema, dump=dump))
    elif isinstance(field, marshmallow.fields.List):
        ret['items'] = field2property(field.container, spec=spec, use_refs=use_refs, dump=dump)

    # Dasherize metadata that starts with x_
    metadata = {
        key.replace('_', '-') if key.startswith('x_') else key: value
        for key, value in iteritems(field.metadata)
    }
    for key, value in iteritems(metadata):
        if key in _VALID_PROPERTIES or key.startswith(_VALID_PREFIX):
            ret[key] = value
    # Avoid validation error with "Additional properties not allowed"
    # Property "ref" is not valid in this context
    ret.pop('ref', None)

    return ret


def schema2parameters(schema, **kwargs):
    """Return an array of OpenAPI parameters given a given marshmallow
    :class:`Schema <marshmallow.Schema>`. If `default_in` is "body", then return an array
    of a single parameter; else return an array of a parameter for each included field in
    the :class:`Schema <marshmallow.Schema>`.

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#parameterObject
    """
    if hasattr(schema, 'fields'):
        fields = schema.fields
    elif hasattr(schema, '_declared_fields'):
        fields = schema._declared_fields
    else:
        raise ValueError(
            "{0!r} doesn't have either `fields` or `_declared_fields`".format(schema)
        )

    return fields2parameters(fields, schema, **kwargs)


def fields2parameters(fields, schema=None, spec=None, use_refs=True, dump=True,
                      default_in='body', name='body', required=False):
    """Return an array of OpenAPI parameters given a mapping between field names and
    :class:`Field <marshmallow.Field>` objects. If `default_in` is "body", then return an array
    of a single parameter; else return an array of a parameter for each included field in
    the :class:`Schema <marshmallow.Schema>`.

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#parameterObject
    """
    if default_in == 'body':
        if schema is not None:
            # Prevent circular import
            from apispec.ext.marshmallow import resolve_schema_dict
            prop = resolve_schema_dict(spec, schema, dump=dump)
        else:
            prop = fields2jsonschema(fields, spec=spec, use_refs=use_refs, dump=dump)

        return [{
            'in': default_in,
            'required': required,
            'name': name,
            'schema': prop,
        }]

    assert not getattr(schema, 'many', False), \
        "Schemas with many=True are only supported for 'json' location (aka 'in: body')"

    exclude_fields = getattr(getattr(schema, 'Meta', None), 'exclude', [])

    return [
        field2parameter(
            field_obj,
            name=_observed_name(field_obj, field_name),
            spec=spec,
            use_refs=use_refs,
            dump=dump,
            default_in=default_in
        )
            for field_name, field_obj in iteritems(fields)
            if (
                (field_name not in exclude_fields)
                and not (field_obj.dump_only and not dump)
            )
    ]


def field2parameter(field, name='body', spec=None, use_refs=True, dump=True, default_in='body'):
    """Return an OpenAPI parameter as a `dict`, given a marshmallow
    :class:`Field <marshmallow.Field>`.

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#parameterObject
    """
    location = field.metadata.get('location', None)
    prop = field2property(field, spec=spec, use_refs=use_refs, dump=dump)
    return property2parameter(
        prop,
        name=name,
        required=field.required,
        multiple=isinstance(field, marshmallow.fields.List),
        location=location,
        default_in=default_in,
    )


def property2parameter(prop, name='body', required=False, multiple=False, location=None,
                       default_in='body'):
    """Return the Parameter Object definition for a JSON Schema property.

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#parameterObject

    :param dict prop: JSON Schema property
    :param str name: Field name
    :param bool required: Parameter is required
    :param bool multiple: Parameter is repeated
    :param str location: Location to look for ``name``
    :param str default_in: Default location to look for ``name``
    :raise: TranslationError if arg object cannot be translated to a Parameter Object schema.
    :rtype: dict, a Parameter Object
    """
    swagger_location = __location_map__.get(location, default_in)
    ret = {
        'in': swagger_location,
        'required': required,
        'name': name,
    }

    if swagger_location == 'body':
        ret['name'] = 'body'
        ret['schema'] = {}
        schema_props = {}
        if name:
            schema_props[name] = prop
        ret['schema']['properties'] = schema_props
    else:
        if multiple:
            ret['collectionFormat'] = 'multi'
        ret.update(prop)
    return ret


def schema2jsonschema(schema, spec=None, use_refs=True, dump=True, name=None):
    if hasattr(schema, 'fields'):
        fields = schema.fields
    elif hasattr(schema, '_declared_fields'):
        fields = schema._declared_fields
    else:
        raise ValueError(
            "{0!r} doesn't have either `fields` or `_declared_fields`".format(schema)
        )

    return fields2jsonschema(fields, schema, spec=spec, use_refs=use_refs, dump=dump, name=name)


def fields2jsonschema(fields, schema=None, spec=None, use_refs=True, dump=True, name=None):
    """Return the JSON Schema Object for a given marshmallow
    :class:`Schema <marshmallow.Schema>`. Schema may optionally provide the ``title`` and
    ``description`` class Meta options.

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#schemaObject

    Example: ::

        class UserSchema(Schema):
            _id = fields.Int()
            email = fields.Email(description='email address of the user')
            name = fields.Str()

            class Meta:
                title = 'User'
                description = 'A registered user'

        schema2jsonschema(UserSchema)
        # {
        #     'title': 'User', 'description': 'A registered user',
        #     'properties': {
        #         'name': {'required': False,
        #                 'description': '',
        #                 'type': 'string'},
        #         '_id': {'format': 'int32',
        #                 'required': False,
        #                 'description': '',
        #                 'type': 'integer'},
        #         'email': {'format': 'email',
        #                 'required': False,
        #                 'description': 'email address of the user',
        #                 'type': 'string'}
        #     }
        # }

    :param Schema schema: A marshmallow Schema instance or a class object
    :rtype: dict, a JSON Schema Object
    """
    Meta = getattr(schema, 'Meta', None)
    if getattr(Meta, 'fields', None) or getattr(Meta, 'additional', None):
        declared_fields = set(schema._declared_fields.keys())
        if (set(getattr(Meta, 'fields', set())) > declared_fields
            or
            set(getattr(Meta, 'additional', set())) > declared_fields):
            warnings.warn(
                "Only explicitly-declared fields will be included in the Schema Object. "
                "Fields defined in Meta.fields or Meta.additional are ignored."
            )

    jsonschema = {
        'type': 'object',
        'properties': OrderedLazyDict() if getattr(Meta, 'ordered', None) else LazyDict(),
    }

    exclude = set(getattr(Meta, 'exclude', []))

    for field_name, field_obj in iteritems(fields):
        if field_name in exclude or (field_obj.dump_only and not dump):
            continue

        observed_field_name = _observed_name(field_obj, field_name)
        prop_func = lambda field_obj=field_obj: \
            field2property(field_obj, spec=spec, use_refs=use_refs, dump=dump, name=name)  # flake8: noqa
        jsonschema['properties'][observed_field_name] = prop_func

        partial = getattr(schema, 'partial', None)
        if field_obj.required:
            if not partial or (is_collection(partial) and field_name not in partial):
                jsonschema.setdefault('required', []).append(observed_field_name)

    if Meta is not None:
        if hasattr(Meta, 'title'):
            jsonschema['title'] = Meta.title
        if hasattr(Meta, 'description'):
            jsonschema['description'] = Meta.description

    if getattr(schema, 'many', False):
        jsonschema = {
            'type': 'array',
            'items': jsonschema,
        }

    return jsonschema

__location_map__ = {
    'query': 'query',
    'querystring': 'query',
    'json': 'body',
    'headers': 'header',
    'form': 'formData',
    'files': 'formData',
}
