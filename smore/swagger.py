# -*- coding: utf-8 -*-
"""Utilities for generating Swagger spec entities from webargs :class:`Args <webargs.core.Arg>`
and marshmallow :class:`Schemas <marshmallow.Schema>`.

Swagger 2.0 spec: https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md
"""
import warnings

from marshmallow import fields

from smore.compat import text_type, binary_type, iteritems
from smore.exceptions import SmoreError

SWAGGER_VERSION = '2.0'

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

__target_map__ = {
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

    :raise: TranslationError if arg object cannot be translated to a Parameter Object schema.
    :rtype: dict, a Parameter Object
    """
    swagger_target = __target_map__.get(arg.target, default_in)
    ret = {
        'in': swagger_target,
        'required': arg.required,
        'name': name or arg.metadata.get('name', 'body'),
    }

    arg_as_property = arg2property(arg)
    if swagger_target == 'body':
        ret['name'] = 'body'
        ret['schema'] = {}
        schema_props = {}
        if name:
            schema_props[name] = arg_as_property
        ret['schema']['properties'] = schema_props
    else:
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
    }
    ret['description'] = arg.metadata.get('description', '')
    if fmt:
        ret['format'] = fmt
    if arg.default:
        ret['default'] = arg.default
    ret.update(arg.metadata)
    return ret

def args2parameters(args, default_in='body'):
    """Return an array of Swagger properties given a dictionary of webargs
    :class:`Args <webargs.core.Arg>`.

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#parameterObject

    Example: ::

        args = {
            'username': Arg(str, target='querystring', description='Username to log in'),
            'password': Arg(str, target='querystring', description='Password in plain text'),
        }
        args2parameters(args)
        # [{'required': False, 'type': 'string', 'in': 'query',
        #     'description': 'Username to log in', 'name': 'username'},
        # {'required': False, 'type': 'string', 'in': 'query',
        # 'description': 'Password in plain text', 'name': 'password'}]

    :param dict args: Mapping of parameter names -> `Arg` objects.
    """
    return [
        arg2parameter(arg, name=arg.source or name, default_in=default_in)
        for name, arg in iteritems(args)
    ]

##### marshmallow #####

# marshmallow field => (JSON Schema type, format)
FIELD_MAPPING = {
    fields.Integer: ('integer', 'int32'),
    fields.Number: ('number', None),
    fields.Float: ('number', 'float'),
    fields.Fixed: ('number', None),
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

def field2property(field):
    """Return the JSON Schema property definition given a marshmallow
    :class:`Field <marshmallow.fields.Field>`.

    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#schemaObject

    :param Field field: A marshmallow field.
    :rtype: dict, a Property Object
    """
    type_, fmt = _get_json_type_for_field(field)
    ret = {
        'type': type_,
        'description': field.metadata.get('description', '')
    }
    if fmt:
        ret['format'] = fmt
    if field.default:
        ret['default'] = field.default
    ret['required'] = field.required
    ret.update(field.metadata)
    return ret

def schema2jsonschema(schema_cls):
    """Return the JSON Schema Object for a given marshmallow
    :class:`Schema <marshmallow.Schema>`. The Schema must define ``name`` in
    its ``class Meta`` options.

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
    if not hasattr(schema_cls, 'Meta') or not hasattr(schema_cls.Meta, 'title'):
        raise SmoreError('Must define "title" in Meta options.')
    if getattr(schema_cls.Meta, 'fields', None) or getattr(schema_cls.Meta, 'additional', None):
        warnings.warn('Only explicitly-declared fields will be included in the Schema Object. '
                'Fields defined in Meta.fields or Meta.addtional are excluded.')
    ret = {
        'title': schema_cls.Meta.title,
        'description': getattr(schema_cls.Meta, 'description', ''),
        'properties': {
            field_name: field2property(field_obj)
            for field_name, field_obj in iteritems(schema_cls._declared_fields)
        }
    }
    return ret
