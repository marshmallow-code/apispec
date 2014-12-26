# -*- coding: utf-8 -*-

from .exceptions import PluginError

class APISpec(object):

    def __init__(self, *args, **kwargs):
        self.registry = {}
        self._definitions = {}
        self._extensions = {}

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

    # PLUGIN INTERFACE

    # adapted from Sphinx
    def setup_plugin(self, name):
        """Import and setup a plugin. No-op if called twice
        for the same plugin.

        :param str name: Import path to the plugin.
        :raise: PluginError if the given plugin is invalid.
        """
        if name in self._extensions:
            return
        try:
            mod = __import__(
                name, globals=None, locals=None, fromlist=('setup', )
            )
        except ImportError:
            raise PluginError(
                'Could not import plugin "{0}"'.format(name)
            )
        try:
            mod.setup(self)
        except AttributeError:
            raise PluginError('Plugin "{0}" has no setup() function.')
        self._extensions[name] = mod
        return None
