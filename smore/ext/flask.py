# -*- coding: utf-8 -*-
from __future__ import absolute_import

from flask import current_app

from marshmallow.compat import iteritems
from smore.apispec import Path
from smore.apispec.exceptions import APISpecError

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

def path_from_view(view, operations, **kwargs):
    rule = _rule_for_view(view)
    path = rule.rule
    path = Path(path=path, operations=operations)
    return path


def setup(spec):
    spec.register_path_helper(path_from_view)
