# Implementation Plan: Onboarding für einen neuen Schachverein

**Branch**: `002-vereins-onboarding` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-vereins-onboarding/spec.md`

---

## Summary

Einführung eines intuitiven, geführten Onboarding-Assistenten (`/onboarding/`) und eines dynamischen Dashboard-Widgets („Erste Schritte“) für neue Schachvereine. Der Assistent führt den Administrator in 6 logischen Schritten durch die Ersteinrichtung:
1. Vereinsstammdaten & DSB-Verbandsschlüssel (ZPS)
2. Modulauswahl (Satellitenmodule aktivieren/deaktivieren via `ModuleSettings`)
3. Beitragsstruktur (1-Klick-Übernahme von Best-Practice-Kategorien)
4. Mitglieder-Datenübernahme (Hybrid-Weg: ZPS-Direktimport aus DSB-Wertungsportal ODER CSV-Import mit Dry-Run)
5. Funktionäre einladen (E-Mail-Einladungslink mit sicherem Token und eigenständiger Passwortvergabe)
6. Zusammenfassung, Demo-Daten-Bereinigung und Produktivstart

Nach Abschluss begleitet ein interaktives Fortschritts-Widget auf dem Vorstandsdashboard den Verein bei den ersten Schritten.

---

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: Django 5.x, `cryptography` (Fernet für SEPA-IBAN), `urllib` (Standardbibliothek für DSB-Wertungsportal-Abruf), Vanilla JS & handgeschriebenes CSS (kein Node, kein Tailwind-Build, keine Fremd-CDNs gem. DSGVO N1.1)  
**Storage**: PostgreSQL (in Produktion / Docker), SQLite (in Testsuite)  
**Testing**: `pytest`, `pytest-django`, Django Test Client (`assertNumQueries`, Rollentests gem. PRD §3.8)  
**Target Platform**: Linux Server / Docker Compose, Webapplikation (Mobile-First responsive ab 360 px bis 1280 px)  
**Project Type**: Web-Anwendung (Server-seitig gerenderte Django-Templates)  
**Performance Goals**: Onboarding-Schritte laden in < 100 ms; aggregierte Widget-Prüfung in < 30 ms (max. 4 indizierte Queries); Mitgliederimport (50–150 Personen) in < 3 Sekunden  
**Constraints**: Strikte DSGVO-Konformität (keine externen Tracker/CDNs/Fonts), Revisionssicherheit aller Änderungen im `AuditLog`, keine Finanzdatenlöschung, rollenbasierter Zugriffschutz (`@role_required(ADMIN_GROUP)`)  
**Scale/Scope**: Typischer Schachverein (< 200 Mitglieder, ≤ 20 gleichzeitige Nutzer)  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Kriterium / Prinzip (aus AGENTS.md & PRD) | Status | Bewertung & Nachweis |
|---|---|---|
| **I. Test-First & Negativtests** | ✅ PASS | Jeder Schritt und jede Route erhält mindestens einen Negativtest (403 für Nicht-Admins, ungültige Tokens, Dry-Run-Abbrüche, Dublettenprüfung). |
| **II. Reine Fachlogik in `services.py`** | ✅ PASS | Fachlogik (`import_dsb_initial`, `create_staff_invitation`, `accept_staff_invitation`, `get_onboarding_checklist_status`) liegt ohne HTTP-Kontext in `core/services.py` und `members/services/dsb_sync.py`. |
| **III. Keine N+1-Abfragen & Query-Budgets** | ✅ PASS | Widget-Abfrage nutzt gezielte `EXISTS`/`COUNT`-Statements; `assertNumQueries` sichert die Datenbankaufrufe im Test ab. |
| **IV. Finanzdaten & Audit-Spur** | ✅ PASS | Finanzdaten (Beitragsposten, Kassenbuch) werden niemals gelöscht. Alle Profiländerungen, Importe und Einladungen schreiben unveränderliche `AuditLog`-Einträge. |
| **V. DSGVO & Keine Drittanbieter-Assets** | ✅ PASS | Keine externen CDNs/Fonts/Tracker. IBANs werden verschlüsselt gespeichert (Fernet). ZPS-Abgleich läuft rein serverseitig. |
| **VI. Barrierefreiheit & Responsivität** | ✅ PASS | Erfüllung von WCAG 2.1 AA; fehlerfreie Darstellung und Tastaturbedienbarkeit auf 360 px ohne horizontalen Scrollbalken. |

---

## Project Structure

### Documentation (this feature)

```text
specs/002-vereins-onboarding/
├── plan.md              # Dieser Implementierungsplan
├── research.md          # Phase 0: Technische Entscheidungen & Alternativen
├── data-model.md        # Phase 1: Datenmodelle & Relationen
├── quickstart.md        # Phase 1: Validierungs- und Testanleitung
├── contracts/           # Phase 1: Schnittstellenverträge
│   ├── onboarding-wizard-api.md
│   ├── dsb-initial-import-contract.md
│   ├── staff-invitation-contract.md
│   └── getting-started-widget-contract.md
├── checklists/
│   └── requirements.md  # Spezifikations-Qualitätsprüfung
└── tasks.md             # Phase 2: Aufgabenliste (/speckit-tasks)
```

### Source Code (repository root)

```text
core/
├── models.py            # ClubProfile (erweitert um zps_nummer), OnboardingProgress, StaffInvitation
├── forms_onboarding.py  # Formulare für die 6 Onboarding-Schritte
├── services.py          # Onboarding-Status, Checklist-Ermittlung, Funktionärseinladungen
├── views_onboarding.py  # Function-Based Views für den Wizard (/onboarding/...)
├── auth_views.py        # Erst-Redirect nach Login für unvollständige Instanzen
├── urls.py              # URL-Routing für /onboarding/ und /einladung/<token>/
└── tests/
    ├── test_onboarding.py        # E2E- und Rollentests für den Assistenten
    └── test_staff_invitation.py  # Tests für Einladungstokens und Registrierung

