# ADR-028: Rate-Limiting für öffentliche Endpunkte mit django-ratelimit

## Status

Accepted

## Date

2026-10-18

## Context

Die Schachvereins-Software schützt Authentifizierungs-Routen (`/anmelden/`, `/admin/`) erfolgreich mit `django-axes` vor Brute-Force-Angriffen auf Benutzerkonten ([ADR-015](ADR-015-brute-force-schutz-und-dev-profiling.md)).

Öffentlich zugängliche Formulare ohne Authentifizierungspflicht waren bisher jedoch ungedrosselt:
1. **Schnupper-Anfragen / Beitritts-Kontaktformular** (`/mitglied-werden/`, `members.views.join_info`): Kann missbraucht werden, um Vereins-Postfächer mit Spam-E-Mails zu überfluten.
2. **Öffentliche Turnieranmeldungen** (`/turniere/<pk>/`, `tournaments.views.public_detail`): Kann durch automatisierte Massen-Anmeldungen von Scheinteilnehmern gestört werden.
3. **Passwort-Reset-Anfragen** (`/passwort/aendern/`, `core.auth_views.password_reset`): Kann für E-Mail-Bombing missbraucht werden.
4. **Funktionärs-Einladungsannahme** (`/einladung/<token>/`, `core.auth_views.accept_invitation`): Schutz vor Token-Brute-Force.

Häufig eingesetzte Lösungen wie Google reCAPTCHA oder Cloudflare Turnstile verstoßen gegen die strikten DSGVO- und Architektur-Vorgaben des Projekts ([AGENTS.md](../../AGENTS.md), PRD N1.1):
- **Keine Drittanbieter-Dienste, Tracker oder externen CDNs** (DSGVO N1.1).
- Vollständige Unabhängigkeit von externen Cloud-APIs (DSGVO Art. 5, 25 und 44 ff.).

Gesucht war daher ein rein serverseitiges, privatsphärefreundliches Rate-Limiting für sensible öffentliche POST-Endpunkte.

## Decision

1. **Integration von `django-ratelimit` (>=4.1.0):**
   - Aufnahme von `django-ratelimit>=4.1.0` in `requirements.txt`.
   - Konfiguration in `config/settings.py`:
     - `RATELIMIT_ENABLE = True`
     - `RATELIMIT_USE_CACHE = "default"`
     - `RATELIMIT_VIEW = "core.views.ratelimited_view"`
     - `RATELIMIT_IP_META_KEY = os.environ.get("RATELIMIT_IP_META_KEY", "REMOTE_ADDR")`
   - Registrierung von `django_ratelimit.middleware.RatelimitMiddleware` in `MIDDLEWARE`.
   - In `config/settings_test.py` wird `RATELIMIT_ENABLE = False` als Standard gesetzt, analog zu `AXES_ENABLED = False`, damit wiederholte Test-POSTs in der allgemeinen Testsuite nicht gedrosselt werden.

2. **Dekoration öffentlicher POST-Endpunkte:**
   - `@ratelimit(key="ip", rate="5/m", method="POST", block=True)` schützt:
     - `members.views.join_info`
     - `tournaments.views.public_detail`
     - `core.auth_views.password_reset`
     - `core.auth_views.accept_invitation`
   - GET-Anfragen (Lesen von Turnierinformationen, Formularaufrufe) bleiben unbeeinflusst (`method="POST"`).

3. **Benutzerfreundliche Fehlerbehandlung (HTTP 429 Too Many Requests):**
   - Bei Überschreiten des Kontingents fängt `RatelimitMiddleware` die `Ratelimited`-Exception ab und ruft `core.views.ratelimited_view` auf.
   - Die View liefert HTTP-Status `429 Too Many Requests` mit gesetztem `Retry-After: 60`-Header.
   - Barrierefreie, responsive deutsche Fehleransicht in `core/templates/core/ratelimited.html` (im Design von `auth_base.html` / `site.css`) sowie `templates/429.html`.
   - AJAX- und JSON-Anfragen erhalten eine saubere JSON-Fehlermeldung.

## Consequences

- Effektiver Schutz vor Spam, Bots und E-Mail-Fluten auf allen ungeschützten öffentlichen Formularen.
- 100 % DSGVO-konform: Keine Einbindung von Google reCAPTCHA oder Drittanbieter-Skripten.
- Schnelle, speicherschonende Prüfung über das integrierte Cache-Backend ohne N+1-Datenbankabfragen.
- Unveränderte Testgeschwindigkeit: Reguläre Tests bleiben dank `RATELIMIT_ENABLE = False` in `settings_test.py` unbeeinträchtigt, während `core/tests/test_ratelimit.py` das Verhalten gezielt prüft.
