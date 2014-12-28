# -*- coding: utf-8 -*-
import pytest
try:
    from unittest import mock
except ImportError:
    import mock

from smore.apispec import APISpec
from smore.apispec.exceptions import PluginError


@pytest.fixture()
def spec():
    return APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        description='This is a sample Petstore server.  You can find out more '
        'about Swagger at <a href=\"http://swagger.wordnik.com\">http://swagger.wordnik.com</a> '
        'or on irc.freenode.net, #swagger.  For this sample, you can use the api '
        'key \"special-key\" to test the authorization filters'
    )


class TestDefinitions:

    properties = {
        'id': {'type': 'integer', 'format': 'int64'},
        'name': {'type': 'string', 'example': 'doggie'},
    }

    def test_definition(self, spec):
        spec.definition('Pet', properties=self.properties)
        defs_json = spec.to_dict()['definitions']
        assert 'Pet' in defs_json
        assert defs_json['Pet']['properties'] == self.properties

    def test_definition_stores_kwargs(self, spec):
        enum = ['name', 'photoUrls']
        spec.definition(
            'Pet',
            properties=self.properties,
            enum=enum
        )
        defs_json = spec.to_dict()['definitions']
        assert defs_json['Pet']['enum'] == enum


class TestExtensions:

    @mock.patch('tests.plugins.dummy_plugin.setup')
    def test_setup_plugin(self, mock_setup, spec):
        spec.setup_plugin('tests.plugins.dummy_plugin')
        assert 'tests.plugins.dummy_plugin' in spec._plugins
        mock_setup.assert_called_once
        spec.setup_plugin('tests.plugins.dummy_plugin')
        assert mock_setup.call_count == 1

    def test_setup_plugin_doesnt_exist(self, spec):
        with pytest.raises(PluginError):
            spec.setup_plugin('plugin.doesnt.exist')

    def test_register_definition_helper(self, spec):
        def my_definition_helper(name, schema, **kwargs):
            pass
        spec.register_definition_helper(my_definition_helper)
        assert my_definition_helper in spec._definition_helpers


class TestDefinitionHelpers:

    def test_definition_helpers_are_used(self, spec):
        properties = {'properties': {'name': {'type': 'string'}}}

        def definition_helper(name, **kwargs):
            return properties
        spec.register_definition_helper(definition_helper)
        spec.definition('Pet', {})
        assert spec._definitions['Pet'] == properties

    def test_multiple_definition_helpers(self, spec):
        def helper1(name, **kwargs):
            return {'properties': {'age': {'type': 'number'}}}

        def helper2(name, fmt, **kwargs):
            return {'properties': {'age': {'type': 'number', 'format': fmt}}}

        spec.register_definition_helper(helper1)
        spec.register_definition_helper(helper2)
        spec.definition('Pet', fmt='int32')
        expected = {'properties': {'age': {'type': 'number', 'format': 'int32'}}}
        assert spec._definitions['Pet'] == expected
