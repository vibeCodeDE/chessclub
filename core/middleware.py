"""Sicherheits-Header für den Vereinsbetrieb (PRD N1.6)."""


class SicherheitsHeaderMiddleware:
    """Setzt ergänzende Sicherheits-Header (PRD N1.6).

    Content-Security-Policy (CSP) wird deklarativ über ``csp.middleware.CSPMiddleware``
    (django-csp) und ``CONTENT_SECURITY_POLICY`` in settings.py verwaltet.
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
        return antwort


class ModulAktivMiddleware:
    """Sperrt Routen inaktiver Satellitenmodule mit HTTP 404 (T30 / ADR-019)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        resolver_match = getattr(request, "resolver_match", None)
        if not resolver_match:
            return None

        app_name = resolver_match.app_name
        url_name = resolver_match.url_name

        from django.http import Http404

        from core.services import is_module_active

        if app_name == "teams" and not is_module_active("teams", request):
            raise Http404("Das Modul Spielbetrieb ist derzeit deaktiviert.")
        if app_name == "tournaments" and not is_module_active("tournaments", request):
            raise Http404("Das Modul Turniere ist derzeit deaktiviert.")
        if app_name == "cashbook" and not is_module_active("cashbook", request):
            raise Http404("Das Modul Kassenbuch ist derzeit deaktiviert.")
        if app_name == "comms" and not is_module_active("comms", request):
            raise Http404("Das Modul Kommunikation ist derzeit deaktiviert.")
        if app_name == "core" and url_name in ("news_archiv", "news_detail") and not is_module_active("comms", request):
            raise Http404("Das Modul Kommunikation ist derzeit deaktiviert.")
        if app_name == "core" and url_name == "verein" and not is_module_active("homepage", request):
            raise Http404("Das Modul Vereinshomepage ist derzeit deaktiviert.")

        return None

