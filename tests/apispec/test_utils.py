# -*- coding: utf-8 -*-
from smore.apispec import utils

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
