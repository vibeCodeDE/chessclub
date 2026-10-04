# ADR-015: Brute-Force-Schutz (django-axes) und Dev-Profiling (django-debug-toolbar)

## Status
Accepted

## Date
2026-10-05

## Context
Die Vereinssoftware wird auf einem öffentlich erreichbaren Server selbst gehostet (PRD §2, N1.1) und verwaltet vertrauliche Mitglieder- und Finanzdaten. Der Anmelde-Endpunkt (`/anmelden/`) sowie der Django-Admin (`/admin/`) sind potenziellen automatisierten Wörterbuch- und Brute-Force-Angriffen ausgesetzt. Bisher gab es nach der Passworteingabe zwar den Zwei-Faktor-Schritt für Vorstände (T26), jedoch keine automatische Sperre bei wiederholten Fehleingaben des Primärpassworts.

Gleichzeitig verlangen die Architekturregeln (`AGENTS.md`) strikt: *„keine N+1-Abfragen, assertNumQueries im Test“* und Performance-Budgets gemäß PRD N2.2 (Seitenaufbau < 1 s, Suche < 500 ms). Bei komplexeren ORM-Abfragen (Turniertabellen, Beitragsübersichten, Kassenbuch) ist eine unmittelbare visuelle Einsicht in SQL-Queries und Ladezeiten während der Entwicklung unerlässlich.

## Decision
1. **django-axes für Brute-Force-Schutz:**
   - Schutz der Anmelderouten (`/anmelden/` und `/admin/login/`) gegen Passwort-Erraten.
   - Konfiguration: Nach 5 Fehlversuchen (`AXES_FAILURE_LIMIT = 5`) erfolgt eine Sperre für 1 Stunde (`AXES_COOLOFF_TIME = 1`).
   - Bei erfolgreichem Login wird der Zähler automatisch zurückgesetzt (`AXES_RESET_ON_SUCCESS = True`).
   - Bei Überschreitung des Limits wird eine barrierefreie, deutschsprachige Sperrseite (`core/templates/core/lockout.html`) mit HTTP 429 gerendert.
   - Volle DSGVO-Konformität: Keine externen Dienste (wie Google reCAPTCHA oder Cloudflare), alle Logs und Zähler verbleiben lokal in der PostgreSQL-Datenbank.
   - In der allgemeinen Testsuite ist Axes standardmäßig deaktiviert (`AXES_ENABLED = False` in `config/settings_test.py`), um Beeinflussung anderer Tests zu vermeiden; dedizierte Härtungstests aktivieren Axes gezielt per `@override_settings(AXES_ENABLED=True)`.

2. **django-debug-toolbar für Entwicklungs-Profiling:**
   - Ermöglicht Entwicklern im Browser die Echtzeit-Analyse von SQL-Abfragen, Template-Renderzeiten, Signalen und Cache-Zugriffen.
   - Nur aktiv, wenn `DEBUG=True` gesetzt ist und das Paket installiert ist.
   - In Produktion (`DEBUG=False`, `config.production`) ist die Toolbar vollständig deaktiviert und wird gar nicht in die URLs eingebunden.
   - Asynchrone AJAX-Fragmente (gemäß ADR-011) werden über `SHOW_TOOLBAR_CALLBACK` ignoriert, um Fragment-Antworten sauber zu halten.

3. **django-extensions für Entwickler-Werkzeuge & CI:**
   - Bereitstellung von `shell_plus` (automatisches Vorab-Importieren aller Models und Services), `show_urls` (vollständige Routen-Übersicht aller 8 Apps) und `validate_templates` (Syntaxprüfung aller Templates ohne HTTP-Lauf).
   - Nur aktiv bei `DEBUG=True`; in Produktion (`DEBUG=False`) wird die App nicht geladen.

## Consequences
- `django-axes`, `django-debug-toolbar` und `django-extensions` sind in `requirements.txt` erfasst.
- In `config/settings.py` sind `axes` in `INSTALLED_APPS`, `MIDDLEWARE` und `AUTHENTICATION_BACKENDS` konfiguriert; `debug_toolbar` und `django_extensions` werden bedingt bei `DEBUG=True` registriert.
- `core/auth_views.py` übergibt bei der 2FA-Vervollständigung das authentifizierende Backend explizit an `login()`.
- Die Tests in `core/tests/test_axes_and_toolbar.py` sichern das Verhalten aller drei Pakete inklusive Negativtests für die Produktionskonfiguration ab.
