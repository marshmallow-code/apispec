# -*- coding: utf-8 -*-
import pytest
import mock

from apispec import APISpec, Path
from apispec.exceptions import PluginError, APISpecError


description = 'This is a sample Petstore server.  You can find out more '
'about Swagger at <a href=\"http://swagger.wordnik.com\">http://swagger.wordnik.com</a> '
'or on irc.freenode.net, #swagger.  For this sample, you can use the api '
'key \"special-key\" to test the authorization filters'


@pytest.fixture()
def spec():
    return APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        info={'description': description},
        security=[{'apiKey': []}],
    )


class TestMetadata:

    def test_swagger_version(self, spec):
        assert spec.to_dict()['swagger'] == '2.0'

    def test_swagger_metadata(self, spec):
        metadata = spec.to_dict()
        assert metadata['security'] == [{'apiKey': []}]
        assert metadata['info']['title'] == 'Swagger Petstore'
        assert metadata['info']['version'] == '1.0.0'
        assert metadata['info']['description'] == description


class TestTags:

    tag = {
        'name': 'MyTag',
        'description': 'This tag gathers all API endpoints which are mine.'
    }

    def test_tag(self, spec):
        spec.add_tag(self.tag)
        tags_json = spec.to_dict()['tags']
        assert self.tag in tags_json


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

    def test_definition_description(self, spec):
        model_description = 'An animal which lives with humans.'
        spec.definition('Pet', properties=self.properties, description=model_description)
        defs_json = spec.to_dict()['definitions']
        assert defs_json['Pet']['description'] == model_description

    def test_definition_stores_enum(self, spec):
        enum = ['name', 'photoUrls']
        spec.definition(
            'Pet',
            properties=self.properties,
            enum=enum
        )
        defs_json = spec.to_dict()['definitions']
        assert defs_json['Pet']['enum'] == enum


class TestPath:
    paths = {
        '/pet/{petId}': {
            'get': {
                'parameters': [
                    {
                        'required': True,
                        'format': 'int64',
                        'name': 'petId',
                        'in': 'path',
                        'type': 'integer',
                        'description': 'ID of pet that needs to be fetched'
                    }
                ],
                'responses': {
                    "200": {
                        "schema": {'$ref': '#/definitions/Pet'},
                        'description': 'successful operation'
                    },
                    "400": {
                        "description": "Invalid ID supplied"
                    },
                    "404": {
                        "description": "Pet not found"
                    }
                },
                "produces": [
                    "application/json",
                    "application/xml"
                ],
                "operationId": "getPetById",
                "summary": "Find pet by ID",
                'description': ('Returns a pet when ID < 10.  '
                            'ID > 10 or nonintegers will simulate API error conditions'),
                'tags': ['pet']
            }
        }
    }

    def test_add_path(self, spec):
        route_spec = self.paths['/pet/{petId}']['get']
        spec.add_path(
            path='/pet/{petId}',
            operations=dict(
                get=dict(
                    parameters=route_spec['parameters'],
                    responses=route_spec['responses'],
                    produces=route_spec['produces'],
                    operationId=route_spec['operationId'],
                    summary=route_spec['summary'],
                    description=route_spec['description'],
                    tags=route_spec['tags']
                )
            )
        )

        p = spec._paths['/pet/{petId}']['get']
        assert p['parameters'] == route_spec['parameters']
        assert p['responses'] == route_spec['responses']
        assert p['operationId'] == route_spec['operationId']
        assert p['summary'] == route_spec['summary']
        assert p['description'] == route_spec['description']
        assert p['tags'] == route_spec['tags']

    def test_paths_maintain_order(self, spec):
        spec.add_path(path='/path1')
        spec.add_path(path='/path2')
        spec.add_path(path='/path3')
        spec.add_path(path='/path4')
        assert list(spec.to_dict()['paths'].keys()) == ['/path1', '/path2', '/path3', '/path4']

    def test_add_path_merges_paths(self, spec):
        """Test that adding a second HTTP method to an existing path performs
        a merge operation instead of an overwrite"""
        path = '/pet/{petId}'
        route_spec = self.paths[path]['get']
        spec.add_path(
            path=path,
            operations=dict(
                get=route_spec
            )
        )
        spec.add_path(
            path=path,
            operations=dict(
                put=dict(
                    parameters=route_spec['parameters'],
                    responses=route_spec['responses'],
                    produces=route_spec['produces'],
                    operationId='updatePet',
                    summary='Updates an existing Pet',
                    description='Use this method to make changes to Pet `petId`',
                    tags=route_spec['tags']
                )
            )
        )

        p = spec._paths[path]
        assert 'get' in p
        assert 'put' in p

    def test_add_path_ensures_path_parameters_required(self, spec):
        path = '/pet/{petId}'
        spec.add_path(
            path=path,
            operations=dict(
                put=dict(
                    parameters=[{
                        'name': 'petId',
                        'in': 'path',
                    }]
                )
            )
        )
        assert spec._paths[path]['put']['parameters'][0]['required'] is True

    def test_add_path_with_no_path_raises_error(self, spec):
        with pytest.raises(APISpecError) as excinfo:
            spec.add_path()
        assert 'Path template is not specified' in str(excinfo)

    def test_add_path_strips_base_path(self, spec):
        spec.options['basePath'] = '/v1'
        spec.add_path('/v1/pets')
        assert '/pets' in spec._paths
        assert '/v1/pets' not in spec._paths

    def test_add_path_accepts_path(self, spec):
        route = '/pet/{petId}'
        route_spec = self.paths[route]
        path = Path(path=route, operations={'get': route_spec['get']})
        spec.add_path(path)

        p = spec._paths[path.path]
        assert path.path == p.path
        assert 'get' in p

    def test_add_path_strips_path_base_path(self, spec):
        spec.options['basePath'] = '/v1'
        path = Path(path='/v1/pets')
        spec.add_path(path)
        assert '/pets' in spec._paths
        assert '/v1/pets' not in spec._paths

    def test_add_parameters(self, spec):
        route_spec = self.paths['/pet/{petId}']['get']

        spec.add_parameter('test_parameter', 'path', **route_spec['parameters'][0])

        spec.add_path(
            path='/pet/{petId}',
            operations=dict(
                get=dict(
                    parameters=['test_parameter'],
                )
            )
        )

        metadata = spec.to_dict()
        p = spec._paths['/pet/{petId}']['get']

        assert p['parameters'][0] == {'$ref': '#/parameters/test_parameter'}
        assert route_spec['parameters'][0] == metadata['parameters']['test_parameter']


