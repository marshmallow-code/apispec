# -*- coding: utf-8 -*-
import pytest

from apispec import utils
from apispec.exceptions import APISpecError


class TestOpenAPIVersion:
    @pytest.mark.parametrize("version", ("1.0", "4.0"))
    def test_openapi_version_invalid_version(self, version):
        with pytest.raises(APISpecError) as excinfo:
            utils.OpenAPIVersion(version)
        assert "Not a valid OpenAPI version number:" in str(excinfo)

    @pytest.mark.parametrize("version", ("3.0.1", utils.OpenAPIVersion("3.0.1")))
    def test_openapi_version_string_or_openapi_version_param(self, version):
        assert utils.OpenAPIVersion(version) == utils.OpenAPIVersion("3.0.1")

    def test_openapi_version_digits(self):
        ver = utils.OpenAPIVersion("3.0.1")
        assert ver.major == 3
        assert ver.minor == 0
        assert ver.patch == 1
        assert ver.vstring == "3.0.1"
        assert str(ver) == "3.0.1"


def test_reference_path():
    assert utils.reference_path('schema', 2) == '#/definitions/'
    assert utils.reference_path('parameter', 2) == '#/parameters/'
    assert utils.reference_path('response', 2) == '#/responses/'
    assert utils.reference_path('security_scheme', 2) == '#/securityDefinitions/'
    assert utils.reference_path('schema', 3) == '#/components/schemas/'
    assert utils.reference_path('parameter', 3) == '#/components/parameters/'
    assert utils.reference_path('response', 3) == '#/components/responses/'
    assert utils.reference_path('security_scheme', 3) == '#/components/securitySchemes/'
