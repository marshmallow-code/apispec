# -*- coding: utf-8 -*-
import sys

PY2 = int(sys.version[0]) == 2

if PY2:
    text_type = unicode  # noqa: F821
    binary_type = str
    string_types = (str, unicode)  # noqa: F821
    unicode = unicode  # noqa: F821
    basestring = basestring  # noqa: F821
    iterkeys = lambda d: d.iterkeys()  # noqa: E731
    itervalues = lambda d: d.itervalues()  # noqa: E731
    iteritems = lambda d: d.iteritems()  # noqa: E731
else:
    text_type = str
    binary_type = bytes
    string_types = (str,)
    unicode = str
    basestring = (str, bytes)
    iterkeys = lambda d: d.keys()  # noqa: E731
    itervalues = lambda d: d.values()  # noqa: E731
    iteritems = lambda d: d.items()  # noqa: E731
