"""Cross-cutting HTTP compatibility helpers."""

import re

from django.conf import settings
from django.utils.cache import patch_vary_headers

_VERSION_PARAMETER = re.compile(
    r"(?P<prefix>;\s*version\s*=\s*)(?P<quote>\"?)(?P<version>[\w.-]+)(?P=quote)",
    re.IGNORECASE,
)


class ApiVersionCompatibilityMiddleware:
    """Translate the supported legacy Accept version to the current contract."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        legacy_version = None
        accept = request.META.get("HTTP_ACCEPT", "")
        aliases = settings.API_VERSION_ALIASES

        def replace_version(match):
            nonlocal legacy_version
            version = match.group("version")
            current = aliases.get(version)
            if current is None:
                return match.group(0)
            legacy_version = version
            return f'{match.group("prefix")}{match.group("quote")}{current}{match.group("quote")}'

        if accept:
            request.META["HTTP_ACCEPT"] = _VERSION_PARAMETER.sub(
                replace_version, accept
            )

        response = self.get_response(request)
        if legacy_version is not None:
            response["Deprecation"] = "true"
            response["Warning"] = (
                f'299 AnkiHub-Brasil "API version {legacy_version} is deprecated"'
            )
            patch_vary_headers(response, ("Accept",))
        return response
