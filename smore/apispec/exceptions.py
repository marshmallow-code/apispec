# -*- coding: utf-8 -*-

from smore.exceptions import SmoreError

class APISpecError(SmoreError):
    pass

class PluginError(APISpecError):
    pass
