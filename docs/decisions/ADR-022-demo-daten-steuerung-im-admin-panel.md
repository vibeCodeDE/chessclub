# ADR-022: Demo-Daten-Steuerung im Django Admin Panel (Ein / Aus)

## Status

Accepted

## Date

2026-10-14

## Context

Für Präsentationen, Funktionsprüfungen, Abnahmetests und Schulungen werden realistische Vereins- und Spielbetriebsdaten benötigt. Hierfür existiert der Management-Befehl `python manage.py seed_demo`.

Im Cloud- und Managed-Betrieb (z. B. auf Scalingo oder bei Vorstandsmitgliedern ohne Terminal-/SSH-Zugriff) ist die Ausführung von CLI-Befehlen jedoch umständlich oder unzugänglich. Es bestand der Wunsch, die Demo-Daten direkt über das geschützte Django Admin Panel (`/admin/`) an- und ausschalten (laden und entfernen) zu können.

Dabei müssen zentrale Sicherheits- und Revisionsanforderungen gewahrt bleiben:
1. **Schutz vor Datenverlust:** Ein versehentliches Löschen echter Mitglieder-, Vereins- oder Finanzdaten darf niemals möglich sein.
2. **Revisionssicherheit & Audit-Trail:** Sowohl das Laden als auch das Entfernen der Demo-Daten muss im `AuditLog` mit Zeitstempel und handelndem Benutzer unveränderlich protokolliert werden.
3. **Berechtigung:** Zugriff ausschließlich für autorisierte Administratoren (`admin`-Gruppe bzw. `is_superuser`).

## Decision

1. **Reine Fachlogik in `core/services.py`:**
   - `get_demo_data_status()`: Analysiert den Zustand der Datenbank (Demo-Daten vorhanden, Mitgliederanzahl, Erkennung von manuell angelegten / echten Mitgliedern oder Benutzern).
   - `install_demo_data(user=None)`: Führt das Seeding aus (sofern keine Mitglieder existieren) und protokolliert die Aktion im `AuditLog`.
   - `remove_demo_data(user=None, confirm=False)`:
     - Verlangt explizite Bestätigung (`confirm=True`).
     - Prüft auf echte Produktivdaten (`has_real_data`). Werden echte Mitglieder oder Benutzer gefunden, wird der Vorgang sofort mit einer Fehlermeldung abgebrochen.
     - Löscht bei ausschließlichem Demo-Bestand atomar die Beispieldaten.
     - Schreibt einen Revisions-Eintrag in das `AuditLog` (`AuditLog` selbst wird nicht gelöscht).

2. **Proxy-Modell `DemoData` in `core/models.py`:**
   - Ein Proxy-Modell auf `ModuleSettings` (`proxy = True`), wodurch keine neuen Tabellen oder komplexen Schemaänderungen entstehen.
   - Registriert im Django Admin (`core/admin.py`) als „Demo-Daten (Ein/Aus)“.

3. **Admin-Ansicht & Template (`templates/admin/core/demodata/change_list.html`):**
   - Übersichtlicher Dashboard-Status (Aktiv / Inaktiv, Kennzahlen).
   - Zwei klar getrennte Aktionen:
     - **Demo-Daten laden („An“)**: Grüner Primärbutton; gesperrt, falls bereits Mitglieder existieren.
     - **Demo-Daten entfernen („Aus“)**: Roter Button mit Bestätigungs-Checkbox; gesperrt bei erkannten Produktivdaten.
   - Audit-Historie der letzten Demo-Aktionen.
   - Nahtloses Theming (Light Mode / Dark Mode) gemäß WCAG 2.1 AA Kontrastanforderungen.

## Consequences

- Vorstände und Administratoren können Test- und Vorführdaten mit einem Klick im Browser erzeugen und wieder zurücksetzen.
- Echte Produktivdaten sind durch automatische Heuristiken und Bestätigungspflicht gegen versehentliches Löschen geschützt.
- Sämtliche Vorgänge sind im Audit-Log lückenlos nachvollziehbar.
