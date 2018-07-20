# -*- coding: utf-8 -*-
from apispec import yaml_utils

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
    result = yaml_utils.load_yaml_from_docstring(f.__doc__)
    assert result == {'herp': 1, 'derp': 2}
