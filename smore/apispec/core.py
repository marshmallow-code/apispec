# -*- coding: utf-8 -*-

from .exceptions import PluginError

class APISpec(object):

    def __init__(self, *args, **kwargs):
        # Metadata
        self._definitions = {}
        # Plugin and helpers
        self._plugins = {}
        self._definition_helpers = []

    def to_dict(self):
        return {
            'definitions': self._definitions,
        }

    def definition(self, name, properties=None, **kwargs):
        ret = {}
        if properties:
            ret['properties'] = properties
        for func in self._definition_helpers:
            ret.update(func(name, **kwargs))
        self._definitions[name] = ret

    # PLUGIN INTERFACE

    # adapted from Sphinx
    def setup_plugin(self, name):
        """Import and setup a plugin. No-op if called twice
        for the same plugin.

        :param str name: Import path to the plugin.
        :raise: PluginError if the given plugin is invalid.
        """
        if name in self._plugins:
            return
        try:
            mod = __import__(
                name, globals=None, locals=None, fromlist=('setup', )
            )
        except ImportError:
            raise PluginError(
                'Could not import plugin "{0}"'.format(name)
            )
        if not hasattr(mod, 'setup'):
            raise PluginError('Plugin "{0}" has no setup() function.')
        else:
            mod.setup(self)
        self._plugins[name] = mod
        return None

    def register_definition_helper(self, func):
        """Register a new definition helper. The helper **must** meet the following conditions:

        - Receive the definition `name` as the first argument.
        - Receive **kwargs.
        - Return a `dict` representation of the definition's Schema object.

        The helper may define any named arguments after the `name` argument.

        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#definitionsObject

        :param callable func: The definition helper function.
        """
        self._definition_helpers.append(func)
