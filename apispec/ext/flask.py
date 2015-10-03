# -*- coding: utf-8 -*-
"""Flask plugin. Includes a path helper that allows you to pass a view
function to `add_path`.
"""
from __future__ import absolute_import
import re

from flask import current_app

from apispec.compat import iteritems
from apispec import Path
from apispec.exceptions import APISpecError
from apispec import utils

def _rule_for_view(view):
    view_funcs = current_app.view_functions
    endpoint = None
    for ep, view_func in iteritems(view_funcs):
        if view_func == view:
            endpoint = ep
    if not endpoint:
        raise APISpecError('Could not find endpoint for view {0}'.format(view))

    # WARNING: Assume 1 rule per view function for now
    rule = current_app.url_map._rules_by_endpoint[endpoint][0]
    return rule

# from flask-restplus
RE_URL = re.compile(r'<(?:[^:<>]+:)?([^<>]+)>')

def flaskpath2swagger(path):
    """Convert a Flask URL rule to a Swagger-compliant path.

    :param str path: Flask path template.
    """
    return RE_URL.sub(r'{\1}', path)

def path_from_view(spec, view, operations, **kwargs):
    """Path helper that allows passing a Flask view function."""
    rule = _rule_for_view(view)
    path = flaskpath2swagger(rule.rule)
    operations = utils.load_operations_from_docstring(view.__doc__)
    path = Path(path=path, operations=operations)
    return path

def setup(spec):
    """Setup for the plugin."""
    spec.register_path_helper(path_from_view)
