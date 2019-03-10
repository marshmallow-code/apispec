# -*- coding: utf-8 -*-
# flake8: noqa
import re
import sys

RegexType = type(re.compile(""))

PY2 = int(sys.version[0]) == 2

if PY2:
    unicode = unicode
    basestring = basestring
    iterkeys = lambda d: d.iterkeys()
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()
else:
    unicode = str
    basestring = (str, bytes)
    iterkeys = lambda d: d.keys()
    itervalues = lambda d: d.values()
    iteritems = lambda d: d.items()
