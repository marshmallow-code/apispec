
from .core import ValidationError, BaseConverter

from colander import Invalid

class from_colander(BaseConverter):
    """Convert a colander validator from colander to a marshmallow validator.

    :param validators: Colander validators as positional arguments.
    """

    def make_validator(self, colander_validator):
        def marshmallow_validator(value):
            try:
                colander_validator(None, value)
            except Invalid as err:
                raise ValidationError(err.msg.interpolate())
        return marshmallow_validator
