# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from .core import ValidationError, BaseConverter

from colander import Invalid

class from_colander(BaseConverter):
    """Convert a colander validator to a marshmallow validator.

    Example::

        from marshmallow import fields
        from smore.validate.colander import from_colander
        from colander import Length

        password = fields.Str(
            validate=from_colander([Length(min=8, max=100)])
        )

    :param list validators: Colander validators.
    """

    def make_validator(self, colander_validator):
        def marshmallow_validator(value):
            try:
                colander_validator(None, value)
            except Invalid as err:
                raise ValidationError(err.msg.interpolate())
        return marshmallow_validator
