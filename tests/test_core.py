# -*- coding: utf-8 -*-
from collections import OrderedDict

import pytest
import yaml

from apispec import APISpec, BasePlugin
from apispec.exceptions import APISpecError

from .utils import get_definitions, get_paths, get_parameters, get_responses


description = 'This is a sample Petstore server.  You can find out more '
'about Swagger at <a href=\"http://swagger.wordnik.com\">http://swagger.wordnik.com</a> '
'or on irc.freenode.net, #swagger.  For this sample, you can use the api '
'key \"special-key\" to test the authorization filters'


@pytest.fixture(params=('2.0', '3.0.0'))
def spec(request):
    openapi_version = request.param
    if openapi_version == '2.0':
        security_kwargs = {
            'security': [{'apiKey': []}],
        }
    else:
        security_kwargs = {
            'components': {
                'securitySchemes': {
                    'bearerAuth':
                        dict(type='http', scheme='bearer', bearerFormat='JWT'),
                },
                'schemas': {
                    'ErrorResponse': {
                        'type': 'object',
                        'properties': {
                            'ok': {
                                'type': 'boolean', 'description': 'status indicator', 'example': False,
                            },
                        },
                        'required': ['ok'],
                    },
                },
            },
        }
    return APISpec(
        title='Swagger Petstore',
        version='1.0.0',
        openapi_version=openapi_version,
        info={'description': description},
        **security_kwargs
    )


class TestAPISpecInit:

    def test_raises_wrong_apispec_version(self):
        with pytest.raises(APISpecError) as excinfo:
            APISpec(
                'Swagger Petstore',
                version='1.0.0',
                openapi_version='4.0',  # 4.0 is not supported
                info={'description': description},
                security=[{'apiKey': []}],
            )
        assert 'Not a valid OpenAPI version number:' in str(excinfo)


class TestMetadata:

    def test_openapi_metadata(self, spec):
        metadata = spec.to_dict()
        assert metadata['info']['title'] == 'Swagger Petstore'
        assert metadata['info']['version'] == '1.0.0'
        assert metadata['info']['description'] == description
        if spec.openapi_version.major < 3:
            assert metadata['swagger'] == spec.openapi_version.vstring
            assert metadata['security'] == [{'apiKey': []}]
        else:
            assert metadata['openapi'] == spec.openapi_version.vstring
            security_schemes = {'bearerAuth': dict(type='http', scheme='bearer', bearerFormat='JWT')}
            assert metadata['components']['securitySchemes'] == security_schemes
            assert metadata['components']['schemas'].get('ErrorResponse', False)
            assert metadata['info']['title'] == 'Swagger Petstore'
            assert metadata['info']['version'] == '1.0.0'
            assert metadata['info']['description'] == description

    @pytest.mark.parametrize('spec', ('3.0.0', ), indirect=True)
    def test_openapi_metadata_merge_v3(self, spec):
        properties = {
            'ok': {
                'type': 'boolean', 'description': 'property description', 'example': True,
            },
        }
        spec.components.schema('definition', properties=properties, description='definiton description')
        metadata = spec.to_dict()
        assert metadata['components']['schemas'].get('ErrorResponse', False)
        assert metadata['components']['schemas'].get('definition', False)


class TestTags:

    tag = {
        'name': 'MyTag',
        'description': 'This tag gathers all API endpoints which are mine.',
    }

    def test_tag(self, spec):
        spec.tag(self.tag)
        tags_json = spec.to_dict()['tags']
        assert self.tag in tags_json

    def test_tag_is_chainable(self, spec):
        spec.tag({'name': 'tag1'}).tag({'name': 'tag2'})
        assert spec.to_dict()['tags'] == [{'name': 'tag1'}, {'name': 'tag2'}]


