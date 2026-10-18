# Implementation Plan: Mannschaftskampf-Autopilot

**Branch**: `001-mannschaftskampf-autopilot` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

---

## Summary

Umsetzung von **Modul A: Der Mannschaftskampf-Autopilot** zur Beseitigung des organisatorischen Aufwands und Last-Minute-Chaos vor Spieltagen:
1. **Einmaliger Roster-Import**: Upload offizieller Mannschaftsmeldelisten (Rang- und Brettzuordnungen je Saison) als CSV/Excel mit Dry-Run-Validierung und Mitgliederabgleich.
2. **Automatisierte 10-Tage-Verfügbarkeitsabfrage**: Zeitgesteuerter Trigger generiert personalisierte, login-freie Magic-Links für Stammspieler. Spieler melden sich mit 1 Klick zurück (`[Bin dabei]`, `[Kann nicht]`, `[Fahrbedarf]`).
3. **Ersatzspieler-Ermittlung & Festspiel-Warnung**: Bei Absage analysiert eine reine Servicefunktion (`get_eligible_substitutes`) die unteren Mannschaften nach offizieller Rangliste, prüft Terminkollisionen und berechnet bisherige Einsätze gegen die Festspielschwelle (DSB-Turnierordnung, konfigurierbar).
4. **1-Klick-Ersatzanfrage (First-Come-First-Serve)**: Mannschaftsführer wählt Kandidaten vor und löst mit 1 Klick E-Mails sowie DSGVO-konforme WhatsApp Click-to-Chat-Aktionen (`wa.me`) aus. Der erste Klick sichert den Platz transaktionssicher (`select_for_update`); nachfolgende Klicks werden freundlich abgewiesen.
5. **Fahrgemeinschaften-Logistik**: Aggregation von Angebot und Nachfrage für Auswärtsspiele direkt im Spieltags-Cockpit.

