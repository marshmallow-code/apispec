# -*- coding: utf-8 -*-
import pytest

from apispec import APISpec
from apispec import utils

def test_load_yaml_from_docstring():
    def f():
        """
        Foo
            bar
            baz quux

        ---
        herp: 1
        derp: 2
        """
    result = utils.load_yaml_from_docstring(f.__doc__)
    assert result == {'herp': 1, 'derp': 2}


def test_validate_swagger_is_deprecated():
    spec = APISpec(
        title='Pets',
        version='0.1',
        openapi_version='3.0.0'
    )
    with pytest.warns(DeprecationWarning, match='validate_spec'):
        utils.validate_swagger(spec)
