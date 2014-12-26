# -*- coding: utf-8 -*-

class APISpec(object):

    def __init__(self, *args, **kwargs):
        self.registry = {}
        self._definitions = {}

    def to_dict(self):
        return {
            'definitions': self._definitions,
        }

    def definition(self, name, properties=None, **kwargs):
        ret = {}
        if properties:
            ret['properties'] = properties
        ret.update(kwargs)
        self._definitions[name] = ret
