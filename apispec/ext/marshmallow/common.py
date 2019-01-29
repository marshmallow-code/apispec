# -*- coding: utf-8 -*-
"""Utilities to get schema instances/classes"""

import copy
import warnings
from collections import namedtuple

import marshmallow


MODIFIERS = ['only', 'exclude', 'load_only', 'dump_only', 'partial']


def resolve_schema_instance(schema):
    """Return schema instance for given schema (instance or class)

    :param type|Schema|str schema: instance, class or class name of marshmallow.Schema
    :return: schema instance of given schema (instance or class)
    """
    if isinstance(schema, type) and issubclass(schema, marshmallow.Schema):
        return schema()
    if isinstance(schema, marshmallow.Schema):
        return schema
    return marshmallow.class_registry.get_class(schema)()


def resolve_schema_cls(schema):
    """Return schema class for given schema (instance or class)

    :param type|Schema|str: instance, class or class name of marshmallow.Schema
    :return: schema class of given schema (instance or class)
    """
    if isinstance(schema, type) and issubclass(schema, marshmallow.Schema):
        return schema
    if isinstance(schema, marshmallow.Schema):
        return type(schema)
    return marshmallow.class_registry.get_class(schema)


def get_fields(schema):
    """Return fields from schema"""
    if hasattr(schema, 'fields'):
        return schema.fields
    elif hasattr(schema, '_declared_fields'):
        return copy.deepcopy(schema._declared_fields)
    raise ValueError("{0!r} doesn't have either `fields` or `_declared_fields`.".format(schema))


def make_schema_key(schema):
    if not isinstance(schema, marshmallow.Schema):
        raise TypeError('can only make a schema key based on a Schema instance.')
    modifiers = []
    for modifier in MODIFIERS:
        attribute = getattr(schema, modifier)
        try:
            hash(attribute)
        except TypeError:
            attribute = tuple(attribute)
        modifiers.append(attribute)
    return SchemaKey(schema.__class__, *modifiers)


SchemaKey = namedtuple('SchemaKey', ['SchemaClass'] + MODIFIERS)


def get_unique_schema_name(components, name, counter=0):
    """Function to generate a unique name based on the provided name and names
    already in the spec.  Will append a number to the name to make it unique if
    the name is already in the spec.

    :param Components components: instance of the components of the spec
    :param string name: the name to use as a basis for the unique name
    :param int counter: the counter of the number of recursions
    :return: the unique name
    """
    if name not in components._schemas:
        return name
    if not counter:  # first time time through recursion
        warnings.warn(
            'Multiple schemas resolved to the name {} - name has been modified '
            'either manually add each of the schemas with a different name or '
            'provide custom schema_name_resolver'.format(name),
            UserWarning,
        )
    else:  # subsequent recursions
        name = name[:-len(str(counter))]
    counter += 1
    return get_unique_schema_name(components, name + str(counter), counter)
