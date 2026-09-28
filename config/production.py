"""Produktions-Settings – schärfer als der Dev-Fallback in ``settings.py``.

Von der Runtime aktivieren, z.B.::

    DJANGO_SETTINGS_MODULE=config.production gunicorn config.wsgi:application

Pflicht-Env-Variablen: ``DJANGO_SECRET_KEY`` und ``DJANGO_EMAIL_BACKEND``
(Passwort-Reset-Mails müssen echte Zustellung haben, kein Console-Backend).
"""
import os

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F401,F403

_secret_key = os.environ.get("DJANGO_SECRET_KEY", "")
if not _secret_key or _secret_key == "dev-insecure-key":
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY muss in der Produktion gesetzt sein "
        "(der Dev-Fallback-Schlüssel ist nicht erlaubt)."
    )
SECRET_KEY = _secret_key

_email_backend = os.environ.get("DJANGO_EMAIL_BACKEND", "")
if not _email_backend or _email_backend.startswith(
    "django.core.mail.backends.console"
):
    raise ImproperlyConfigured(
        "DJANGO_EMAIL_BACKEND muss in der Produktion auf ein Backend mit "
        "echter Zustellung zeigen (z.B. smtp)."
    )
EMAIL_BACKEND = _email_backend

DEBUG = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
