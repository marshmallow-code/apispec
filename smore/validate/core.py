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
        def __init__(self, message, *args, **kwargs):
            status_code = kwargs.pop('status_code', 400)
            WebargsValidationError.__init__(self, message, status_code=status_code)
            MarshmallowValidationError.__init__(self, message, *args, **kwargs)
else:
    class ValidationError(MarshmallowValidationError):
        """Raised when a validation fails. Inherits from both
        webargs' ``ValidationError`` (if webargs is installed) and marshmallow's
        ``ValidationError`` so that the same validation functions can be used in either library.
        """

        def __init__(self, message, field=None, **_):
            # make the signature compatible with the above impl for when not HAS_WEBARGS
            super(ValidationError, self).__init__(message, field)


class BaseConverter(object):
    """Base converter validator that converts a third-party validators into
    marshmallow validators.
    """

    def __init__(self, validators):
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
                errors.extend(err.messages)
        if errors:
            raise ValidationError(errors)
