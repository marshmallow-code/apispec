import pytest
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
    assert result == {"herp": 1, "derp": 2}


@pytest.mark.parametrize("docstring", (None, "", "---"))
def test_load_yaml_from_docstring_empty_docstring(docstring):
    assert yaml_utils.load_yaml_from_docstring(docstring) == {}


@pytest.mark.parametrize("docstring", (None, "", "---"))
def test_load_operations_from_docstring_empty_docstring(docstring):
    assert yaml_utils.load_operations_from_docstring(docstring) == {}


def test_dict_to_yaml_unicode():
    assert yaml_utils.dict_to_yaml({"가": "나"}) == '"\\uAC00": "\\uB098"\n'
    assert yaml_utils.dict_to_yaml({"가": "나"}, {"allow_unicode": True}) == "가: 나\n"