class TestPlugins:

    DUMMY_PLUGIN = 'tests.plugins.dummy_plugin'

    @mock.patch(DUMMY_PLUGIN + '.setup', autospec=True)
    def test_setup_plugin(self, mock_setup, spec):
        spec.setup_plugin(self.DUMMY_PLUGIN)
        assert self.DUMMY_PLUGIN in spec.plugins
        mock_setup.assert_called_once_with(spec)
        spec.setup_plugin(self.DUMMY_PLUGIN)
        assert mock_setup.call_count == 1

    def test_setup_plugin_doesnt_exist(self, spec):
        with pytest.raises(PluginError):
            spec.setup_plugin('plugin.doesnt.exist')

    def test_setup_plugin_with_no_setup_function_raises_error(self, spec):
        plugin_path = 'tests.plugins.dummy_plugin_no_setup'
        with pytest.raises(PluginError) as excinfo:
            spec.setup_plugin(plugin_path)
        msg = excinfo.value.args[0]
        assert msg == 'Plugin "{0}" has no setup(spec) function'.format(plugin_path)

    def test_register_definition_helper(self, spec):
        def my_definition_helper(name, schema, **kwargs):
            pass
        spec.register_definition_helper(my_definition_helper)
        assert my_definition_helper in spec._definition_helpers

    def test_register_path_helper(self, spec):
        def my_path_helper(**kwargs):
            pass

        spec.register_path_helper(my_path_helper)
        assert my_path_helper in spec._path_helpers

    def test_multiple_path_helpers_w_different_signatures(self, spec):
        def helper1(spec, spam, **kwargs):
            return Path(path='/foo/bar')

        def helper2(spec, eggs, **kwargs):
            return Path(path='/foo/bar')

        spec.register_path_helper(helper1)
        spec.register_path_helper(helper2)

        spec.add_path(eggs=object())

    def test_multiple_definition_helpers_w_different_signatures(self, spec):
        def helper1(spec, name, spam, **kwargs):
            return mock.MagicMock()

        def helper2(spec, name, eggs, **kwargs):
            return mock.MagicMock()

        spec.register_definition_helper(helper1)
        spec.register_definition_helper(helper2)

        spec.definition('SpammitySpam', eggs=mock.MagicMock())


class TestDefinitionHelpers:

    def test_definition_helpers_are_used(self, spec):
        properties = {'properties': {'name': {'type': 'string'}}}

        def definition_helper(spec, name, **kwargs):
            assert type(spec) == APISpec
            return properties
        spec.register_definition_helper(definition_helper)
        spec.definition('Pet', {})
        assert spec._definitions['Pet'] == properties

    def test_multiple_definition_helpers(self, spec):
        def helper1(spec, name, **kwargs):
            return {'properties': {'age': {'type': 'number'}}}

        def helper2(spec, name, fmt, **kwargs):
            return {'properties': {'age': {'type': 'number', 'format': fmt}}}

        spec.register_definition_helper(helper1)
        spec.register_definition_helper(helper2)
        spec.definition('Pet', fmt='int32')
        expected = {'properties': {'age': {'type': 'number', 'format': 'int32'}}}
        assert spec._definitions['Pet'] == expected


class TestPathHelpers:

    def test_path_helper_is_used(self, spec):
        def path_helper(spec, view_func, **kwargs):
            return Path(path=view_func['path'], method='get')
        spec.register_path_helper(path_helper)
        spec.add_path(
            view_func={'path': '/pet/{petId}'},
            operations=dict(
                get=dict(
                    produces=('application/xml', ),
                    responses={
                        "200": {
                            "schema": {'$ref': '#/definitions/Pet'},
                            'description': 'successful operation'
                        }
                    }
                )
            )
        )
        expected = {
            '/pet/{petId}': {
                'get': {
                    'produces': ('application/xml', ),
                    'responses': {
                        '200': {
                            'schema': {'$ref': '#/definitions/Pet'},
                            'description': 'successful operation',
                        }
                    }
                }
            }
        }

        assert spec._paths == expected

class TestResponseHelpers:

    def test_response_helper_is_used(self, spec):
        def success_helper(spec, success_description, **kwargs):
            return {'description': success_description}

        spec.register_response_helper(success_helper, 'get', 200)
        spec.add_path('/pet/{petId}', success_description='success!', operations={
            'get': {
                'responses': {
                    200: {
                        'schema': {'$ref': 'Pet'}
                    }
                }
            }
        })

        resp_obj = spec._paths['/pet/{petId}']['get']['responses'][200]
        assert resp_obj['schema'] == {'$ref': 'Pet'}
        assert resp_obj['description'] == 'success!'
