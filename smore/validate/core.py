# -*- coding: utf-8 -*-

from marshmallow import ValidationError as MarshmallowValidationError
try:
    from webargs import ValidationError as WebargsValidationError
except ImportError:
    HAS_WEBARGS = False
else:
    HAS_WEBARGS = True

if HAS_WEBARGS:
    class ValidationError(WebargsValidationError, MarshmallowValidationError):
        """Raised when a validation fails. Inherits from both
        webargs' ``ValidationError`` (if webargs is installed) and marshmallow's
        ``ValidationError`` so that the same validation functions can be used in either library.
        """
        #TODO: handle both marshmallow `field` and webargs `status_code` kwargs
        pass
else:
    class ValidationError(MarshmallowValidationError):
        """Raised when a validation fails. Inherits from both
        webargs' ``ValidationError`` (if webargs is installed) and marshmallow's
        ``ValidationError`` so that the same validation functions can be used in either library.
        """
        pass

class BaseConverter(object):
    """Base converter validator that converts a third-party validators into
    marshmallow validators.
    """

    def __init__(self, *validators):
        self.validators = validators

    def make_validator(self, validator):
        raise NotImplementedError('Converter must implement make_validator')

    def __call__(self, val):
        errors = []
        for vendor_validator in self.validators:
            validator = self.make_validator(vendor_validator)
            try:
                validator(val)
            except ValidationError as err:
                errors.append(str(err))
        if errors:
            raise ValidationError(errors)
