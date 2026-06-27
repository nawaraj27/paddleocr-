"""Extra password strength rule on top of Django's validators."""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class StrongPasswordValidator:
    """Require upper, lower, digit and symbol."""

    def validate(self, password, user=None):
        checks = [
            (r"[A-Z]", _("an uppercase letter")),
            (r"[a-z]", _("a lowercase letter")),
            (r"[0-9]", _("a digit")),
            (r"[^A-Za-z0-9]", _("a symbol")),
        ]
        missing = [msg for rx, msg in checks if not re.search(rx, password or "")]
        if missing:
            raise ValidationError(
                _("Password must contain %(items)s.") % {"items": ", ".join(missing)},
                code="password_not_strong")

    def get_help_text(self):
        return _("Use upper & lower case, a digit and a symbol.")
