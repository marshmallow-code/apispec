from marshmallow import Schema, validate, fields
import inspect

import sqlalchemy as sa
from sqlalchemy.orm.properties import ColumnProperty

class ModelConversionError(Exception):
    pass

class ModelConverter(object):

    FIELD_MAPPING = {
        sa.String: fields.String,
        sa.Unicode: fields.String,
        sa.Enum: fields.Field,
    }

    def fields_for_model(self, model):
        result = {}
        for prop in model.__mapper__.iterate_properties:
            field = None
            # Normal column -> marshmallow field
            field = self._property2field(prop)
            if field:
                result[prop.key] = field
        return result

    def _property2field(self, prop):
        if isinstance(prop, ColumnProperty):
            # Get field class based on python type
            field_kwargs = self._get_field_kwargs_for_property(prop)
            field_class = self._get_field_class_for_property(prop)
            return field_class(**field_kwargs)
        # TODO: relationships

    def _get_field_class_for_property(self, prop):
        column = prop.columns[0]
        types = inspect.getmro(type(column.type))

        # First search for a field class from self.FIELD_MAPPING
        for col_type in types:
            if col_type in self.FIELD_MAPPING:
                field_cls = self.FIELD_MAPPING[col_type]
                break
        else:
            # Try to find a field class based on the column's python_type
            if column.type.python_type in Schema.TYPE_MAPPING:
                field_cls = Schema.TYPE_MAPPING[column.type.python_type]
            else:
                raise ModelConversionError(
                    'Could not find field converter for %s (%r).' % (prop.key, types[0]))
        return field_cls

    @staticmethod
    def _get_field_kwargs_for_property(prop):
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

        if column.nullable:
            kwargs['allow_none'] = True

        if hasattr(column.type, 'enums'):
            kwargs['validate'].append(validate.OneOf(choices=column.type.enums))

        # Add a length validator if a max length is set on the column
        if hasattr(column.type, 'length'):
            kwargs['validate'].append(validate.Length(max=column.type.length))
        return kwargs


default_converter = ModelConverter()
fields_for_model = default_converter.fields_for_model

