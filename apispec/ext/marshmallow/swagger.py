# -*- coding: utf-8 -*-
"""Utilities for generating OpenAPI spec (fka Swagger) entities from webargs :class:`Args <webargs.core.Arg>`
and marshmallow :class:`Schemas <marshmallow.Schema>`.

.. note::

    Even though this module supports webargs, webargs is an optional dependency.

OpenAPI 2.0 spec: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md
"""
from __future__ import absolute_import, unicode_literals
import operator
import warnings
import functools

import marshmallow
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
    # Assume base Field and Raw are strings
    marshmallow.fields.Field: ('string', None),
    marshmallow.fields.Raw: ('string', None),
    marshmallow.fields.List: ('array', None),
}


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


def field2property(field, spec=None, use_refs=True, dump=True):
    """Return the JSON Schema property definition given a marshmallow
    :class:`Field <marshmallow.fields.Field>`.

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#schemaObject

    :param Field field: A marshmallow field.
    :param APISpec spec: Optional `APISpec` containing refs.
    :param bool use_refs: Use JSONSchema ``refs``.
    :param bool dump: Introspect dump logic.
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

    if isinstance(field, marshmallow.fields.Nested):
        del ret['type']
        if use_refs and field.metadata.get('ref'):
            ref_schema = {'$ref': field.metadata['ref']}
            if field.many:
                ret['type'] = 'array'
                ret['items'] = ref_schema
            else:
                ret.update(ref_schema)
        elif spec:
            ret.update(resolve_schema_dict(spec, field.schema))
        else:
            ret.update(schema2jsonschema(field.schema))
    elif isinstance(field, marshmallow.fields.List):
        ret['items'] = field2property(field.container, spec=spec, use_refs=use_refs, dump=dump)

    ret.update(field.metadata)
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
        ) \
            for field_name, field_obj in iteritems(fields) \
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
    location = field.metadata.pop('location', None)
    prop = field2property(field, spec=spec, use_refs=use_refs, dump=dump)
    return property2parameter(
        prop,
        name=name,
        required=field.required,
        multiple=isinstance(field, marshmallow.fields.List),
        location=location,
        default_in=default_in,
    )


def arg2parameter(arg, name='body', default_in='body'):
    """Return an OpenAPI parameter as a `dict`, given a webargs `Arg <webargs.Arg>`.

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#parameterObject
    """
    prop = arg2property(arg)
    return property2parameter(
        prop,
        name=arg.metadata.get('name', name),
        required=arg.required,
        multiple=arg.multiple,
        location=arg.location,
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


def schema2jsonschema(schema, spec=None, use_refs=True, dump=True):
    if hasattr(schema, 'fields'):
        fields = schema.fields
    elif hasattr(schema, '_declared_fields'):
        fields = schema._declared_fields
    else:
        raise ValueError(
            "{0!r} doesn't have either `fields` or `_declared_fields`".format(schema)
        )

    return fields2jsonschema(fields, schema, spec=spec, use_refs=use_refs, dump=dump)


def fields2jsonschema(fields, schema=None, spec=None, use_refs=True, dump=True):
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
        warnings.warn(
            "Only explicitly-declared fields will be included in the Schema Object. "
            "Fields defined in Meta.fields or Meta.additional are ignored."
        )

    jsonschema = {
        'type': 'object',
        'properties': LazyDict({}),
    }

    exclude = set(getattr(Meta, 'exclude', []))

    for field_name, field_obj in iteritems(fields):
        if field_name in exclude or (field_obj.dump_only and not dump):
            continue

        observed_field_name = _observed_name(field_obj, field_name)
        prop_func = lambda field_obj=field_obj: \
            field2property(field_obj, spec=spec, use_refs=use_refs, dump=dump)  # flake8: noqa
        jsonschema['properties'][observed_field_name] = prop_func

        if field_obj.required:
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

##### webargs (older versions) #####

# Python type => (JSON Schema type, format)
__type_map__ = {
    text_type: ('string', None),
    binary_type: ('string', 'byte'),
    int: ('integer', 'int32'),
    float: ('number', 'float'),
    bool: ('boolean', None),
    list: ('array', None),
    tuple: ('array', None),
    set: ('array', None),
}

__location_map__ = {
    'querystring': 'query',
    'json': 'body',
    'headers': 'header',
    'form': 'formData',
    'files': 'formData',
}


def _get_json_type(pytype):
    json_type, fmt = __type_map__.get(pytype, ('string', None))
    return json_type, fmt


def arg2property(arg):
    """Return the JSON Schema property definition given a webargs :class:`Arg <webargs.core.Arg>`.

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#schemaObject

    Example: ::

        arg = Arg(int, description='A count of blog posts')
        arg2property(arg)
        # {'type': 'integer', 'format': 'int32', 'description': 'A count of blog posts'}

    :rtype: dict, a Property Object
    """
    if arg.multiple:
        json_type, fmt = 'array', None
    else:
        json_type, fmt = _get_json_type(arg.type)
    ret = {
        'type': json_type,
        'description': arg.metadata.get('description', ''),
    }
    if fmt:
        ret['format'] = fmt
    if arg.multiple:
        ret['items'] = type2items(arg.type)
    if arg.default:
        ret['default'] = arg.default
    ret.update(arg.metadata)
    return ret


def type2items(type):
    """Return the JSON Schema property definition given a webargs :class:`Arg <webargs.core.Arg>`.

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#itemsObject

    Example: ::

        type2items(int)
        # {'type': 'integer', 'format': 'int32'}

    :rtype: dict, an Items Object
    """
    json_type, fmt = _get_json_type(type)
    ret = {'type': json_type}
    if fmt:
        ret['format'] = fmt
    return ret


def args2parameters(args, default_in='body'):
    """Return an array of OpenAPI properties given a dictionary of webargs
    :class:`Args <webargs.core.Arg>`.

    https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#parameterObject

    Example: ::

        args = {
            'username': Arg(str, location='querystring', description='Username to log in'),
            'password': Arg(str, location='querystring', description='Password in plain text'),
        }
        args2parameters(args)
        # [{'required': False, 'type': 'string', 'in': 'query',
        #     'description': 'Username to log in', 'name': 'username'},
        # {'required': False, 'type': 'string', 'in': 'query',
        # 'description': 'Password in plain text', 'name': 'password'}]

    :param dict args: Mapping of parameter names -> `Arg` objects.
    """
    return [
        arg2parameter(arg, name=name, default_in=default_in)
        for name, arg in iteritems(args)
    ]
