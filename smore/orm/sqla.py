from marshmallow import Schema, validate

from sqlalchemy.orm.properties import ColumnProperty

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
        FieldClass = Schema.TYPE_MAPPING[prop.columns[0].type.python_type]
        kwargs = field_kwargs_for_property(prop)
        return FieldClass(**kwargs)
    # TODO: Relationships

def fields_for_model(model):
    """Generate a dictionary of fields given a SQLA model."""
    result = {}
    for prop in model.__mapper__.iterate_properties:
        field = None
        # Normal column -> marshmallow field
        field = property2field(prop)
        if field:
            result[prop.key] = field
    return result
