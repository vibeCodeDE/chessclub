"""Sicherheits-Header und Proxy-IP-Ermittlung für den Vereinsbetrieb (PRD N1.6, SEC-05)."""

import ipaddress


def _is_internal_proxy(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Prüft, ob eine IP-Adresse zu einem internen/privaten Proxy-Netzwerk gehört.

    Erkennt RFC 1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), Loopback (127.0.0.0/8, ::1)
    und Link-Local-Adressen, wie sie von Docker, Kubernetes und lokalen Proxies genutzt werden.
    Dokumentations- und Testnetze (RFC 5737 wie 203.0.113.0/24) gelten bewusst als externe Adressen.
    """
    if ip_obj.is_loopback or ip_obj.is_link_local:
        return True
    if ip_obj.version == 4:
        parts = [int(x) for x in str(ip_obj).split(".")[:2]]
        if parts[0] == 10:
            return True
        if parts[0] == 172 and 16 <= parts[1] <= 31:
            return True
        if parts[0] == 192 and parts[1] == 168:
            return True
        if parts[0] == 127:
            return True
    elif ip_obj.version == 6:
        if ip_obj.is_private:
            return True
    return False


def extract_client_ip(request) -> str:
    """Extrahiert die echte Client-IP aus einem Django HttpRequest oder META-Dict.

    Verhindert IP-Spoofing beim Rate-Limiting und AuditLog hinter Reverse Proxies (PRD N1.6, ADR-028 / SEC-05):
    1. Bevorzugt HTTP_X_REAL_IP, wenn vorhanden und syntaktisch valide (wird von Caddy / Nginx / Scalingo gesetzt).
    2. Wertet HTTP_X_FORWARDED_FOR sicher von rechts nach links aus: Interne Proxy-Hops
       (Docker-Netzwerke, Loopback, RFC 1918) werden übersprungen, sodass bei Proxy-Ketten
       (z. B. Scalingo/Cloudflare + Caddy) die echte Client-IP und nicht ein manipulierter
       Eintrag am Anfang des Headers gewählt wird.
    3. Fällt auf REMOTE_ADDR zurück.
    """
    if request is None:
        return "—"

    meta = getattr(request, "META", request) if not isinstance(request, dict) else request

    # 1. X-Real-IP (von Caddy / Scalingo strikt überschriebene Einzel-IP)
    real_ip = meta.get("HTTP_X_REAL_IP")
    if real_ip:
        try:
            return str(ipaddress.ip_address(real_ip.strip()))
        except ValueError:
            pass

    # 2. X-Forwarded-For von rechts nach links auswerten
    forwarded = meta.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        raw_ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        valid_ips = []
        for raw in raw_ips:
            try:
                valid_ips.append(ipaddress.ip_address(raw))
            except ValueError:
                continue
        if valid_ips:
            # Von rechts nach links suchen: überspringe interne/private Proxies
            for ip in reversed(valid_ips):
                if not _is_internal_proxy(ip):
                    return str(ip)
            # Falls alle IPs im Header intern sind (z. B. rein lokales Testnetzwerk), nimm die erste
            return str(valid_ips[0])

    # 3. Fallback auf REMOTE_ADDR
    remote_addr = meta.get("REMOTE_ADDR")
    if remote_addr:
        try:
            return str(ipaddress.ip_address(remote_addr.strip()))
        except ValueError:
            pass

    return "—"


def get_ratelimit_ip(request) -> str:
    """Liefert die verifizierte Client-IP für django-ratelimit (PRD N1.6, ADR-028, SEC-05).

    Verhindert Denial-of-Service-Risiken hinter Reverse Proxies (Caddy, Scalingo Router),
    indem nicht ungeprüft auf die interne Proxy-IP in REMOTE_ADDR (z. B. 172.18.x.x oder 127.0.0.1)
    zurückgegriffen wird, sondern verifizierte Proxy-Header ausgewertet werden.
    """
    ip = extract_client_ip(request)
    if not ip or ip == "—":
        return "127.0.0.1"
    return ip


class RemoteAddrMiddleware:
    """Konfiguriert Djangos request.META['REMOTE_ADDR'] bei Proxy-Terminierung korrekt (SEC-05).

    Verhindert IP-Spoofing und Abstürze bei kommagetrennten Headern hinter Reverse-Proxies.
    Muss ganz oben in MIDDLEWARE registriert werden, damit nachfolgende Middlewares
    (SecurityMiddleware, AxesMiddleware, RatelimitMiddleware) sowie Views und Signals
    eine bereinigte, verifizierte Client-IP in request.META['REMOTE_ADDR'] vorfinden.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        client_ip = extract_client_ip(request)
        if client_ip and client_ip != "—":
            request.META["REMOTE_ADDR"] = client_ip
        return self.get_response(request)



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
