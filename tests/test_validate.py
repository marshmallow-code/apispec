# -*- coding: utf-8 -*-
import pytest

from marshmallow import fields
from marshmallow.exceptions import UnmarshallingError
from webargs import Arg, ValidationError as WebargsValidationError

from smore.validate import ValidationError

class TestValidationError:

    def test_marshmallow_validation(self):
        def validator(val):
            raise ValidationError('oh no')

        f = fields.Field(validate=validator)
        with pytest.raises(UnmarshallingError):
            f.deserialize('')

    def test_webargs_validation(self):
        def validator(val):
            raise ValidationError('oh no')

        a = Arg(validate=validator)
        with pytest.raises(WebargsValidationError):
            a.validated('', '')

# WTForms

from smore.validate.wtforms import from_wtforms
from wtforms.validators import AnyOf, NoneOf, Length

class TestWTFormsValidation:

    def test_from_wtforms(self):
        field = fields.Field(
            validate=from_wtforms(AnyOf(['red', 'blue']))
        )

        assert field.deserialize('red') == 'red'
        with pytest.raises(UnmarshallingError) as excinfo:
            field.deserialize('green')
        assert 'Invalid value' in str(excinfo)

    def test_from_wtforms_multi():
        field = fields.Field(
            validate=from_wtforms(
                Length(min=4),
                NoneOf(['nil', 'null', 'NULL'])
            )
        )
        assert field.deserialize('thisisfine') == 'thisisfine'
        with pytest.raises(UnmarshallingError) as excinfo:
            field.deserialize('bad')
        assert 'Field must be at least 4 characters long' in str(excinfo)
        with pytest.raises(UnmarshallingError) as excinfo:
            field.deserialize('null')
        assert "Invalid value, can't be any of: nil, null, NULL." in str(excinfo)

        with pytest.raises(UnmarshallingError) as excinfo:
            field.deserialize('nil')
        # both errors are returned
        assert "Invalid value, can't be any of: nil, null, NULL." in str(excinfo)
        assert 'Field must be at least 4 characters long' in str(excinfo)

# Colander

from smore.validate.colander import from_colander
from colander import ContainsOnly

class TestColanderValidation:
    def test_from_colander(self):
        field = fields.Field(
            validate=from_colander(ContainsOnly([1]))
        )
        assert field.deserialize([1]) == [1]
        with pytest.raises(UnmarshallingError) as excinfo:
            field.deserialize([2])
        assert 'One or more of the choices you made was not acceptable' in str(excinfo)

