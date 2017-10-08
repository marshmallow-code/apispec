# -*- coding: utf-8 -*-
"""AioHTTP plugin. Includes a path helper that allows you to pass a view
function/class to `add_path`. Inspects URL routes and view docstrings.

from aiohttp import web

async def index_view(request):
    '''Index view
    ---
    responses:
        200:
            schema:
                $ref: '#/definitions/Gist'
    '''
    return web.json_response(data={'data': 'Hello, world'})


class GistView(web.View):
    async def get(self):
        '''Gist view
        ---
        responses:
            200: OK
        '''
        return web.json_response(data={'data': 'Hello, world'})

    async def post(self):
        '''Without documentation'''
        return web.Response(text="POST method")

def create_app():
    app = web.Application()

    # Config app routing
    app.router.add_get('/', index_view)
    app.router.add_route('*', '/gist', GistView)

    return app

...
spec.add_path(view=index_view, app=app)
spec.add_path(view=GistView, app=app)
print(dict(spec.to_dict()['paths']))
# {
#   "paths": {
#     "/": {
#       "head": {
#         "responses": {"200": {"schema": {"$ref": "#/definitions/Gist"}}}
#       },
#       "get": {
#         "responses": {"200": {"schema": {"$ref": "#/definitions/Gist"}}}
#       }
#     },
#     "/gist": {"get": {"responses": {"200": "OK"}}}
#   }
# }

"""
from __future__ import absolute_import

from urllib.parse import urljoin

from aiohttp.web import View

from apispec import Path
from apispec.exceptions import APISpecError
from apispec import utils


def setup(spec):
    """Setup for the plugin."""
    spec.register_path_helper(path_from_view)


def path_from_view(spec, view, app, **kwargs):
    """
    Path helper that allows passing an AioHTTP
    view fucntion/class and app instance.
    ATTENTION: Assume one route per view function/class for now
    """
    app_root = '/'

    view_routes = _get_routes_for_view(view=view, app=app)
    if not view_routes:
        raise APISpecError('Could not find route for view {0}'.format(view))

    routes_by_path = {}
    for route in view_routes:
        path_info = route.resource.get_info()
        if path_info.get("path", None):
            path = path_info.get("path")
        else:
            path = path_info.get("formatter")

        if not path:
            continue

        if path not in routes_by_path:
            routes_by_path[path] = []
        routes_by_path[path].append(route)

    if not routes_by_path:
        raise APISpecError('Could not find path for view {0}'.format(view))

    path, routes = list(routes_by_path.items())[0]
    app_path = urljoin(app_root.rstrip('/') + '/', path.lstrip('/'))
    return Path(path=app_path, operations=_get_operations_for_routes(routes))


def _get_routes_for_view(view, app):
    return [route for route in app.router.routes() if route.handler == view]


def _get_operations_for_routes(routes):
    operations = {}
    for route in routes:
        operations.update(_get_operations_for_route(route))
    return operations


def _get_operations_for_route(route):
    operations = {}

    if issubclass(route.handler, View):
        for http_method in utils.PATH_KEYS:
            view_method = getattr(route.handler, http_method.lower(), None)
            operation = (
                utils.load_yaml_from_docstring(view_method.__doc__)
                if view_method else None
            )
            if operation:
                operations[http_method.lower()] = operation
        return operations

    if route.method.lower() in utils.PATH_KEYS:
        operation = utils.load_yaml_from_docstring(route.handler.__doc__)
        if operation:
            operations[route.method.lower()] = operation
    elif route.method == '*':
        operations.update(
            utils.load_operations_from_docstring(
                route.handler.__doc__
            ) or {}
        )
    return operations