---

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: Django 5.x, PostgreSQL (`psycopg`), `cryptography`, `secrets`, Vanilla JS & handgeschriebenes CSS (kein Node, kein Buildschritt, keine Fremd-CDNs gem. DSGVO N1.1)  
**Storage**: PostgreSQL (in Docker/Produktion), SQLite (in Testsuite)  
**Testing**: `pytest`, `pytest-django`, Django Test Client (`assertNumQueries`, Negativtests, Rollentests gem. PRD §3.8)  
**Target Platform**: Linux Server / Docker Compose, Webapplikation (Mobile-First responsive ab 360 px bis 1280 px)  
**Project Type**: Web-Anwendung (Server-seitig gerenderte Django-Templates mit Function-Based Views)  
**Performance Goals**: Magic-Link-Antwort in < 100 ms; Aufstellungsberechnung & Ersatzvorschläge in < 50 ms (max. 3 indizierte Queries); kein N+1  
**Constraints**: 100% DSGVO-konform (keine externen Gateways/Meta-APIs/CDNs), AuditLog für Aufstellungsänderungen, transaktionssichere Vergabe (`select_for_update`), rollenbasierter Zugriff (`@role_required(ADMIN_GROUP, KAPITAEN_GROUP)`)  
**Scale/Scope**: Typischer Schachverein (< 200 Mitglieder, 1–6 Mannschaften, 4–8 Bretter, 9–18 Spieltage/Saison)  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Kriterium / Prinzip (aus AGENTS.md & PRD) | Status | Bewertung & Nachweis |
|---|---|---|
| **I. Test-First & Negativtests** | ✅ PASS | Alle neuen Endpunkte erhalten Negativtests (403 für unberechtigte Rollen, abgelaufene Tokens, Doppelbesetzungen, Dry-Run-Validierungsfehler). |
| **II. Reine Fachlogik in `services.py`** | ✅ PASS | Fachlogik (`get_eligible_substitutes`, `get_carpool_summary`, `import_team_roster`, `process_sub_claim`) liegt ohne HTTP-Kontext in `teams/services.py`. |
| **III. Keine N+1-Abfragen & Query-Budgets** | ✅ PASS | Optimierte Abfragen mittels `select_related("member", "roster__team")` und `prefetch_related`; `assertNumQueries` sichert die Datenbankaufrufe im Test ab. |
| **IV. Revisionssicherheit & Audit-Spur** | ✅ PASS | Alle manuellen Aufstellungsänderungen, Absagen und Ersatzvergaben erzeugen Einträge im `AuditLog`. |
| **V. DSGVO & Keine Drittanbieter-Assets** | ✅ PASS | Null externe CDNs/Fonts/Tracker. WhatsApp erfolgt ausschließlich über clientseitige Click-to-Chat-Links (`wa.me`), keine Datenübertragung an Meta-Server. |
| **VI. Barrierefreiheit & Responsivität** | ✅ PASS | Mobile-First-Design ab 360 px für die Magic-Link-Oberfläche am Smartphone; Tastaturbedienbarkeit und semantisches HTML. |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-mannschaftskampf-autopilot/
├── plan.md              # Dieser Implementierungsplan (/speckit-plan)
├── research.md          # Phase 0: Technische Entscheidungen & Alternativen (/speckit-plan)
├── data-model.md        # Phase 1: Datenmodelle & Relationen (/speckit-plan)
├── quickstart.md        # Phase 1: Validierungs- und Testanleitung (/speckit-plan)
├── contracts/           # Phase 1: Schnittstellenverträge (/speckit-plan)
│   ├── magic-link-contract.md
│   ├── team-roster-import-contract.md
│   ├── substitution-finder-contract.md
│   └── carpool-contract.md
├── checklists/
│   └── requirements.md  # Spezifikations-Qualitätsprüfung
└── tasks.md             # Phase 2: Aufgabenliste (/speckit-tasks)
```

### Source Code (repository root)

```text
teams/
├── models.py            # Team (erweitert), TeamRoster, RosterEntry, MatchAvailabilityQuery, PlayerAvailability, SubRequest, SubRequestCandidate
├── forms.py             # RosterImportForm, AvailabilityResponseForm, SubRequestCandidateSelectionForm
├── services.py          # get_eligible_substitutes, get_carpool_summary, import_team_roster, create_match_query, claim_sub_seat
├── views.py             # team_roster_import, match_sub_finder, match_sub_request, availability_magic_view, sub_claim_magic_view
├── urls.py              # URL-Routing für /spielbetrieb/meldeliste/ und /spielbetrieb/rueckmeldung/ etc.
├── management/
│   └── commands/
│       └── process_match_queries.py  # Täglicher 10-Tage-Trigger für Verfügbarkeitsabfragen
└── tests/
    ├── test_autopilot.py       # E2E- und Unittests für Magic Links, FCFS und Festspiel-Berechnung
    ├── test_roster_import.py   # Dry-Run- und Validierungstests für Roster-Upload
    └── test_carpool.py         # Fahrgemeinschaften-Aggregation

templates/
└── teams/
    ├── autopilot/
    │   ├── availability_form.html    # Mobile Ein-Klick-Rückmeldung für Stammspieler
    │   ├── availability_thanks.html  # Bestätigungsseite
    │   ├── sub_claim_form.html       # Mobile Zusage für Ersatzkandidaten (FCFS)
    │   ├── sub_already_taken.html    # Hinweis bei vergebenem Platz
    │   └── sub_finder_modal.html     # Ersatzspieler-Vorschlag mit Festspielwarnung & Checkboxen
    ├── roster_import.html            # Upload- & Dry-Run-Maske für Meldelisten
    └── includes/
        └── carpool_widget.html       # Fahrgemeinschaften-Ampel im Spieltags-Cockpit
```

---

## Complexity Tracking

| Verletzung / Abweichung | Warum benötigt | Einfachere Alternative verworfen, weil |
|---|---|---|
| *Keine Verletzungen* | Alle Architekturvorgaben aus AGENTS.md und PRD werden strikt eingehalten. | - |
