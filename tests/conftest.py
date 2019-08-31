from collections import namedtuple

import pytest

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin


def make_spec(openapi_version):
    ma_plugin = MarshmallowPlugin()
    spec = APISpec(
        title="Validation",
        version="0.1",
        openapi_version=openapi_version,
        plugins=(ma_plugin,),
    )
    return namedtuple("Spec", ("spec", "ma_plugin"))(spec, ma_plugin)


@pytest.fixture(params=("2.0", "3.0.0"))
def spec_fixture(request):
    return make_spec(request.param)


@pytest.fixture(params=("2.0", "3.0.0"))
def spec(request):
    return make_spec(request.param).spec


@pytest.fixture(params=("2.0", "3.0.0"))
def ma_plugin(request):
    return make_spec(request.param).ma_plugin