class TestDefinitions:

    properties = {
        'id': {'type': 'integer', 'format': 'int64'},
        'name': {'type': 'string', 'example': 'doggie'},
    }

    def test_definition(self, spec):
        spec.components.schema('Pet', properties=self.properties)
        if spec.openapi_version.major < 3:
            defs = spec.to_dict()['definitions']
        else:
            defs = spec.to_dict()['components']['schemas']
        assert 'Pet' in defs
        assert defs['Pet']['properties'] == self.properties

    def test_definition_is_chainable(self, spec):
        spec.components.schema('Pet', properties={}).schema('Plant', properties={})
        if spec.openapi_version.major < 3:
            defs = spec.to_dict()['definitions']
        else:
            defs = spec.to_dict()['components']['schemas']
        assert 'Pet' in defs
        assert 'Plant' in defs

    def test_definition_description(self, spec):
        model_description = 'An animal which lives with humans.'
        spec.components.schema('Pet', properties=self.properties, description=model_description)
        if spec.openapi_version.major < 3:
            defs = spec.to_dict()['definitions']
        else:
            defs = spec.to_dict()['components']['schemas']
        assert defs['Pet']['description'] == model_description

    def test_definition_stores_enum(self, spec):
        enum = ['name', 'photoUrls']
        spec.components.schema(
            'Pet',
            properties=self.properties,
            enum=enum,
        )
        if spec.openapi_version.major < 3:
            defs = spec.to_dict()['definitions']
        else:
            defs = spec.to_dict()['components']['schemas']
        assert defs['Pet']['enum'] == enum

    def test_definition_extra_fields(self, spec):
        extra_fields = {'discriminator': 'name'}
        spec.components.schema('Pet', properties=self.properties, extra_fields=extra_fields)
        if spec.openapi_version.major < 3:
            defs = spec.to_dict()['definitions']
        else:
            defs = spec.to_dict()['components']['schemas']
        assert defs['Pet']['discriminator'] == 'name'

    def test_to_yaml(self, spec):
        enum = ['name', 'photoUrls']
        spec.components.schema(
            'Pet',
            properties=self.properties,
            enum=enum,
        )
        assert spec.to_dict() == yaml.safe_load(spec.to_yaml())

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
                        'description': 'ID of pet that needs to be fetched',
                    },
                ],
                'responses': {
                    '200': {
                        'schema': {'$ref': '#/definitions/Pet'},
                        'description': 'successful operation',
                    },
                    '400': {
                        'description': 'Invalid ID supplied',
                    },
                    '404': {
                        'description': 'Pet not found',
                    },
                },
                'produces': [
                    'application/json',
                    'application/xml',
                ],
                'operationId': 'getPetById',
                'summary': 'Find pet by ID',
                'description': (
                    'Returns a pet when ID < 10.  '
                    'ID > 10 or nonintegers will simulate API error conditions'
                ),
                'tags': ['pet'],
            },
        },
    }

    def test_path(self, spec):
        route_spec = self.paths['/pet/{petId}']['get']
        spec.path(
            path='/pet/{petId}',
            operations=dict(
                get=dict(
                    parameters=route_spec['parameters'],
                    responses=route_spec['responses'],
                    produces=route_spec['produces'],
                    operationId=route_spec['operationId'],
                    summary=route_spec['summary'],
                    description=route_spec['description'],
                    tags=route_spec['tags'],
                ),
            ),
        )

        p = get_paths(spec)['/pet/{petId}']['get']
        assert p['parameters'] == route_spec['parameters']
        assert p['responses'] == route_spec['responses']
        assert p['operationId'] == route_spec['operationId']
        assert p['summary'] == route_spec['summary']
        assert p['description'] == route_spec['description']
        assert p['tags'] == route_spec['tags']

    def test_paths_maintain_order(self, spec):
        spec.path(path='/path1')
        spec.path(path='/path2')
        spec.path(path='/path3')
        spec.path(path='/path4')
        assert list(spec.to_dict()['paths'].keys()) == ['/path1', '/path2', '/path3', '/path4']

    def test_paths_is_chainable(self, spec):
        spec.path(path='/path1').path('/path2')
        assert list(spec.to_dict()['paths'].keys()) == ['/path1', '/path2']

    def test_methods_maintain_order(self, spec):
        methods = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
        for method in methods:
            spec.path(path='/path', operations=OrderedDict({method: {}}))
        assert list(spec.to_dict()['paths']['/path']) == methods

    def test_path_merges_paths(self, spec):
        """Test that adding a second HTTP method to an existing path performs
        a merge operation instead of an overwrite"""
        path = '/pet/{petId}'
        route_spec = self.paths[path]['get']
        spec.path(
            path=path,
            operations=dict(
                get=route_spec,
            ),
        )
        spec.path(
            path=path,
            operations=dict(
                put=dict(
                    parameters=route_spec['parameters'],
                    responses=route_spec['responses'],
                    produces=route_spec['produces'],
                    operationId='updatePet',
                    summary='Updates an existing Pet',
                    description='Use this method to make changes to Pet `petId`',
                    tags=route_spec['tags'],
                ),
            ),
        )

        p = get_paths(spec)[path]
        assert 'get' in p
        assert 'put' in p

    def test_path_ensures_path_parameters_required(self, spec):
        path = '/pet/{petId}'
        spec.path(
            path=path,
            operations=dict(
                put=dict(
                    parameters=[{
                        'name': 'petId',
                        'in': 'path',
                    }],
                ),
            ),
        )
        assert get_paths(spec)[path]['put']['parameters'][0]['required'] is True

    def test_path_with_no_path_raises_error(self, spec):
        with pytest.raises(APISpecError) as excinfo:
            spec.path()
        assert 'Path template is not specified' in str(excinfo)

    def test_parameter(self, spec):
        route_spec = self.paths['/pet/{petId}']['get']

        spec.components.parameter('test_parameter', 'path', **route_spec['parameters'][0])

        spec.path(
            path='/pet/{petId}',
            operations={'get': {'parameters': ['test_parameter']}},
        )

        metadata = spec.to_dict()
        p = get_paths(spec)['/pet/{petId}']['get']

        if spec.openapi_version.major < 3:
            assert p['parameters'][0] == {'$ref': '#/parameters/test_parameter'}
            assert route_spec['parameters'][0] == metadata['parameters']['test_parameter']
        else:
            assert p['parameters'][0] == {'$ref': '#/components/parameters/test_parameter'}
            assert route_spec['parameters'][0] == metadata['components']['parameters']['test_parameter']

    def test_parameter_is_chainable(self, spec):
        spec.components.parameter('param1', 'path').parameter('param2', 'path')
        if spec.openapi_version.major < 3:
            params = spec.to_dict()['parameters']
        else:
            params = spec.to_dict()['components']['parameters']
        assert 'param1' in params
        assert 'param2' in params

    def test_response(self, spec):
        route_spec = self.paths['/pet/{petId}']['get']

        spec.components.response('test_response', **route_spec['responses']['200'])

        spec.path(
            path='/pet/{petId}',
            operations={'get': {'responses': {'200': 'test_response'}}},
        )

        metadata = spec.to_dict()
        p = get_paths(spec)['/pet/{petId}']['get']

        if spec.openapi_version.major < 3:
            assert p['responses']['200'] == {'$ref': '#/responses/test_response'}
            assert route_spec['responses']['200'] == metadata['responses']['test_response']
        else:
            assert p['responses']['200'] == {'$ref': '#/components/responses/test_response'}
            assert route_spec['responses']['200'] == metadata['components']['responses']['test_response']

    def test_response_is_chainable(self, spec):
        spec.components.response('resp1').response('resp2')
        if spec.openapi_version.major < 3:
            responses = spec.to_dict()['responses']
        else:
            responses = spec.to_dict()['components']['responses']
        assert 'resp1' in responses
        assert 'resp2' in responses

    def test_path_check_invalid_http_method(self, spec):
        spec.path('/pet/{petId}', operations={'get': {}})
        spec.path('/pet/{petId}', operations={'x-dummy': {}})
        with pytest.raises(APISpecError) as excinfo:
            spec.path('/pet/{petId}', operations={'dummy': {}})
        assert 'One or more HTTP methods are invalid' in str(excinfo)


