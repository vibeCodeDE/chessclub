# Implementation Plan: Saisonverwaltung für den Vereinsvorstand (z. B. 2026/2027)

**Branch**: `004-saison-verwaltung` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

---

## Summary

Umsetzung der zentralen **Saisonverwaltung für den Vereinsvorstand** zur strukturierten Steuerung von Spielzeiten (z. B. `2026/2027`), historisierten Spielbetrieben und Vereinsturnieren:
1. **Saison-Modell & Steuerung der aktiven Hauptsaison**: Einführung von `Season` in `teams.models` mit Zeitraum, Status (`vorbereitung`, `aktiv`, `archiviert`) und atomar geschaltetem `ist_aktiv`-Flag.
2. **Saisonbindung von Mannschaften & Bestandsdaten-Migration**: Anbindung von `Team.saison` (`models.PROTECT`), Ersetzen des globalen `unique=True` auf den Namen durch `UniqueConstraint(name, saison)`, samt verlustfreier Drei-Stufen-Datenmigration für bestehende Teams.
3. **Geführter Saisonwechsel (Rollover-Assistent)**: 1-Klick-Übernahme bestehender Mannschaften aus der Vorsaison mit flexibler Anpassung von Liga, Brettanzahl und Mannschaftsleitung sowie leeren Spielplänen für das neue Jahr (`rollover_teams`).
4. **Saisonbezogener Spielbetrieb & Filter-Integration**: Globaler Context-Processor `season_context` und Template-Filter zur nahtlosen Navigation zwischen aktiver Hauptsaison und historischen Spielzeiten.
5. **Archivierungs-Schreibschutz & Löschsperre**: Schutz historischer Spielberichte und Aufstellungen gegen versehentliche Manipulation nach Saisonabschluss (`archive_season`), Revisionssicherheit via `AuditLog` und Blockade von Datenverlusten.

---

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: Django 5.x, PostgreSQL (`psycopg`), Tailwind/CSS (handgeschrieben, keine Fremd-CDNs gem. DSGVO N1.1)  
**Storage**: PostgreSQL (in Produktion/Docker), SQLite (in automatisierter Testsuite)  
**Testing**: `pytest`, `pytest-django`, Django Test Client (`assertNumQueries`, Negativtests, Rollen-Matrix gem. PRD §3.8)  
**Target Platform**: Linux Server / Docker Compose, Webapplikation (Mobile-First responsive ab 360 px bis 1280 px)  
**Project Type**: Web-Anwendung (Server-seitig gerenderte Django-Templates mit Function-Based Views)  
**Performance Goals**: Umschalten der Saison & Laden gefilterter Listen in < 100 ms (max. 3 optimierte SQL-Queries via `select_related`/`prefetch_related`); kein N+1  
**Constraints**: 100 % DSGVO-konform, AuditLog für alle Vorstandshandlungen, Barrierefreiheit nach WCAG 2.1 AA (Kontraste ≥ 4.5:1, Tastaturfokus), rollenbasierter Zugriff (`@role_required(ADMIN_GROUP)`)  
**Scale/Scope**: Schachverein (< 200 Mitglieder, 1–10 Mannschaften, 1–5 aktive/historische Saisons)  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Kriterium / Prinzip (aus AGENTS.md & PRD) | Status | Bewertung & Nachweis |
|---|---|---|
| **I. Test-First & Negativtests** | ✅ PASS | Alle Verwaltungs-Endpunkte erhalten Negativtests (403 für Gast/Mitglied/Kapitän, ungültige Datumsbereiche, Löschblockade bei verknüpften Daten, Schreibschutz für archivierte Saisons). |
| **II. Reine Fachlogik in `services.py`** | ✅ PASS | Alle Geschäftsregeln (`create_season`, `set_active_season`, `archive_season`, `rollover_teams`) liegen als reine Funktionen ohne HTTP-Kontext in `teams/services.py`. |
| **III. Keine N+1-Abfragen & Query-Budgets** | ✅ PASS | QuerySets nutzen `select_related("saison", "kapitaen")` und `prefetch_related("matches")`; `assertNumQueries` sichert die Abfragebudgets in Tests ab. |
| **IV. Revisionssicherheit & Audit-Spur** | ✅ PASS | Statuswechsel (Aktivierung, Archivierung), Datumsänderungen und Mannschaftsübernahmen erzeugen strukturierte `AuditLog`-Einträge. |
| **V. DSGVO & Keine Drittanbieter-Assets** | ✅ PASS | Keine externen CDNs, Tracker oder Web-Fonts; alle Assets liegen lokal vor. |
| **VI. Barrierefreiheit & Responsivität** | ✅ PASS | WCAG 2.1 AA mit Touch-Zielen ≥ 44 px, sichtbaren Fokus-Ringen und responsiver Darstellung ab 360 px ohne horizontalen Overflow. |

---

## Project Structure

### Documentation (this feature)

```text
specs/004-saison-verwaltung/
├── spec.md              # Fachliche Spezifikation (/speckit-specify)
├── plan.md              # Dieser Implementierungsplan (/speckit-plan)
├── research.md          # Phase 0: Architekturentscheidungen & Recherchen (/speckit-plan)
├── data-model.md        # Phase 1: Datenmodelle, Relationen & Status-Automaten (/speckit-plan)
├── quickstart.md        # Phase 1: Validierungs- und Testanleitung (/speckit-plan)
├── contracts/           # Phase 1: Schnittstellen- und Service-Verträge (/speckit-plan)
│   ├── season-endpoints-contract.md
│   ├── season-services-contract.md
│   └── season-template-context-contract.md
├── checklists/
│   └── requirements.md  # Spezifikations-Qualitätsprüfung
└── tasks.md             # Phase 2: Aufgabenliste (/speckit-tasks)
```

### Source Code (repository root)

```text
teams/
├── models.py            # Neues Modell Season, modifiziertes Modell Team (FK saison, UniqueConstraint)
├── forms.py             # SeasonForm, SeasonRolloverForm
├── services.py          # create_season, set_active_season, archive_season, rollover_teams, validate_match_season_bounds
├── context_processors.py# season_context (aktive_saison, alle_saisons, gewaehlte_saison)
├── views.py             # season_list, season_create, season_edit, season_activate, season_archive, season_delete, season_rollover
├── urls.py              # URL-Routing für /saison/ und Aktionen
├── migrations/          # 3-stufige Migration (Schema, Datenmigration für Bestandsteams, Constraints)
└── tests/
    └── test_season.py   # Umfassende Tests (CRUD, Rollenprüfung, Negativtests, Rollover, Query-Budgets)

tournaments/
└── models.py            # Modellerweiterung: saison = ForeignKey("teams.Season", null=True, blank=True)

templates/
├── teams/
│   ├── season_list.html     # Übersichts- und Verwaltungsliste der Saisons für den Vorstand
│   ├── season_form.html     # Anlege- und Bearbeitungsmaske
│   ├── season_rollover.html # Tabellarischer Übernahme-Assistent für Mannschaften
│   └── includes/
│       └── season_filter.html # Wiederverwendbare Saison-Auswahlkomponente für Spielbetrieb/Turniere
└── includes/
    └── navigation.html      # Menüeintrag "Saisons" für Administratoren/Vorstände
```

---

## Complexity Tracking

| Verletzung / Abweichung | Warum benötigt | Einfachere Alternative verworfen, weil |
|---|---|---|
| *Keine Verletzungen* | Alle Architekturvorgaben aus AGENTS.md, dem PRD und Spec-Kit werden eingehalten. | - |
