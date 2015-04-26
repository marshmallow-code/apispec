# -*- coding: utf-8 -*-
import inspect

import marshmallow as ma
from marshmallow import validate, fields
from marshmallow.compat import text_type, with_metaclass
import sqlalchemy as sa
from sqlalchemy.orm.util import identity_key

def get_pk_from_identity(obj):
    _, key = identity_key(instance=obj)
    if len(key) == 1:
        return key[0]
    else:  # Compund primary key
        return ':'.join(text_type(x) for x in key)

class ModelConversionError(Exception):
    pass

class ModelConverter(object):

    SQLA_TYPE_MAPPING = {
        sa.String: fields.String,
        sa.Unicode: fields.String,
        sa.Enum: fields.Field,
        # TODO: Finish me
    }
    DIRECTION_MAPPING = {
        'MANYTOONE': fields.QuerySelect,
        'MANYTOMANY': fields.QuerySelectList,
        'ONETOMANY': fields.QuerySelectList,
    }

    def fields_for_model(self, model, session=None, include_fk=False, keygetter=None):
        """Generate a dict of field_name: `marshmallow.Field` pairs for the
        given model.

        :param model: The SQLAlchemy model
        :param Session session: SQLAlchemy session. Required if the model includes
            foreign key relationships.
        :param bool include_fk: Whether to include foreign key fields from the
            output.
        :return: dict of field_name: Field instance pairs
        """
        result = {}
        for prop in model.__mapper__.iterate_properties:
            if hasattr(prop, 'columns'):
                if not include_fk and prop.columns[0].foreign_keys:
                    continue
            field = self._property2field(prop, session=session, keygetter=keygetter)
            if field:
                result[prop.key] = field
        return result

    def _property2field(self, prop, session=None, keygetter=None):
        field_kwargs = self._get_field_kwargs_for_property(
            prop, session=session, keygetter=keygetter
        )
        field_class = self._get_field_class_for_property(prop)
        return field_class(**field_kwargs)

    def _get_field_class_for_property(self, prop):
        if hasattr(prop, 'direction'):
            field_cls = self.DIRECTION_MAPPING[prop.direction.name]
        else:
            column = prop.columns[0]
            types = inspect.getmro(type(column.type))
            # First search for a field class from self.SQLA_TYPE_MAPPING
            for col_type in types:
                if col_type in self.SQLA_TYPE_MAPPING:
                    field_cls = self.SQLA_TYPE_MAPPING[col_type]
                    break
            else:
                # Try to find a field class based on the column's python_type
                if column.type.python_type in ma.Schema.TYPE_MAPPING:
                    field_cls = ma.Schema.TYPE_MAPPING[column.type.python_type]
                else:
                    raise ModelConversionError(
                        'Could not find field converter for {0} ({1}).'.format(prop.key, types[0]))
        return field_cls

    @staticmethod
    def _get_field_kwargs_for_property(prop, session=None, keygetter=None):
        kwargs = {
            'validate': []
        }
        if hasattr(prop, 'columns'):
            column = prop.columns[0]
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
                'keygetter': keygetter or get_pk_from_identity,
            })
        return kwargs


default_converter = ModelConverter()
fields_for_model = default_converter.fields_for_model


class SQLAlchemySchemaOpts(ma.SchemaOpts):

    def __init__(self, meta):
        super(SQLAlchemySchemaOpts, self).__init__(meta)
        self.model = getattr(meta, 'model', None)
        self.sqla_session = getattr(meta, 'sqla_session', None)
        if self.model and not self.sqla_session:
            raise ValueError('SQLAlchemyModelSchema requires the "sqla_session" class Meta option')
        self.keygetter = getattr(meta, 'keygetter', get_pk_from_identity)
        self.model_converter = getattr(meta, 'model_converter', ModelConverter)

class SQLAlchemySchemaMeta(ma.schema.SchemaMeta):

    # override SchemaMeta
    @classmethod
    def get_declared_fields(mcs, klass, *args, **kwargs):
        """Updates declared fields with fields converted from the SQLAlchemy model
        passed as the `model` class Meta option.
        """
        declared_fields = kwargs.get('dict_class', dict)()
        # inheriting from base classes
        for base in inspect.getmro(klass):
            opts = klass.opts
            if opts.model:
                Converter = opts.model_converter
                converter = Converter()
                declared_fields = converter.fields_for_model(
                    opts.model, opts.sqla_session, keygetter=opts.keygetter)
                break
        base_fields = super(SQLAlchemySchemaMeta, mcs).get_declared_fields(
            klass, *args, **kwargs
        )
        declared_fields.update(base_fields)
        return declared_fields


class SQLAlchemyModelSchema(with_metaclass(SQLAlchemySchemaMeta, ma.Schema)):
    OPTIONS_CLASS = SQLAlchemySchemaOpts
