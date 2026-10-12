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
    "axes",
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
]
try:
    import whitenoise  # noqa: F401

    MIDDLEWARE.append("whitenoise.middleware.WhiteNoiseMiddleware")
except ImportError:
    pass
MIDDLEWARE.extend([
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.SicherheitsHeaderMiddleware",
    "core.middleware.ModulAktivMiddleware",
    "axes.middleware.AxesMiddleware",
])


AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Brute-Force-Schutz für Anmeldungen (PRD N1.6, ADR-015)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # 1 Stunde Sperre nach 5 Fehlversuchen
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "core/lockout.html"
# Proxy-Konfiguration für Reverse Proxy (Caddy / Docker, PRD N1.6)
AXES_PROXY_COUNT = int(os.environ.get("AXES_PROXY_COUNT", "1"))
AXES_META_PRE_NAME = os.environ.get("AXES_META_PRE_NAME", "HTTP_X_FORWARDED_FOR")

# Entwicklungs-Profiling (django-debug-toolbar, PRD N2.2, ADR-015):
# Nur aktiv, wenn DEBUG=True gesetzt ist und das Paket installiert ist.
if DEBUG:
    try:
        import debug_toolbar  # noqa: F401

        INSTALLED_APPS.append("debug_toolbar")
        MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    except ImportError:
        pass

    try:
        import django_extensions  # noqa: F401

        INSTALLED_APPS.append("django_extensions")
    except ImportError:
        pass

INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]


def show_debug_toolbar(request):
    """Toolbar nur bei DEBUG anzeigen und nicht für asynchrone AJAX-Fragmente."""
    from django.conf import settings as _s

    return bool(_s.DEBUG) and request.headers.get("x-requested-with") != "XMLHttpRequest"


DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": "config.settings.show_debug_toolbar",
}

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

# Produktion nutzt PostgreSQL (siehe docker-compose.yml bzw. Scalingo DATABASE_URL).
# Unterstützt SCALINGO_POSTGRESQL_URL / DATABASE_URL (PaaS) sowie POSTGRES_HOST (Docker).
# Ohne Datenbankserver fällt die App auf SQLite zurück (Entwicklung, Tests, Vorführung).
_db_url = os.environ.get("DATABASE_URL") or os.environ.get("SCALINGO_POSTGRESQL_URL")
if _db_url:
    import urllib.parse

    _parsed_url = urllib.parse.urlparse(_db_url)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _parsed_url.path.lstrip("/"),
            "USER": _parsed_url.username or "",
            "PASSWORD": _parsed_url.password or "",
            "HOST": _parsed_url.hostname or "localhost",
            "PORT": str(_parsed_url.port or 5432),
        }
    }
    _query = urllib.parse.parse_qs(_parsed_url.query)
    if "sslmode" in _query:
        DATABASES["default"]["OPTIONS"] = {"sslmode": _query["sslmode"][0]}
elif os.environ.get("POSTGRES_HOST"):
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

try:
    import whitenoise  # noqa: F401

    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
except ImportError:
    pass

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

# SEPA-Lastschriften (pain.008 / ADR-017 / PRD S2.7)
# Gläubiger-Identifikationsnummer (z. B. DE98ZZZ09999999999)
SEPA_CREDITOR_ID = os.environ.get("SEPA_CREDITOR_ID", "DE98ZZZ09999999999")
# Vereins-IBAN für den Lastschrifteinzug
SEPA_CREDITOR_IBAN = os.environ.get("SEPA_CREDITOR_IBAN", "DE89370400440532013000")
# Optional: Vereins-BIC
SEPA_CREDITOR_BIC = os.environ.get("SEPA_CREDITOR_BIC", "")
# Name des Gläubigers (Standard: CLUB_NAME)
SEPA_CREDITOR_NAME = os.environ.get("SEPA_CREDITOR_NAME", "")

# DSB-Schnittstelle (ADR-016 / K3.6): Wertungsportal-API & DWZ-Sync
DSB_VKZ = os.environ.get("DSB_VKZ", "")                       # Vereinskennziffer, z. B. "C0101"
DSB_API_TOKEN = os.environ.get("DSB_API_TOKEN", "")           # Zugangsschlüssel
DSB_API_BASE_URL = os.environ.get(
    "DSB_API_BASE_URL", "https://www.schachbund.de/wertungsportal-api/vereinsliste"
)
DSB_CACHE_TIMEOUT = int(os.environ.get("DSB_CACHE_TIMEOUT", "86400"))  # 24 h serverseitiges Caching

# Produkt-Landingpage (/produkt/): Name und Kontakt für den Verkauf als Dienstleistung.
PRODUCT_NAME = os.environ.get("PRODUCT_NAME", "Schachverwaltung.de")
PRODUCT_CONTACT = os.environ.get("PRODUCT_CONTACT", "kontakt@schachverwaltung.de")

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
