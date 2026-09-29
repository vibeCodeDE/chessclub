import os
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Vercel setzt VERCEL=1 (Build und Laufzeit). Dort läuft Django serverlos:
# TLS endet am Rand, das Dateisystem ist schreibgeschützt, die Domains liegen
# unter *.vercel.app (siehe docs/deployment.md, Abschnitt „Vercel“).
ON_VERCEL = bool(os.environ.get("VERCEL"))


def _env_liste(name, default=""):
    """Kommagetrennte Umgebungsvariable als Liste (leere Einträge entfallen)."""
    return [wert.strip() for wert in os.environ.get(name, default).split(",") if wert.strip()]


def _vercel_hosts():
    """Hostnamen, unter denen Vercel dieses Projekt ausliefert.

    Vercel leitet nur Domains des eigenen Projekts an die Funktion weiter, ein
    fremder ``Host``-Header erreicht Django dort also nicht. ``.vercel.app``
    deckt Produktions-Alias, Branch-Aliase und Deployment-URLs ab;
    ``VERCEL_PROJECT_PRODUCTION_URL`` ergänzt eine eigene Produktionsdomain.
    """
    hosts = [".vercel.app"]
    for name in ("VERCEL_PROJECT_PRODUCTION_URL", "VERCEL_BRANCH_URL", "VERCEL_URL"):
        wert = os.environ.get(name, "").strip()
        host = wert.removeprefix("https://").removeprefix("http://").strip("/")
        if host:
            hosts.append(host)
    return hosts


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = _env_liste("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
if ON_VERCEL:
    # Ohne diese Einträge antwortet Django auf jede Vercel-Domain mit
    # „Bad Request (400)“ (DisallowedHost). Eigene Domains: DJANGO_ALLOWED_HOSTS.
    ALLOWED_HOSTS += [host for host in _vercel_hosts() if host not in ALLOWED_HOSTS]

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

# libpq-Parameter, die aus einer Datenbank-URL übernommen werden. Manche Anbieter
# hängen eigene Parameter an (z. B. ``supa=``), an denen libpq sonst scheitert.
_POSTGRES_URL_PARAMETER = (
    "sslmode",
    "sslrootcert",
    "channel_binding",
    "connect_timeout",
    "application_name",
    "options",
)


def _datenbank_aus_url(url):
    """``DATABASES``-Eintrag aus einer Postgres-URL (Vercel/Neon: ``DATABASE_URL``)."""
    teile = urlsplit(url)
    if teile.scheme not in ("postgres", "postgresql"):
        raise ImproperlyConfigured(
            "DATABASE_URL muss eine PostgreSQL-URL sein (postgres://… oder postgresql://…)."
        )
    parameter = {
        schluessel: wert
        for schluessel, wert in parse_qsl(teile.query)
        if schluessel in _POSTGRES_URL_PARAMETER
    }
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(teile.path.lstrip("/")),
        "USER": unquote(teile.username or ""),
        "PASSWORD": unquote(teile.password or ""),
        "HOST": teile.hostname or "",
        "PORT": str(teile.port) if teile.port else "",
        # Serverlos steht meist ein Connection-Pooler im Transaction-Modus
        # (PgBouncer) vor der Datenbank: keine Server-Side-Cursors und kein
        # automatisches Prepared-Statement-Caching von psycopg 3.
        "DISABLE_SERVER_SIDE_CURSORS": True,
        "OPTIONS": {**parameter, "prepare_threshold": None},
    }


# Produktion nutzt PostgreSQL. Vercel-Datenbank-Integrationen (Neon, Supabase)
# liefern eine URL in DATABASE_URL bzw. POSTGRES_URL; docker-compose.yml nutzt
# die Einzelwerte POSTGRES_HOST/_DB/_USER/_PASSWORD. Ohne beides fällt die App
# auf SQLite zurück – so lässt sie sich ohne Datenbankserver starten
# (Entwicklung, Tests, Vorführung). Auf Vercel ist SQLite keine Option: das
# Dateisystem ist dort schreibgeschützt.
_datenbank_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
if _datenbank_url:
    DATABASES = {"default": _datenbank_aus_url(_datenbank_url)}
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

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/anmelden/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)

# Zwei-Faktor für die Vorstandschaft (PRD N1.6). In der Entwicklung abschaltbar
# (TWOFA_PFLICHT=0), im Produktivbetrieb verbindlich.
TWOFA_PFLICHT = os.environ.get("TWOFA_PFLICHT", "1") == "1"

# DSGVO: Aufbewahrungsfrist nach Austritt, danach werden Kontaktdaten anonymisiert.
DSGVO_ANONYMISIERUNGS_FRIST_TAGE = int(os.environ.get("DSGVO_FRIST_TAGE", "730"))

# Härtung im Produktivbetrieb (hinter TLS-Reverse-Proxy, PRD N1.6).
if not DEBUG:
    # Vercel liefert ausschließlich per HTTPS aus (HTTP wird am Rand umgeleitet),
    # daher sind sichere Cookies dort der Standard; der Redirect bleibt Sache von Vercel.
    _https_standard = "1" if ON_VERCEL else "0"
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "0") == "1"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", _https_standard) == "1"
    CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", _https_standard) == "1"
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
    SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0
    SECURE_CONTENT_TYPE_NOSNIFF = True

if ON_VERCEL:
    # Vercels Edge setzt X-Forwarded-Proto selbst und überschreibt Werte von
    # Clients. So erkennt Django HTTPS (CSRF-Origin-Prüfung, sichere Cookies)
    # unabhängig davon, wie die Runtime die WSGI-Umgebung aufbaut.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Vertrauenswürdige Origins für Formular-POSTs (z. B. Reverse-Proxy-Domain).
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# Vereinsprofil – zentral, damit Templates und Mahnbriefe denselben Kopf nutzen.
CLUB_NAME = os.environ.get("CLUB_NAME", "Schachclub Königsspringer Musterstadt e.V.")
CLUB_SHORT = os.environ.get("CLUB_SHORT", "SC Königsspringer")
CLUB_CONTACT = os.environ.get("CLUB_CONTACT", "vorstand@koenigsspringer-musterstadt.de")

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
