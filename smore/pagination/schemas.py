# -*- coding: utf-8 -*-

import six
import marshmallow as ma


class PageSchemaOpts(ma.schema.SchemaOpts):
    def __init__(self, meta):
        super(PageSchemaOpts, self).__init__(meta)
        self.results_schema_class = getattr(meta, 'results_schema_class', None)
        self.results_field_name = getattr(meta, 'results_field_name', 'results')
        self.results_schema_options = getattr(meta, 'results_schema_options', {})


class PageMeta(ma.schema.SchemaMeta):
    """Metaclass for `PageSchema` that creates a `Nested` field based on the
    options configured in `OPTIONS_CLASS`.
    """
    def __new__(mcs, name, bases, attrs):
        klass = super().__new__(mcs, name, bases, attrs)
        opts = klass.OPTIONS_CLASS(klass.Meta)
        klass._declared_fields[opts.results_field_name] = ma.fields.Nested(
            opts.results_schema_class,
            attribute='results',
            many=True,
            **opts.results_schema_options
        )
        return klass


class BaseInfoSchema(ma.Schema):
    count = ma.fields.Integer()
    pages = ma.fields.Integer()
    per_page = ma.fields.Integer()


class OffsetInfoSchema(BaseInfoSchema):
    page = ma.fields.Integer()


class SeekInfoSchema(BaseInfoSchema):
    last_indexes = ma.fields.Raw()


class OffsetPageSchema(six.with_metaclass(PageMeta, ma.Schema)):
    OPTIONS_CLASS = PageSchemaOpts
    pagination = ma.fields.Nested(OffsetInfoSchema, attribute='info')


class SeekPageSchema(six.with_metaclass(PageMeta, ma.Schema)):
    OPTIONS_CLASS = PageSchemaOpts
    pagination = ma.fields.Nested(SeekInfoSchema, attribute='info')
