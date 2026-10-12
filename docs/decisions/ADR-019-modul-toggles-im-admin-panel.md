# ADR-019: Modul-Toggles im Django Admin Panel (UI- und Feature-Schalter)

## Status

Accepted

## Date

2026-10-11

## Context

Schachvereine variieren stark in ihrer Struktur und ihren Schwerpunkten (PRD §1). Ein kleiner Verein
mit 25 Mitgliedern ohne Ligabetrieb benötigt keine Mannschaftsaufstellungen (`teams`); ein Verein,
dessen Kassenwart eine externe Buchhaltungssoftware nutzt, benötigt kein separates Vereinskassenbuch
(`cashbook`); ein reiner Trainingsclub veranstaltet keine offenen Schweizer-System-Turniere (`tournaments`).
Zudem sieht die Managed-Abo-Preisgestaltung in [ADR-014](ADR-014-preisgestaltung.md) unterschiedliche
Tarife vor (z. B. „Start“ ohne Spielbetrieb vs. „Verein“ mit Spielbetrieb).

Bislang waren alle Module statisch in der Navigation und im Dashboard für alle berechtigten Rollen sichtbar.
Es stellte sich die Frage, ob und wie der Superadmin bzw. Vereinsvorstand einzelne Module an- und
ausschalten können soll.

Ein dynamisches Laden/Entladen von Django-Apps zur Laufzeit (`INSTALLED_APPS`) scheidet aus: Es würde
Foreign-Key-Constraints, Migrationen, Datenbank-Integrität und URL-Registrierungen beschädigen.

## Decision

1. **Singleton-Modell `ModuleSettings` in `core/models.py`:**
   - Speichert die Aktivierung der vier optionalen Satellitenmodule:
     - `spielbetrieb_aktiv` (`teams`)
     - `turniere_aktiv` (`tournaments`)
     - `kassenbuch_aktiv` (`cashbook`)
     - `nachrichten_aktiv` (`comms`)
   - Immer genau ein Datensatz (`pk=1`), Löschen im Modell und Admin unterbunden.
   - Kernmodule (`core`, `members`, `dues`) sind **niemals abschaltbar**, da sie die Basis für
     Benutzer, Authentifizierung, DSGVO-Rechte und Mitgliederverwaltung bilden.

2. **Reine Fachlogik in `core/services.py`:**
   - `is_module_active(module_key, request=None)` prüft den Aktivitätsstatus.
   - O(1)-Query-Budget per Request durch Caching am `request`-Objekt (`request._module_settings`).

3. **URL-Schutz via Middleware `ModulAktivMiddleware`:**
   - Versucht ein Nutzer oder Gast eine Route eines inaktiven Moduls direkt aufzurufen
     (z. B. `/mannschaften/`, `/turniere/`, `/kasse/`, `/ankuendigungen/`), antwortet das
     System mit HTTP 404 („Modul deaktiviert“).
   - Der Django-Admin (`/admin/`) bleibt für Superadmins zur Administration erreichbar.

4. **Dynamische Navigation und UI-Anpassung:**
   - `core/context_processors.py` filtert inaktive Menüeinträge und ganze Sektionen aus
     `nav_sektionen` heraus.
   - Badges für inaktive Module werden nicht abgefragt (keine unnötigen Queries).
   - Das Dashboard (`core/templates/core/dashboard*.html`) und die öffentliche Vereinsseite
     blenden Kacheln und Termine inaktiver Module aus.
   - Die globale Suche (`core/views.py:suche`) ignoriert Treffer aus inaktiven Modulen.

5. **Integrität der Finanzdaten bleibt gewahrt:**
   - Wenn `kassenbuch_aktiv=False` ist, erzeugt die Beitragszahlung in `dues/services.py`
     weiterhin im Hintergrund den revisionssicheren `CashEntry`-Datensatz (ADR-005, ADR-006).
     Nur die Benutzeroberfläche und die Kassenbuch-Routen sind deaktiviert. Daten werden nie gelöscht.

6. **Audit-Trail für Konfigurationsänderungen:**
   - Jede Statusänderung der Modul-Toggles im Admin-Panel erzeugt einen Eintrag im `AuditLog`
     mit handelndem Benutzer und geänderten Modulwerten.

## Alternatives Considered

### Steuerung rein über Umgebungsvariablen (`.env`)
- Pro: Kein Modell, keine Migration, kein DB-Zustand.
- Contra: Erfordert Container-Neustart bei Änderungen und kann nicht durch den Vorstand
  selbstständig im Browser konfiguriert werden.

### Dynamisches Ändern von `INSTALLED_APPS`
- Abgelehnt: Zerstört relationale Integrität, Migrationen und URL-Dispatcher.

## Consequences

- Vorstände und Superadmins können die Softwareoberfläche passgenau auf die Bedürfnisse ihres
  Vereins zuschneiden, ohne Code anzufassen oder Container neuzustarten.
- Alle Daten inaktiver Module bleiben in der PostgreSQL-Datenbank unverändert erhalten; bei
  Reaktivierung ist der Zustand sofort wieder vollständig verfügbar.