members/
└── services/
    └── dsb_sync.py      # Erweiterung um import_dsb_initial

templates/
├── core/
│   ├── onboarding/
│   │   ├── base_onboarding.html  # Progress-Bar & Wizard-Shell
│   │   ├── step_1_profile.html   # Stammdaten
│   │   ├── step_2_modules.html   # Modultoggles
│   │   ├── step_3_dues.html      # Beitragskategorien
│   │   ├── step_4_import.html    # Hybrid-Import (ZPS / CSV)
│   │   ├── step_5_staff.html     # Funktionäre
│   │   └── step_6_finish.html    # Zusammenfassung & Go-Live
│   ├── includes/
│   │   └── onboarding_widget.html # Dashboard Getting-Started Widget
│   └── invitation_accept.html    # Passwortvergabe für eingeladene Funktionäre

static/
└── css/
    └── app.css          # Wizard-Styling (Barrierefrei, 360 px bis 1280 px)
```

**Structure Decision**: Konsistente Erweiterung der bestehenden Django-Apps `core` (Allgemeine Steuerung, Profile, Einladungen) und `members` (DSB-Mitgliederimport). Keine neuen Third-Party-Packages, keine SPA.

---

## Complexity Tracking

> Keine Constitution-Verletzungen. Kein Über-Engineering (YAGNI): Bestehende Services (`dsb_sync`, `import_service`, `ClubProfile`, `ModuleSettings`, `DemoData`) werden direkt wiederverwendet und über ein einfaches Singleton-Zustandsmodell orchestriert.

| Aspekt | Gewählte Lösung | Warum kein Over-Engineering |
|---|---|---|
| Wizard-State | `OnboardingProgress` (Singleton, DB) | Keine volatilen Session-Caches, keine Third-Party FormWizard-Bibliothek nötig. |
| ZPS-Import | Kapselung in `members.services.dsb_sync` | Nutzt bestehende HTTP- und Parser-Infrastruktur; kein neuer API-Client. |
| Einladungs-Tokens | `secrets.token_urlsafe(32)` | Native Python-Standardbibliothek; keine schwere Einladungs-Engine nötig. |
| Dashboard-Widget | Reiner Context-Injektor im Vorstandsdashboard | 4 einfache Aggregate; keine WebSocket- oder SPA-Komplexität. |
