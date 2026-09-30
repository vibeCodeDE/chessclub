import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "members",
    "dues",
    "teams",
    "tournaments",
    "comms",
    "cashbook",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.SicherheitsHeaderMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.nav",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Produktion nutzt PostgreSQL (siehe docker-compose.yml). Ohne POSTGRES_HOST
# fällt die App auf SQLite zurück – so lässt sie sich ohne Datenbankserver
# starten (Entwicklung, Tests, Vorführung).
if os.environ.get("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "schachverein"),
            "USER": os.environ.get("POSTGRES_USER", "schachverein"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "schachverein"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("SQLITE_PATH", BASE_DIR / "db.sqlite3"),
            "OPTIONS": {"timeout": 20},
        }
    }

# PRD N1.6: Passwörter mit Argon2 (Fallback auf Djangos Standard, falls das
# Paket in einer Umgebung fehlt – dann bleibt der Betrieb lauffähig).
try:  # pragma: no cover - Umgebungsabhängig
    import argon2  # noqa: F401

    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.Argon2PasswordHasher",
        "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    ]
except ImportError:  # pragma: no cover
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/anmelden/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# E-Mail komplett per Env konfigurierbar (Variablennamen wie in
# .env.prod.example). Ohne gesetzte Werte greift das Console-Backend für die
# Entwicklung; config/production.py erzwingt dort ein Backend mit echter
# Zustellung.
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))

# Zwei-Faktor für die Vorstandschaft (PRD N1.6). In der Entwicklung abschaltbar
# (TWOFA_PFLICHT=0), im Produktivbetrieb verbindlich.
TWOFA_PFLICHT = os.environ.get("TWOFA_PFLICHT", "1") == "1"

# DSGVO: Aufbewahrungsfrist nach Austritt, danach werden Kontaktdaten anonymisiert.
DSGVO_ANONYMISIERUNGS_FRIST_TAGE = int(os.environ.get("DSGVO_FRIST_TAGE", "730"))

# ADR-010: Die IBAN wird verschluesselt gespeichert. Der Schluessel kommt aus
# der Umgebung und wird weder in die Datenbank noch ins Repo geschrieben.
# Ohne Schluessel laeuft die App, aber jede IBAN-Zugriffsart bricht mit
# ImproperlyConfigured ab – config/production.py verlangt den Schluessel.
IBAN_FERNET_KEY = os.environ.get("IBAN_FERNET_KEY", "")

# Härtung im Produktivbetrieb (hinter TLS-Reverse-Proxy, PRD N1.6).
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "0") == "1"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "0") == "1"
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
    SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0
    SECURE_CONTENT_TYPE_NOSNIFF = True

# Vertrauenswürdige Origins für Formular-POSTs (z. B. Reverse-Proxy-Domain).
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# Vereinsprofil – zentral, damit Templates und Mahnbriefe denselben Kopf nutzen.
CLUB_NAME = os.environ.get("CLUB_NAME", "Schachclub Königsspringer Musterstadt e.V.")
CLUB_SHORT = os.environ.get("CLUB_SHORT", "SC Königsspringer")
CLUB_CONTACT = os.environ.get("CLUB_CONTACT", "vorstand@koenigsspringer-musterstadt.de")

# Profil der öffentlichen Vereinsseite (ADR-012). Alle Werte sind optional und
# kommen aus der Umgebung: fehlt ein Wert, blendet das Template die Zeile aus,
# statt einen erfundenen Inhalt zu zeigen.
CLUB_FOUNDED = os.environ.get("CLUB_FOUNDED", "")            # z. B. "1924"
CLUB_LOCATION = os.environ.get("CLUB_LOCATION", "")          # z. B. "Musterstadt"
CLUB_ROOM = os.environ.get("CLUB_ROOM", "")                  # Spielort / Anschrift
CLUB_NIGHT_HOURS = os.environ.get("CLUB_NIGHT_HOURS", "Donnerstags ab 19:00 Uhr")
CLUB_YOUTH_HOURS = os.environ.get("CLUB_YOUTH_HOURS", "")    # z. B. "Donnerstags 17:30 – 19:00 Uhr"
CLUB_DESCRIPTION = os.environ.get("CLUB_DESCRIPTION", "")    # Kurztext für den Footer

# Produkt-Landingpage (/produkt/): Name und Kontakt für den Verkauf als Dienstleistung.
PRODUCT_NAME = os.environ.get("PRODUCT_NAME", "Schachclub-Manager")
PRODUCT_CONTACT = os.environ.get("PRODUCT_CONTACT", "hallo@schachclub-manager.example")

# Absender für System- und Gruppen-Mails (PRD M5.2) sowie Fehlerbenachrichtigung.
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", CLUB_CONTACT)
SERVER_EMAIL = DEFAULT_FROM_EMAIL
ADMINS = [
    (name.strip(), adresse.strip())
    for name, adresse in (
        eintrag.split(":", 1) if ":" in eintrag else (eintrag, eintrag)
        for eintrag in os.environ.get("DJANGO_ADMINS", f"Vorstand:{CLUB_CONTACT}").split(",")
        if eintrag.strip()
    )
]

# Fehlerbenachrichtigung an den Vorstand (PRD N2.5) – nur wenn DEBUG aus ist.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "mail_admins": {"class": "django.utils.log.AdminEmailHandler", "level": "ERROR"},
    },
    "loggers": {
        "django.request": {
            "handlers": ["console", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
