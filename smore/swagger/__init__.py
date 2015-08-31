# -*- coding: utf-8 -*-
"""Utilities for generating Swagger spec entities from webargs :class:`Args <webargs.core.Arg>`
and marshmallow :class:`Schemas <marshmallow.Schema>`.

.. note::

    Even though this module supports webargs, webargs is an optional dependency.

Swagger 2.0 spec: https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md
"""
from __future__ import absolute_import, unicode_literals
import warnings

from marshmallow import fields
from marshmallow.compat import text_type, binary_type, iteritems


SWAGGER_VERSION = '2.0'

##### marshmallow #####

# marshmallow field => (JSON Schema type, format)
FIELD_MAPPING = {
    fields.Integer: ('integer', 'int32'),
    fields.Number: ('number', None),
    fields.Float: ('number', 'float'),
    fields.Fixed: ('number', None),
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


def field2property(field, spec=None, use_refs=True):
    """Return the JSON Schema property definition given a marshmallow
    :class:`Field <marshmallow.fields.Field>`.

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#schemaObject

    :param Field field: A marshmallow field.
    :rtype: dict, a Property Object
    """
    from smore.ext.marshmallow import resolve_schema_dict
    type_, fmt = _get_json_type_for_field(field)
    ret = {
        'type': type_,
        'description': field.metadata.get('description', '')
    }
    if fmt:
        ret['format'] = fmt
    if field.default:
        ret['default'] = field.default
    ret.update(field.metadata)
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


def schema2jsonschema(schema_cls, spec=None, use_refs=True):
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
    if getattr(schema_cls.Meta, 'fields', None) or getattr(schema_cls.Meta, 'additional', None):
        warnings.warn('Only explicitly-declared fields will be included in the Schema Object. '
                'Fields defined in Meta.fields or Meta.additional are excluded.')
    ret = {'properties': {}}
    exclude = set(getattr(schema_cls.Meta, 'exclude', []))
    for field_name, field_obj in iteritems(schema_cls._declared_fields):
        if field_name in exclude:
            continue
        ret['properties'][field_name] = field2property(field_obj, spec=spec, use_refs=use_refs)
        if field_obj.required:
            ret.setdefault('required', []).append(field_name)
    if hasattr(schema_cls, 'Meta'):
        if hasattr(schema_cls.Meta, 'title'):
            ret['title'] = schema_cls.Meta.title
        if hasattr(schema_cls.Meta, 'description'):
            ret['description'] = schema_cls.Meta.description
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


def arg2parameter(arg, name=None, default_in='body'):
    """Return the Parameter Object definition for a :class:`webargs.Arg <webargs.core.Arg>`.

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#parameterObject
    :param webargs.core.Arg arg: Webarg
    :param str name: Field name
    :param str default_in: Default location to look for ``name``
    :raise: TranslationError if arg object cannot be translated to a Parameter Object schema.
    :rtype: dict, a Parameter Object
    """
    swagger_location = __location_map__.get(arg.location, default_in)
    ret = {
        'in': swagger_location,
        'required': arg.required,
        'name': name or arg.metadata.get('name', 'body'),
    }

    arg_as_property = arg2property(arg)
    if swagger_location == 'body':
        ret['name'] = 'body'
        ret['schema'] = {}
        schema_props = {}
        if name:
            schema_props[name] = arg_as_property
        ret['schema']['properties'] = schema_props
    else:
        if arg.multiple:
            ret['collectionFormat'] = 'multi'
        ret.update(arg_as_property)
    return ret


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
