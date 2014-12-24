# -*- coding: utf-8 -*-
from wtforms.validators import ValidationError as WTFValidationError

from .core import BaseConverter, ValidationError

# from: https://github.com/wtforms/wtforms/blob/master/tests/common.py
# TODO: il8n
class DummyTranslations(object):
    def gettext(self, string):
        return string

    def ngettext(self, singular, plural, n):
        if n == 1:
            return singular

        return plural

class DummyField(object):
    _translations = DummyTranslations()

    def __init__(self, data, errors=(), raw_data=None):
        self.data = data
        self.errors = list(errors)
        self.raw_data = raw_data

    def gettext(self, string):
        return self._translations.gettext(string)

    def ngettext(self, singular, plural, n):
        return self._translations.ngettext(singular, plural, n)

dummy_form = dict()


class from_wtforms(BaseConverter):
    """Convert a WTForms validator from `wtforms.validators` to a marshmallow validator.

    Example::

        from wtforms.validators import Length

        password = fields.Str(
            validate=from_wtforms(Length(min=8, max=100))
        )

    :param validators: WTForms validators as positional arguments.
    """

    def make_validator(self, wtf_validator):
        def marshmallow_validator(value):
            field = DummyField(value)
            try:
                wtf_validator(dummy_form, field)
            except WTFValidationError as err:
                raise ValidationError(str(err))
        return marshmallow_validator

