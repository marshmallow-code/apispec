# -*- coding: utf-8 -*-
"""Utilities for generating Swagger spec entities from webargs :class:`Args <webargs.core.Arg>`
and marshmallow :class:`Schemas <marshmallow.Schema>`.

.. note::

    Even though this module supports webargs, webargs is an optional dependency.

Swagger 2.0 spec: https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md
"""
from __future__ import absolute_import, unicode_literals
import operator
import warnings
import functools

from marshmallow import fields
from marshmallow.compat import text_type, binary_type, iteritems


SWAGGER_VERSION = '2.0'

##### marshmallow #####

# marshmallow field => (JSON Schema type, format)
FIELD_MAPPING = {
    fields.Integer: ('integer', 'int32'),
    fields.Number: ('number', None),
    fields.Float: ('number', 'float'),
    fields.Decimal: ('number', None),
    fields.String: ('string', None),
    fields.Boolean: ('boolean', None),
    fields.UUID: ('string', 'uuid'),
    fields.DateTime: ('string', 'date-time'),
    fields.Date: ('string', 'date'),
    fields.Time: ('string', None),
    fields.Email: ('string', 'email'),
    fields.URL: ('string', 'url'),
    # Assume base Field and Raw are strings
    fields.Field: ('string', None),
    fields.Raw: ('string', None),
    fields.List: ('array', None),
}


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


def field2property(field, spec=None, use_refs=True):
    """Return the JSON Schema property definition given a marshmallow
    :class:`Field <marshmallow.fields.Field>`.

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#schemaObject

    :param Field field: A marshmallow field.
    :param APISpec spec: Optional `APISpec` containing refs
    :param bool use_refs: Use JSONSchema ``refs``.
    :rtype: dict, a Property Object
    """
    from apispec.ext.marshmallow import resolve_schema_dict
    type_, fmt = _get_json_type_for_field(field)
    ret = {
        'type': type_,
    }
    if field.metadata.get('description'):
        ret['description'] = field.metadata['description']
    if fmt:
        ret['format'] = fmt
    if field.default:
        ret['default'] = field.default
    ret.update(field.metadata)
    choices = field2choices(field)
    if choices:
        ret['enum'] = list(choices)
    # Avoid validation error with "Additional properties not allowed"
    # Property "ref" is not valid in this context
    ret.pop('ref', None)
    if isinstance(field, fields.Nested):
        if use_refs and field.metadata.get('ref'):
            schema = {'$ref': field.metadata['ref']}
        elif spec:
            schema = resolve_schema_dict(spec, field.schema)
        else:
            schema = schema2jsonschema(field.schema.__class__)
        if field.many:
            ret['type'] = 'array'
            ret['items'] = schema
        else:
            ret = schema
    elif isinstance(field, fields.List):
        ret['items'] = field2property(field.container, spec=spec, use_refs=use_refs)
    return ret


def schema2parameters(schema_cls, **kwargs):
    """Return an array of Swagger parameters given a given marshmallow
    :class:`Schema <marshmallow.Schema>`. If `default_in` is "body", then return an array
    of a single parameter; else return an array of a parameter for each included field in
    the :class:`Schema <marshmallow.Schema>`.

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#parameterObject
    """
    fields = schema_cls._declared_fields
    return fields2parameters(fields, schema_cls, **kwargs)


def fields2parameters(fields, schema_cls=None, spec=None, use_refs=True, default_in='body',
                      name='body', required=False):
    """Return an array of Swagger parameters given a mapping between field names and
    :class:`Field <marshmallow.Field>` objects. If `default_in` is "body", then return an array
    of a single parameter; else return an array of a parameter for each included field in
    the :class:`Schema <marshmallow.Schema>`.

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#parameterObject
    """
    Meta = getattr(schema_cls, 'Meta', None)
    if default_in == 'body':
        if schema_cls is not None:
            # Prevent circular import
            from apispec.ext.marshmallow import resolve_schema_dict
            prop = resolve_schema_dict(spec, schema_cls)
        else:
            prop = fields2jsonschema(fields, schema_cls=schema_cls, spec=spec, use_refs=use_refs)
        return [{
            'in': default_in,
            'required': required,
            'name': name,
            'schema': prop,
        }]
    return [
        field2parameter(field_obj, name=field_name, spec=spec,
            use_refs=use_refs, default_in=default_in)
        for field_name, field_obj in iteritems(fields)
        if field_name not in getattr(Meta, 'exclude', [])
    ]


def field2parameter(field, name='body', spec=None, use_refs=True, default_in='body'):
    """Return Swagger parameter as a `dict`, given a marshmallow
    :class:`Field <marshmallow.Field>`.

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#parameterObject
    """
    location = field.metadata.pop('location', None)
    prop = field2property(field, spec=spec, use_refs=use_refs)
    return property2parameter(
        prop, name=name, required=field.required, multiple=isinstance(field, fields.List),
        location=location, default_in=default_in,
    )


def arg2parameter(arg, name='body', default_in='body'):
    """Return Swagger parameter as a `dict`, given a webargs `Arg <webargs.Arg>`.

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#parameterObject
    """
    prop = arg2property(arg)
    return property2parameter(
        prop, name=arg.metadata.get('name', name), required=arg.required, multiple=arg.multiple,
        location=arg.location, default_in=default_in,
    )


def property2parameter(prop, name='body', required=False, multiple=False, location=None,
                       default_in='body'):
    """Return the Parameter Object definition for a JSON Schema property.

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#parameterObject
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


def schema2jsonschema(schema_cls, spec=None, use_refs=True):
    fields = schema_cls._declared_fields
    return fields2jsonschema(fields, schema_cls, spec=spec, use_refs=use_refs)


def fields2jsonschema(fields, schema_cls=None, spec=None, use_refs=True):
    """Return the JSON Schema Object for a given marshmallow
    :class:`Schema <marshmallow.Schema>`. Schema may optionally provide the ``title`` and
    ``description`` class Meta options.

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#schemaObject

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

    :param type schema_cls: A marshmallow :class:`Schema <marshmallow.Schema>`
    :rtype: dict, a JSON Schema Object
    """
    Meta = getattr(schema_cls, 'Meta', None)
    if getattr(Meta, 'fields', None) or getattr(Meta, 'additional', None):
        warnings.warn('Only explicitly-declared fields will be included in the Schema Object. '
                'Fields defined in Meta.fields or Meta.additional are excluded.')
    ret = {'properties': {}}
    exclude = set(getattr(Meta, 'exclude', []))
    for field_name, field_obj in iteritems(fields):
        if field_name in exclude:
            continue
        ret['properties'][field_name] = field2property(field_obj, spec=spec, use_refs=use_refs)
        if field_obj.required:
            ret.setdefault('required', []).append(field_name)
    if Meta is not None:
        if hasattr(Meta, 'title'):
            ret['title'] = Meta.title
        if hasattr(Meta, 'description'):
            ret['description'] = Meta.description
    return ret

##### webargs #####

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

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#schemaObject

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

    https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#itemsObject

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
    """Return an array of Swagger properties given a dictionary of webargs
    :class:`Args <webargs.core.Arg>`.

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#parameterObject

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
