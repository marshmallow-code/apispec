# -*- coding: utf-8 -*-
"""Various utilities for parsing OpenAPI operations from docstrings and validating against
the OpenAPI spec.
"""
import json
import warnings

from distutils import version

from apispec import exceptions

def validate_spec(spec):
    """Validate the output of an :class:`APISpec` object against the
    OpenAPI specification.

    Note: Requires installing apispec with the ``[validation]`` extras.
    ::

        pip install 'apispec[validation]'

    :raise: apispec.exceptions.OpenAPIError if validation fails.
    """
    try:
        import prance
    except ImportError as error:  # re-raise with a more verbose message
        exc_class = type(error)
        raise exc_class(
            'validate_spec requires prance to be installed. '
            'You can install all validation requirements using:\n'
            "    pip install 'apispec[validation]'",
        )
    parser_kwargs = {}
    if spec.openapi_version.version[0] == 3:
        parser_kwargs['backend'] = 'openapi-spec-validator'
    try:
        prance.BaseParser(spec_string=json.dumps(spec.to_dict()), **parser_kwargs)
    except prance.ValidationError as err:
        raise exceptions.OpenAPIError(*err.args)
    else:
        return True

def validate_swagger(spec):
    """
    .. deprecated:: 0.38.0
        Use `apispec.utils.validate_spec` instead.
    """
    warnings.warn(
        'apispec.utils.validate_swagger is deprecated. Use apispec.utils.validate_spec instead.',
        DeprecationWarning,
    )
    return validate_spec(spec)


class OpenAPIVersion(version.LooseVersion, object):
    """OpenAPI version

    :param str|OpenAPIVersion openapi_version: OpenAPI version

    Parses an OpenAPI version expressed as string. Provides shortcut to digits
    (major, minor, patch).

        Example: ::

            ver = OpenAPIVersion('3.0.1')
            assert ver.major == 3
            assert ver.minor == 0
            assert ver.patch == 1
            assert ver.vstring == '3.0.1'
            assert str(ver) == '3.0.1'
    """
    MIN_INCLUSIVE_VERSION = version.LooseVersion('2.0')
    MAX_EXCLUSIVE_VERSION = version.LooseVersion('4.0')

    def __init__(self, openapi_version):
        if isinstance(openapi_version, version.LooseVersion):
            openapi_version = openapi_version.vstring
        if not self.MIN_INCLUSIVE_VERSION <= openapi_version < self.MAX_EXCLUSIVE_VERSION:
            raise exceptions.APISpecError(
                'Not a valid OpenAPI version number: {}'.format(openapi_version),
            )
        super(OpenAPIVersion, self).__init__(openapi_version)

    @property
    def major(self):
        return self.version[0]

    @property
    def minor(self):
        return self.version[1]

    @property
    def patch(self):
        return self.version[2]
