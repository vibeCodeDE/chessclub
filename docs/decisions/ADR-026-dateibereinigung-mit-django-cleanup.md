# ADR-026: Automatische Dateisystem-Bereinigung mit django-cleanup

## Status

Accepted

## Date

2026-10-17

## Context

Die Vereinsverwaltung wird auf einem eigenen Server bzw. einer containerisierten Umgebung mit begrenzten Speicherressourcen betrieben (PRD §2, [ADR-001](ADR-001-django-stack.md), [ADR-009](ADR-009-betrieb-caddy-restic-uptime-kuma.md)). 
In verschiedenen Fachbereichen (z. B. Dokumente, Belege, Turnierausschreibungen oder Vereinsnachrichten) können Dateien über Django `FileField`s hochgeladen und verwaltet werden.

Standardmäßig verbleiben Dateien beim Aktualisieren oder Löschen von Django-Modellinstanzen physisch auf dem Datenträger (`MEDIA_ROOT`). Auf Dauer führt dies zu verwaisten Dateien („File Leaks“), unnötigem Speicherplatzverbrauch und potenziellen Datenüberbleibseln, die den Datenschutzgrundsätzen der Datenminimierung und Speicherbegrenzung (Art. 5 Abs. 1 lit. c, e DSGVO) widersprechen.

Gleichzeitig verlangen die Architekturregeln ([AGENTS.md](../../AGENTS.md)):
- Finanzdaten (`CashEntry`, `Payment`) dürfen niemals gelöscht werden (ADR-005, ADR-006, GoBD-Konformität).
- Keine unnötigen Hintergrund-Worker (kein Celery/Redis).
- Transaktionssicherheit: Dateien dürfen bei abgebrochenen Datenbank-Transaktionen nicht vorzeitig gelöscht werden.

## Decision

1. **Integration von `django-cleanup` (>=9.0):**
   - Aufnahme von `django-cleanup>=9.0` in `requirements.txt`.
   - Registrierung von `"django_cleanup.apps.CleanupConfig"` am Ende von `INSTALLED_APPS` in `config/settings.py`.
   - Definition von `MEDIA_URL = "media/"` und `MEDIA_ROOT = BASE_DIR / "media"`, inkl. Aufnahme von `media/` in `.gitignore`.
   - Einbindung von `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` in `config/urls.py` für die lokale Entwicklungsumgebung (`DEBUG=True`).

2. **Funktionsweise & Transaktionssicherheit:**
   - `django-cleanup` lauscht auf `post_delete`- und `post_save`-Signale aller Modelle mit Dateifeldern.
   - Die physische Löschung wird über Djangos `transaction.on_commit()` erst nach erfolgreichem Datenbank-Commit ausgeführt. Scheitert eine Transaktion (Rollback), bleibt die Datei auf der Festplatte erhalten.
   - Fehlt eine Datei auf dem Dateisystem bereits, fängt `django-cleanup` dies sauber ab, ohne dass die Modell-Löschung abbricht.
   - Modelle ohne `FileField` oder ohne Löschberechtigung (wie die GoBD-geschützten Finanzdaten) bleiben unberührt.

3. **Verifikation:**
   - Dedizierte Testsuite in `core/tests/test_cleanup.py` prüft:
     - Korrekte Registrierung in `INSTALLED_APPS` und `MEDIA_*`-Konfiguration.
     - Physische Dateilöschung beim Löschen von Modellinstanzen.
     - Physische Dateilöschung beim Ersetzen bestehender Dateien (Altdaten werden entfernt, Neudaten bleiben).
     - Negativtest: Fehlertoleranz bei bereits gelöschten oder leeren Dateifeldern.
     - Negativtest: Erhalt der physischen Datei bei Transaktions-Rollbacks.
     - Negativtest: Unveränderter Löschschutz für Finanzdaten gemäß GoBD.

## Consequences

- Das Dateisystem bereinigt sich vollautomatisch im Hintergrund ohne Cronjobs, Celery oder manuelle Wartungsskripte.
- DSGVO-Konformität: Keine verwaisten Dateileichen auf dem Server.
- Vollständige Kompatibilität mit dem bestehenden Stack (Django 5, PostgreSQL, Docker Compose).
