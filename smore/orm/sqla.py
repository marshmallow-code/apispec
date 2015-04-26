from marshmallow import Schema, validate, fields
import inspect

import sqlalchemy as sa
from sqlalchemy.orm.properties import ColumnProperty

class ModelConversionError(Exception):
    pass

class ModelConverter(object):

    def __init__(self):
        self.converters = {}

    def converts(self, *args):
        """Decorator that registering a function that
        converts the given SQLA column types to a
        marshmallow field. The registered function receives
        the sqlalchemy Property and a dictionary of keyword
        arguments for the marshmallow field. The function
        should return an instance of a marshmallow `Field`.

        :params args: A list of SQLA column types
        """
        def _inner(func):
            for sa_type in args:
                self.converters[sa_type] = func
            return func
        return _inner

    def fields_for_model(self, model):
        result = {}
        for prop in model.__mapper__.iterate_properties:
            field = None
            # Normal column -> marshmallow field
            field = self._property2field(prop)
            if field:
                result[prop.key] = field
        return result

    @staticmethod
    def fallback_converter(prop, field_kwargs, **extra):
        FieldClass = Schema.TYPE_MAPPING[prop.columns[0].type.python_type]
        return FieldClass(**field_kwargs)

    def _get_converter_for_property(self, prop):
        column = prop.columns[0]
        types = inspect.getmro(type(column.type))

        # Find a converter for the column's type in self.converters
        for col_type in types:
            if col_type in self.converters:
                converter = self.converters[col_type]
                break
        else:
            # Use fallback if there's no registered converter
            if column.type.python_type in Schema.TYPE_MAPPING:
                converter = self.fallback_converter
            else:
                raise ModelConversionError(
                    'Could not find field converter for %s (%r).' % (prop.key, types[0]))
        return converter

    def _property2field(self, prop):
        if isinstance(prop, ColumnProperty):
            # Get field class based on python type
            converter_func = self._get_converter_for_property(prop)
            field_kwargs = field_kwargs_for_property(prop)
            return converter_func(prop, field_kwargs=field_kwargs)
        # TODO: relationships


default_converter = ModelConverter()
converts = default_converter.converts
fields_for_model = default_converter.fields_for_model

@converts(sa.String, sa.Unicode)
def conv_String(prop, field_kwargs, **extra):
    return fields.String(**field_kwargs)


def field_kwargs_for_property(prop):
    column = prop.columns[0]
    kwargs = {
        'validate': []
    }
    # From wtforms-sqlalchemy
    # Support sqlalchemy.schema.ColumnDefault, so users can benefit
    # from  setting defaults for fields, e.g.:
    #   field = Column(DateTimeField, default=datetime.utcnow)
    default = getattr(column, 'default', None)
    if default is not None:
        # Only actually change default if it has an attribute named
        # 'arg' that's callable.
        callable_default = getattr(default, 'arg', None)

        if callable_default is not None:
            # ColumnDefault(val).arg can be also a plain value
            default = callable_default(None) if callable(callable_default) else callable_default
        kwargs['default'] = default

    # Add a length validator if a max length is set on the column
    if getattr(column.type, 'length', None):
        kwargs['validate'].append(validate.Length(max=column.type.length))
    return kwargs

def property2field(prop):
    if isinstance(prop, ColumnProperty):
        column = prop.columns[0]
        # Get field class based on python type
        FieldClass = Schema.TYPE_MAPPING[column.type.python_type]
        kwargs = field_kwargs_for_property(prop)
        return FieldClass(**kwargs)
    # TODO: Relationships
