# -*- coding: utf-8 -*-
"""Various utilities for parsing OpenAPI operations from docstrings and validating against
the OpenAPI spec.
"""
import re
import json
import warnings

import yaml

from apispec.compat import iteritems
from apispec import exceptions

# from django.contrib.admindocs.utils
def trim_docstring(docstring):
    """Uniformly trims leading/trailing whitespace from docstrings.

    Based on http://www.python.org/peps/pep-0257.html#handling-docstring-indentation
    """
    if not docstring or not docstring.strip():
        return ''
    # Convert tabs to spaces and split into lines
    lines = docstring.expandtabs().splitlines()
    indent = min(len(line) - len(line.lstrip()) for line in lines if line.lstrip())
    trimmed = [lines[0].lstrip()] + [line[indent:].rstrip() for line in lines[1:]]
    return '\n'.join(trimmed).strip()

# from rest_framework.utils.formatting
def dedent(content):
    """
    Remove leading indent from a block of text.
    Used when generating descriptions from docstrings.
    Note that python's `textwrap.dedent` doesn't quite cut it,
    as it fails to dedent multiline docstrings that include
    unindented text on the initial line.
    """
    whitespace_counts = [len(line) - len(line.lstrip(' '))
                         for line in content.splitlines()[1:] if line.lstrip()]

    # unindent the content if needed
    if whitespace_counts:
        whitespace_pattern = '^' + (' ' * min(whitespace_counts))
        content = re.sub(re.compile(whitespace_pattern, re.MULTILINE), '', content)

    return content.strip()

def load_yaml_from_docstring(docstring):
    """Loads YAML from docstring."""
    split_lines = trim_docstring(docstring).split('\n')

    # Cut YAML from rest of docstring
    for index, line in enumerate(split_lines):
        line = line.strip()
        if line.startswith('---'):
            cut_from = index
            break
    else:
        return None

    yaml_string = '\n'.join(split_lines[cut_from:])
    yaml_string = dedent(yaml_string)
    return yaml.load(yaml_string)


PATH_KEYS = set([
    'get',
    'put',
    'post',
    'delete',
    'options',
    'head',
    'patch',
])

def load_operations_from_docstring(docstring):
    """Return a dictionary of Swagger operations parsed from a
    a docstring.
    """
    doc_data = load_yaml_from_docstring(docstring)
    if doc_data:
        return {key: val for key, val in iteritems(doc_data)
                        if key in PATH_KEYS or key.startswith('x-')}
    else:
        return None

def validate_spec(spec):
    """Validate the output of an :class:`APISpec` object against the
    OpenAPI specification.

    Note: Requires installing apispec with the ``[validation]`` extras.
    ::

        pip install 'apispec[validation]'

    :raise: apispec.exceptions.OpenAPIError if validation fails.
    """
    try:
        import prance
    except ImportError as error:  # re-raise with a more verbose message
        exc_class = type(error)
        raise exc_class(
            'validate_swagger requires prance to be installed. '
            'You can install all validation requirements using:\n'
            "    pip install 'apispec[validation]'"
        )
    parser_kwargs = {}
    if spec.openapi_version.version[0] == 3:
        parser_kwargs['backend'] = 'openapi-spec-validator'
    try:
        prance.BaseParser(spec_string=json.dumps(spec.to_dict()), **parser_kwargs)
    except prance.ValidationError as err:
        raise exceptions.OpenAPIError(*err.args)
    else:
        return True

def validate_swagger(spec):
    """
    .. deprecated:: 0.38.0
        Use `apispec.utils.validate_spec` instead.
    """
    warnings.warn(
        'apispec.utils.validate_swagger is deprecated. Use apispec.utils.validate_spec instead.',
        DeprecationWarning
    )
    return validate_spec(spec)
