# ADR-023: Vereinshomepage als modulares Add-on (`homepage_aktiv`)

## Status

Accepted

## Date

2026-10-17

## Context

Die Kernanwendung des Systems ist die **Schachverwaltung** (Mitgliederstamm, Beitrags- und SEPA-Mandatswesen, Spielbetrieb/Mannschaftskämpfe, Schweizer-System-Turniere, Kassenbuch, Audit-Trail, internes Mitglieder- & Funktionärs-Dashboard).

Schachvereine variieren in ihrer digitalen Infrastruktur:
- Viele Vereine verfügen bereits über eine langjährig etablierte Vereinswebsite (z. B. auf WordPress, Typo3, Jimdo oder einer Subdomain des Hauptsportvereins) und betreiben die Schachverwaltung auf einer separaten Verwaltungs-Subdomain (z. B. `verwaltung.schachverein.de` oder `app.schachverein.de`).
- In diesem Szenario ist eine öffentliche Startseite mit Vereinsporträt und allgemeinen Vereinsinformationen überflüssig oder verwirrend.
- Andere Vereine hingegen möchten das Gesamtsystem als „All-in-One“-Lösung nutzen und die integrierte öffentliche Vereinswebsite (`/`, `/verein/`, öffentliche News und Termine) als Webauftritt einsetzen.

Bislang war die Vereinshomepage fest als Einstiegsroute `/` verdrahtet und konnte – im Gegensatz zu den anderen Satellitenmodulen (ADR-019) – nicht abgeschaltet werden.

## Decision

1. **Erweiterung des Singleton-Modells `ModuleSettings` (`core/models.py`):**
   - Neues Boolean-Feld `homepage_aktiv` (Default: `True` zur Gewährleistung der Abwärtskompatibilität).
   - Steuerung direkt im Django Admin Panel (`ModuleSettingsAdmin`) sowie im Onboarding-Assistenten (Schritt 2).

2. **Reine Fachlogik in `core/services.py`:**
   - Registrierung der Schlüssel `"homepage"`, `"vereinshomepage"`, `"webseite"` in `MODUL_SCHLUESSEL`.
   - `is_module_active("homepage", request)` prüft den Aktivitätszustand mit O(1)-Request-Caching.

3. **Routing und Weiterleitung bei inaktiver Homepage:**
   - **Startseite `/` (`core:home`):**
     - Angemeldete Benutzer werden transparent direkt auf ihr internes Dashboard (`core:dashboard`) umgeleitet.
     - Nicht angemeldete Besucher werden zur Anmeldeseite (`core:login`) weitergeleitet.
   - **Öffentliche Vereinsseite `/verein/` (`core:verein`):**
     - Wird bei inaktivem Modul durch `ModulAktivMiddleware` mit HTTP 404 blockiert.
   - **Rechtliche Pflichtseiten (`/impressum/`, `/datenschutz/`):**
     - Bleiben aus rechtlichen Gründen (DSGVO / TMG) stets erreichbar.

4. **Dynamische Navigation (`core/context_processors.py`):**
   - Der Menüeintrag *„Vereinsseite“* (`core:home`) wird in der internen Seitennavigation (`nav_sektionen`) ausgeblendet, wenn `homepage_aktiv=False` ist.
   - Interne Dashboard-Kacheln (z. B. Vereinsabend-Karte) verlinken bei inaktiver Homepage nicht mehr auf `/verein/`.

5. **Onboarding-Integration (`core/views_onboarding.py`, Schritt 2):**
   - Neue Vereine können in Schritt 2 des Assistenten explizit wählen, ob sie die Vereinshomepage aktivieren möchten oder bereits eine eigene Website betreiben.

## Alternatives Considered

### Vereinshomepage als getrennte Django-App
- Abgelehnt: Würde unnötig Code und Templates fragmentieren (`core` enthält bereits schlanke Views für Landing und Impressum). Das Modul-Toggle-Muster aus ADR-019 hat sich für flexible Funktionsbereiche bewährt.

### Statische Steuerung rein über Environment-Variablen (`.env`)
- Abgelehnt: Erfordert Serverneustarts und nimmt dem Vorstand die Möglichkeit, das System direkt im Browser oder Onboarding zu konfigurieren.

## Consequences

- Klare Schärfung der Produktidentität: Die Schachverwaltung ist die Hauptanwendung, die Vereinshomepage ein flexibles Add-on.
- Vereine mit externer Homepage können die Software nahtlos als reines Verwaltungs- und Spielbetriebs-Portal auf einer Subdomain betreiben, ohne dass Besuchern eine doppelte Vereinsstartseite angezeigt wird.
- Vollständige Reversibilität: Das Modul kann jederzeit mit einem Klick im Admin-Panel reaktiviert werden, ohne dass Inhalte oder Einstellungen verloren gehen.
