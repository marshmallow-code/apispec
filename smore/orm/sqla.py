import inspect

from marshmallow import Schema, validate, fields
from marshmallow.compat import text_type
import sqlalchemy as sa
from sqlalchemy.orm.util import identity_key

def get_pk_from_identity(obj):
    cls, key = identity_key(instance=obj)
    return ':'.join(text_type(x) for x in key)

class ModelConversionError(Exception):
    pass

class ModelConverter(object):

    FIELD_MAPPING = {
        sa.String: fields.String,
        sa.Unicode: fields.String,
        sa.Enum: fields.Field,
    }
    DIRECTION_MAPPING = {
        'MANYTOONE': fields.QuerySelect,
        'MANYTOMANY': fields.QuerySelectList,
        'ONETOMANY': fields.QuerySelectList,
    }

    def fields_for_model(self, model, session=None):
        result = {}
        for prop in model.__mapper__.iterate_properties:
            field = None
            # Normal column -> marshmallow field
            field = self._property2field(prop, session=session)
            if field:
                result[prop.key] = field
        return result

    def _property2field(self, prop, session=None):
        field_kwargs = self._get_field_kwargs_for_property(prop, session=session)
        field_class = self._get_field_class_for_property(prop)
        return field_class(**field_kwargs)

    def _get_field_class_for_property(self, prop):
        if hasattr(prop, 'direction'):
            field_cls = self.DIRECTION_MAPPING[prop.direction.name]
        else:
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
    def _get_field_kwargs_for_property(prop, session=None):
        kwargs = {
            'validate': []
        }
        if hasattr(prop, 'columns'):
            column = prop.columns[0]
            # From wtforms-sqlalchemy
            # Support sqlalchemy.schema.ColumnDefault, so users can benefit
            # from  setting defaults for fields, e.g.:
            #   field = Column(DateTimeField, default=datetime.utcnow)
            default = getattr(column, 'default', None)
            if default is not None:
                # Only actually change default if it has an attribute named
                # 'arg' that's callable.
                default = getattr(default, 'arg', None)

                if default is not None:
                    # ColumnDefault(val).arg can be also a plain value
                    if callable(default):
                        default = default(None)
                kwargs['default'] = default

            if column.nullable:
                kwargs['allow_none'] = True

            if hasattr(column.type, 'enums'):
                kwargs['validate'].append(validate.OneOf(choices=column.type.enums))

            # Add a length validator if a max length is set on the column
            if hasattr(column.type, 'length'):
                kwargs['validate'].append(validate.Length(max=column.type.length))
        if hasattr(prop, 'direction'):  # Relationship property
            # Get field class based on python type
            if not session:
                raise ModelConversionError(
                    'Cannot convert field {0}, need DB session.'.format(prop.key)
                )
            foreign_model = prop.mapper.class_
            nullable = True
            for pair in prop.local_remote_pairs:
                if not pair[0].nullable:
                    nullable = False
            kwargs.update({
                'allow_none': nullable,
                'query': lambda: session.query(foreign_model).all(),
                'keygetter': get_pk_from_identity,
            })
        return kwargs


default_converter = ModelConverter()
fields_for_model = default_converter.fields_for_model
