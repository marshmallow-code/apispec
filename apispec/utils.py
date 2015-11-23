# -*- coding: utf-8 -*-
import re
import json
import tempfile
import subprocess

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
    return "\n".join(trimmed).strip()

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

    yaml_string = "\n".join(split_lines[cut_from:])
    yaml_string = dedent(yaml_string)
    try:
        return yaml.load(yaml_string)
    except yaml.YAMLError:
        return None

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
                        if key in PATH_KEYS}
    else:
        return None

def validate_swagger(spec):
    """Validate the output of an :class:`APISpec` object.
    Note: Requires installing the node package `swagger-tools`.

    :raise: SwaggerError if validation fails.
    """
    with tempfile.NamedTemporaryFile(mode='w') as fp:
        json.dump(spec.to_dict(), fp)
        fp.seek(0)
        try:
            subprocess.check_output(
                ['swagger-tools', 'validate', fp.name],
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as error:
            raise exceptions.SwaggerError(error.output.decode('utf-8'))
