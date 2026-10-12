"""Produktions-Settings – schärfer als der Dev-Fallback in ``settings.py``.

Wird von ``docker-compose.prod.yml`` über ``DJANGO_SETTINGS_MODULE`` aktiviert;
für einen manuellen Start genügt::

    DJANGO_SETTINGS_MODULE=config.production gunicorn config.wsgi:application

Pflicht-Env-Variablen: ``DJANGO_SECRET_KEY``, ``EMAIL_BACKEND`` (Passwort-Reset-Mails
müssen echte Zustellung haben, kein Console-Backend) und ``IBAN_FERNET_KEY``
(Verschlüsselung der IBAN, ADR-010).
"""
import os

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F401,F403

_secret_key = os.environ.get("DJANGO_SECRET_KEY") or os.environ.get("SECRET_KEY", "")
if not _secret_key or _secret_key == "dev-insecure-key":
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY muss in der Produktion gesetzt sein "
        "(der Dev-Fallback-Schlüssel ist nicht erlaubt)."
    )
SECRET_KEY = _secret_key


# Gleiche Variable wie in settings.py und .env.prod.example; der ältere Name
# DJANGO_EMAIL_BACKEND wird weiterhin gelesen, damit bestehende .env-Dateien
# nicht stillschweigend auf das Console-Backend zurückfallen.
_email_backend = os.environ.get("EMAIL_BACKEND") or os.environ.get(
    "DJANGO_EMAIL_BACKEND", ""
)
if not _email_backend or _email_backend.startswith(
    "django.core.mail.backends.console"
):
    raise ImproperlyConfigured(
        "EMAIL_BACKEND muss in der Produktion auf ein Backend mit "
        "echter Zustellung zeigen (z.B. smtp)."
    )
EMAIL_BACKEND = _email_backend

DEBUG = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Härtung wie in .env.prod.example dokumentiert: HTTPS erzwingen und HSTS
# setzen. Ohne das blieb die Seite auch über HTTP erreichbar und der Browser
# bekäme keine HSTS-Header.
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "1") == "1"
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "0") == "1"
)
if SECURE_HSTS_SECONDS:
    SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "0") == "1"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ADR-010: Ohne IBAN-Schlüssel startet der Produktivbetrieb nicht. Sonst ginge
# ein Mandat mit Klartext-IBAN verloren, sobald jemand den Schlüssel nachsetzt.
if not os.environ.get("IBAN_FERNET_KEY", "").strip():
    raise ImproperlyConfigured(
        "IBAN_FERNET_KEY muss in der Produktion gesetzt sein (Verschlüsselung "
        "der IBAN, ADR-010). Erzeugen mit: python -c \"from cryptography.fernet "
        "import Fernet; print(Fernet.generate_key().decode())\""
    )
