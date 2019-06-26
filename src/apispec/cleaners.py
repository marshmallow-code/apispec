import warnings
from collections import OrderedDict

from .compat import iteritems

from .exceptions import InvalidParameterError, DuplicateParameterError, APISpecError
from .utils import COMPONENT_SUBSECTIONS


class Cleaner:
    VALID_METHODS_OPENAPI_V2 = [
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
    ]
    VALID_METHODS_OPENAPI_V3 = VALID_METHODS_OPENAPI_V2 + ["trace"]
    VALID_METHODS = {2: VALID_METHODS_OPENAPI_V2, 3: VALID_METHODS_OPENAPI_V3}

    def __init__(self, openapi_major_version):
        """
        :param int openapi_major_version: The major version of the OpenAPI standard
        """
        self.openapi_major_version = openapi_major_version

    def get_ref(self, obj_type, obj):
        """Return object or reference

        If obj is a dict, it is assumed to be a complete description and it is returned as is.
        Otherwise, it is assumed to be a reference name as string and the corresponding $ref
        string is returned.

        :param str obj_type: "parameter" or "response"
        :param dict|str obj: parameter or response in dict form or as ref_id string
        """
        if isinstance(obj, dict):
            return obj
        return self.build_reference(obj_type, obj)

    def build_reference(self, component_type, component_name):
        """Return path to reference

        :param str component_type: Component type (schema, parameter, response, security_scheme)
        :param str component_name: Name of component to reference
        """
        return {
            "$ref": "#/{}{}/{}".format(
                "components/" if self.openapi_major_version >= 3 else "",
                COMPONENT_SUBSECTIONS[self.openapi_major_version][component_type],
                component_name,
            )
        }

    def normalize_parameters(self, parameters):
        """Ensure that all parameters with "in" equal to "path" are also required
        as required by the OpenAPI specification

        See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#parameterObject.

        :param list parameters: List of parameters mapping
        """
        for parameter in (p for p in parameters if isinstance(p, dict)):
            # Add "required" attribute to path parameters
            if parameter["in"] == "path":
                parameter["required"] = True
        return parameters

    def normalize_operations(self, operations):
        """
        :param dict operations: Dict mapping status codes to operations
        """
        for operation in operations.values():
            if "parameters" in operation:
                operation["parameters"] = self.refer_parameters(operation["parameters"])
            if "responses" in operation:
                responses = OrderedDict()
                for code, response in iteritems(operation["responses"]):
                    try:
                        code = int(code)  # handles IntEnums like http.HTTPStatus
                    except (TypeError, ValueError):
                        if self.openapi_major_version < 3:
                            warnings.warn("Non-integer code not allowed in OpenAPI < 3")

                    responses[str(code)] = self.get_ref("response", response)
                operation["responses"] = responses
        return operations

    def get_parameters_references(self, parameters):
        return [self.get_ref("parameter", p) for p in parameters]

    def refer_parameters(self, parameters):
        parameters = self.clean_parameters(parameters)
        return self.get_parameters_references(parameters)

    def clean_parameters(self, parameters):
        """
        :param list parameters: List of parameters mapping
        """
        self.validate_parameters(parameters)
        parameters = self.normalize_parameters(parameters)
        return parameters

    def clean_operations(self, operations):
        """Ensure that all parameters with "in" equal to "path" are also required
        as required by the OpenAPI specification, as well as normalizing any
        references to global parameters. Also checks for invalid HTTP methods.

        See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#parameterObject.

        :param dict operations: Dict mapping status codes to operations
        """
        self.validate_operations(operations)
        operations = self.normalize_operations(operations)
        return operations

    def validate_operations(self, operations):
        """Verify that none of the operations contains keys other than custom

        :param dict operations: Dict mapping status codes to operations
        """
        valid_methods = set(self.VALID_METHODS[self.openapi_major_version])
        invalid = [
            key for key in set(operations) - valid_methods if not key.startswith("x-")
        ]
        if invalid:
            raise APISpecError(
                "One or more HTTP methods are invalid: {}".format(", ".join(invalid))
            )

    @staticmethod
    def validate_parameters(parameters):
        """
        :param list parameters: List of parameters mapping
        """
        seen = set()
        for parameter in (p for p in parameters if isinstance(p, dict)):

            # check missing name / location
            missing_attrs = [attr for attr in ("name", "in") if attr not in parameter]
            if missing_attrs:
                raise InvalidParameterError(
                    "Missing keys {} for parameter".format(missing_attrs)
                )

            # OpenAPI Spec 3 and 2 don't allow for duplicated parameters
            # A unique parameter is defined by a combination of a name and location
            unique_key = parameter["name"], parameter["in"]
            if unique_key in seen:
                raise DuplicateParameterError(
                    "Duplicate parameter with name {} and location {}".format(
                        parameter["name"], parameter["in"]
                    )
                )
            seen.add(unique_key)
