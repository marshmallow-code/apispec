# -*- coding: utf-8 -*-
"""
.. module:: webapp2
   :synopsis: Automatic documentation from your webapp2 project

The :mod:`smore.ext.webapp2 <webapp2>` module generates swagger path objects from your routes

"""
from __future__ import absolute_import

import webapp2
from marshmallow.compat import iteritems, basestring
from smore.apispec import Path
from smore.apispec.exceptions import APISpecError
from smore.apispec import utils


def path_from_route(spec, route, operations=None, **kwargs):
    """Creates a :class:`smore.apispec.Path` object based off of a :class:`webapp2.Route`
    and their subclasses

    :param smore.apispec.APISpec spec:
    :param webapp2.Route route:
    :param kwargs:
    :return: The generated :class:`Path <smore.apispec.Path>` object
    :rtype: smore.apispec.Path
    """
    # make sure route.reverse_template is lazy loaded
    getattr(route, 'regex', None)
    path = route.reverse_template.replace('%(', '{').replace(')s', '}')
    methods = route.methods if route.methods else ['GET', 'POST', 'PUT', 'DELETE']
    merge_ops = {method.lower(): {} for method in methods}
    for method, details in iteritems(operations or {}):
        if method not in merge_ops:
            raise APISpecError("Method {0} is not handled by route {0}".format(method, path))
        merge_ops[method].update(details)
    handler = route.handler
    if isinstance(handler, basestring):
        if handler not in _route_cache.handlers:
            _route_cache[handler] = handler = webapp2.import_string(handler)
        else:
            handler = _route_cache[handler]
    for method, details in iteritems(merge_ops):
        try_method = route.handler_method or method.lower().replace('-', '_')
        handler_method = getattr(handler, try_method, None)
        docops = utils.load_operations_from_docstring(getattr(handler_method, '__doc__', ''))
        # Merge in any `method`: yaml subsection
        if docops and docops.get(method, None):
            details.update(docops.get(method))
    path = Path(path=path, operations=merge_ops)
    return path


def setup(spec):
    """Register plugin with the :class:`smore.apispec.APISpec`

    :param smore.apispec.APISpec spec: The APISpec instance the plugin will register data onto
    """
    spec.register_path_helper(path_from_route)

_route_cache = {}

__all__ = ['path_from_route', 'setup']
