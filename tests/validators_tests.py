from django.test import TestCase
from adaptor.validators import RegexValidator

class TestValidator(TestCase):
    def test_regex_validator(self):
        validator = RegexValidator("status", "^Z[0,2]")
        self.assertTrue(validator().validate("Z0"))
        self.assertFalse(validator().validate("Z1"))
