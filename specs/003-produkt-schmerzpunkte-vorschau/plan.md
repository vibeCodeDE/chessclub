# Implementation Plan: Schmerzpunkte, Lösungen & Interaktive Vorschau auf /produkt

**Branch**: `003-produkt-schmerzpunkte-vorschau` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-produkt-schmerzpunkte-vorschau/spec.md`

## Summary

Erweiterung der Produkt-Landingpage (`/produkt/` bzw. `/` auf Marketing-Domains) um eine interaktive Schmerzpunkte- und Lösungssektion mit Live-Vorschau. Besucher können zwischen den 5 zentralen Vereinsrollen (Vorstand, Kassenwart, Spielleiter, Mannschaftsführer, Mitglieder) umschalten und sehen für jeden Bereich die typischen Frustpunkte des Vereinsalltags („Vorher“), die passgenaue Lösung der Software („Mit Schachverwaltung“) sowie eine reaktive Vorschau-Box (interaktives UI-Mockup).
Der technische Ansatz setzt auf eine modulare Datenstruktur in `core/produkt.py`, reines semantisches HTML5 und CSS3 (Radio-Tab-Architektur mit `:checked`-Selektoren) ohne externe JavaScript-Bibliotheken oder CDNs – für maximale Performance, 100 % DSGVO-Konformität und vollständige Barrierefreiheit (Progressive Enhancement).

## Technical Context

**Language/Version**: Python 3.12, Django 5.x, HTML5, Modern CSS3  
**Primary Dependencies**: Keine zusätzlichen Bibliotheken. Reines Django-Templating, lokales SVG-Sprite (`includes/sprite.html`), natives CSS (CSS Grid, Flexbox, CSS Variablen aus `app.css`).  
**Storage**: N/A (Rein konfigurationsbasierte Inhaltsdaten in `core/produkt.py`, keine Datenbankmigrationen erforderlich).  
**Testing**: `pytest` / Django `TestCase` (`core/tests/test_produkt.py`), Rollen-Vollständigkeitstests, Negativtests, Rendering-Tests.  
**Target Platform**: Responsive Web (Mobil ab 360 px, Desktop ab 1280 px), alle modernen Browser.  
**Project Type**: Web-Anwendung / Marketing-Landingpage.  
**Performance Goals**: < 50 ms Reaktionszeit bei Rollenwechsel, 0 ms Netzwerklatenz für Simulation, 0 zusätzliche HTTP-Requests.  
**Constraints**: 
- Strikt DSGVO-konform: 0 Tracker, 0 Cookies, keine Drittanbieter-CDNs oder Webfonts (N1.1, AGENTS.md).
- Strikte CSP: Keine Inline-Skripte.
- Barrierefreiheit (WCAG 2.1 AA) und Progressive Enhancement (volle Lesbarkeit auch ohne JavaScript).
- Kein horizontaler Overflow bei 360 px und 1280 px.  
**Scale/Scope**: 5 Vereinsrollen, 15 detaillierte Schmerzpunkte & Lösungen, 5 interaktive Mockup-Szenarien.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Stack-Konformität**: Django 5, Function-Based Views (`core/views.py`), Thin Views.
- [x] **Reine Funktionen & Modularität**: Datenhaltung als strukturierte Wörterbücher in `core/produkt.py`, sauber getrennt von Darstellungslogik. Keine N+1-Abfragen.
- [x] **DSGVO & Datenschutz**: Keine externen Assets (CDN, Fonts, Tracker) gemäß N1.1.
- [x] **Test-Driven-Development**: Vollständige Testabdeckung inklusive Negativtests vor Fertigstellung.
- [x] **UI-Qualität**: Overflow-Garantie bei 360 px und 1280 px.

## Project Structure

### Documentation (this feature)

```text
specs/003-produkt-schmerzpunkte-vorschau/
├── plan.md              # Dieser Plan (Architektur & Workflow)
├── research.md          # Phase 0: Lösungsansatz, CSS-Tab-Architektur, Teststrategie
├── data-model.md        # Phase 1: Datenstrukturen für Rollen, Schmerzpunkte & Mockups
├── quickstart.md        # Phase 1: Validierungsleitfaden & Testanleitung
├── contracts/           # Phase 1: Schnittstellen- & UI-Vertrag
│   └── ui-contract.md   # DOM-Struktur, Template-Kontext, ARIA, CSS-Selektoren
└── checklists/
    └── requirements.md  # Qualitätsprüfung der Spezifikation
```

### Source Code (repository root)

```text
core/
├── produkt.py                       # Datenstruktur ROLLEN_SCHMERZPUNKTE (5 Rollen, Frust, Lösung, Mockup-Daten)
├── views.py                         # Übergabe von rollen_schmerzpunkte an produkt_seite Kontext
├── templates/
│   └── core/
│       └── produkt.html             # Neue Sektion #loesungen mit Rollen-Tabs, Pain-Points & Mockup-Simulator
└── tests/
    └── test_produkt.py              # Tests für Datenintegrität, Rollenvollständigkeit, Rendering & CSP

static/
└── css/
    └── landing.css                  # Styles für .lp-role-selector, .lp-role-panel, .lp-panel-grid, .lp-mock-interactive
```

**Structure Decision**:
Die bestehende Struktur der Marketing-Seite wird nahtlos weitergeführt: Fachliche Inhalte verbleiben in `core/produkt.py`, Styling in `static/css/landing.css`, Template in `core/templates/core/produkt.html` und Tests in `core/tests/test_produkt.py`. Es werden keine neuen Apps oder Abhängigkeiten eingeführt (maximale Schlankheit).

## Complexity Tracking

*Keine Ausnahmen oder Regelverletzungen erforderlich. Die Lösung verwendet native Browser-Standards (HTML5/CSS3) und folgt strikt dem Minimalismus-Prinzip.*