class TestPlugins:

    @staticmethod
    def test_plugin_factory(return_none=False):

        class TestPlugin(BasePlugin):
            def schema_helper(self, name, definition, **kwargs):
                if not return_none:
                    return {'properties': {'name': {'type': 'string'}}}

            def parameter_helper(self, **kwargs):
                if not return_none:
                    return {'description': 'some parameter'}

            def response_helper(self, **kwargs):
                if not return_none:
                    return {'description': '42'}

            def path_helper(self, path, operations, **kwargs):
                if not return_none:
                    if path == '/path_1':
                        operations.update({'get': {'responses': {'200': {}}}})
                        return '/path_1_modified'

            def operation_helper(self, path, operations, **kwargs):
                if path == '/path_2':
                    operations['post'] = {'responses': {'201': {}}}

        return TestPlugin()

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.0'))
    @pytest.mark.parametrize('return_none', (True, False))
    def test_plugin_schema_helper_is_used(self, openapi_version, return_none):
        spec = APISpec(
            title='Swagger Petstore',
            version='1.0.0',
            openapi_version=openapi_version,
            plugins=(self.test_plugin_factory(return_none), ),
        )
        spec.components.schema('Pet', {})
        definitions = get_definitions(spec)
        if return_none:
            assert definitions['Pet'] == {}
        else:
            assert definitions['Pet'] == {'properties': {'name': {'type': 'string'}}}

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.0'))
    @pytest.mark.parametrize('return_none', (True, False))
    def test_plugin_parameter_helper_is_used(self, openapi_version, return_none):
        spec = APISpec(
            title='Swagger Petstore',
            version='1.0.0',
            openapi_version=openapi_version,
            plugins=(self.test_plugin_factory(return_none), ),
        )
        spec.components.parameter('Pet', 'body', **{})
        parameters = get_parameters(spec)
        if return_none:
            assert parameters['Pet'] == {'in': 'body', 'name': 'Pet'}
        else:
            assert parameters['Pet'] == {'in': 'body', 'name': 'Pet', 'description': 'some parameter'}

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.0'))
    @pytest.mark.parametrize('return_none', (True, False))
    def test_plugin_response_helper_is_used(self, openapi_version, return_none):
        spec = APISpec(
            title='Swagger Petstore',
            version='1.0.0',
            openapi_version=openapi_version,
            plugins=(self.test_plugin_factory(return_none), ),
        )
        spec.components.response('Pet', **{})
        responses = get_responses(spec)
        if return_none:
            assert responses['Pet'] == {}
        else:
            assert responses['Pet'] == {'description': '42'}

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.0'))
    @pytest.mark.parametrize('return_none', (True, False))
    def test_plugin_path_helper_is_used(self, openapi_version, return_none):
        spec = APISpec(
            title='Swagger Petstore',
            version='1.0.0',
            openapi_version=openapi_version,
            plugins=(self.test_plugin_factory(return_none), ),
        )
        spec.path('/path_1')
        paths = get_paths(spec)
        assert len(paths) == 1
        if return_none:
            assert paths['/path_1'] == {}
        else:
            assert paths['/path_1_modified'] == {'get': {'responses': {'200': {}}}}

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.0'))
    def test_plugin_operation_helper_is_used(self, openapi_version):
        spec = APISpec(
            title='Swagger Petstore',
            version='1.0.0',
            openapi_version=openapi_version,
            plugins=(self.test_plugin_factory(), ),
        )
        spec.path('/path_2', operations={'post': {'responses': {'200': {}}}})
        paths = get_paths(spec)
        assert len(paths) == 1
        assert paths['/path_2'] == {'post': {'responses': {'201': {}}}}


class TestPluginsOrder:

    class OrderedPlugin(BasePlugin):

        def __init__(self, index, output):
            super(TestPluginsOrder.OrderedPlugin, self).__init__()
            self.index = index
            self.output = output

        def path_helper(self, path, operations, **kwargs):
            self.output.append('plugin_{}_path'.format(self.index))

        def operation_helper(self, path, operations, **kwargs):
            self.output.append('plugin_{}_operations'.format(self.index))

    def test_plugins_order(self):
        """Test plugins execution order in APISpec.path

        - All path helpers are called, then all operation helpers, then all response helpers.
        - At each step, helpers are executed in the order the plugins are passed to APISpec.
        """
        output = []
        spec = APISpec(
            title='Swagger Petstore',
            version='1.0.0',
            openapi_version='3.0.0',
            plugins=(self.OrderedPlugin(1, output), self.OrderedPlugin(2, output)),
        )
        spec.path('/path', operations={'get': {'responses': {200: {}}}})
        assert output == [
            'plugin_1_path', 'plugin_2_path',
            'plugin_1_operations', 'plugin_2_operations',
        ]
