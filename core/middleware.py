"""Sicherheits-Header für den Vereinsbetrieb (PRD N1.6)."""

from django.conf import settings


class SicherheitsHeaderMiddleware:
    """Setzt Header, die ohne externen CDN/Tracker auskommen.

    Bewusst ohne strenge ``script-src``-Allowlist: Die App lädt ausschließlich
    eigene Dateien; ``default-src 'self'`` verbietet Fremdquellen komplett.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        antwort = self.get_response(request)
        kopf = antwort.headers

        kopf.setdefault("X-Content-Type-Options", "nosniff")
        kopf.setdefault("X-Frame-Options", "DENY")
        kopf.setdefault("Referrer-Policy", "same-origin")
        kopf.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        kopf.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if not settings.DEBUG:
            kopf.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                "script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
            )
        return antwort
