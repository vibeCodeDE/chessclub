"""Test-Settings: schnelle Passwort-Hashes, gleiche Datenbank wie Entwicklung."""

from .settings import *  # noqa: F401,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Fester Schluessel nur fuer die Testdatenbank. Die Tests, die das pruefen,
# ueberschreiben ihn mit `override_settings`.
IBAN_FERNET_KEY = "up3_XszoFQiTs6TmInARNOIqBlEeh7V_7e46vfQ_g-E="

# Axes standardmäßig in der allgemeinen Testsuite deaktivieren, damit fehlerhafte
# Logins in einzelnen Tests nicht andere Testfälle sperren. Dedizierte Härtungstests
# aktivieren AXES_ENABLED gezielt per @override_settings(AXES_ENABLED=True).
AXES_ENABLED = False

# 2FA-Pflicht standardmäßig im Testbetrieb deaktivieren, analog zu AXES_ENABLED.
# Dedizierte 2FA-Tests aktivieren TWOFA_PFLICHT gezielt per @override_settings.
TWOFA_PFLICHT = False

# Rate-Limiting standardmäßig in der allgemeinen Testsuite deaktivieren, damit
# wiederholte POST-Anfragen in Standard-Tests nicht gedrosselt werden.
# Dedizierte Tests aktivieren RATELIMIT_ENABLE gezielt per @override_settings(RATELIMIT_ENABLE=True).
RATELIMIT_ENABLE = False

