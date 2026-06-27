import pytest
from django.core.exceptions import ValidationError
from apps.users.validators import StrongPasswordValidator


def test_rejects_weak_password():
    with pytest.raises(ValidationError):
        StrongPasswordValidator().validate("alllowercase")


def test_accepts_strong_password():
    StrongPasswordValidator().validate("Str0ng!Pass")  # no raise
