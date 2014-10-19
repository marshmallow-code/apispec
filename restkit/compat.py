# -*- coding: utf-8 -*-
import sys

PY2 = int(sys.version[0]) == 2
PY26 = PY2 and int(sys.version_info[1]) < 7

if PY2:
    from itertools import imap
    import urllib2 as request
    from urllib import quote as urlquote
    text_type = unicode
    binary_type = str
    string_types = (str, unicode)
    iterkeys = lambda d: d.iterkeys()
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()
    unicode = unicode
    basestring = basestring
    imap = imap
else:
    from urllib import request
    from urllib.parse import quote as urlquote
    text_type = str
    binary_type = bytes
    string_types = (str,)
    iterkeys = lambda d: d.keys()
    itervalues = lambda d: d.values()
    iteritems = lambda d: d.items()
    unicode = str
    basestring = (str, bytes)
    imap = map
