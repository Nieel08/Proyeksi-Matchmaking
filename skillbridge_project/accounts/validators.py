import re
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


_GITHUB_USERNAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_url_validator = URLValidator(schemes=["https"])


def validate_github_profile_url(value):
    if not value:
        return
    try:
        _url_validator(value)
        parts = urlsplit(value)
        port = parts.port
    except (ValidationError, ValueError):
        raise ValidationError("Masukkan URL profil GitHub HTTPS yang valid.")

    segments = parts.path.strip("/").split("/")
    if (
        parts.scheme != "https"
        or parts.hostname != "github.com"
        or parts.username
        or parts.password
        or port
        or parts.query
        or parts.fragment
        or len(segments) != 1
        or not _GITHUB_USERNAME.fullmatch(segments[0])
    ):
        raise ValidationError("URL harus berupa https://github.com/<username>.")
