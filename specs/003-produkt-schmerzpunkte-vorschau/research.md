# Phase 0 Research: Schmerzpunkte, Lösungen & Interaktive Vorschau auf /produkt

**Feature**: `003-produkt-schmerzpunkte-vorschau`  
**Date**: 2026-10-17  
**Status**: Completed  

---

## 1. Technischer Kontext & Fragestellungen

### Frage 1: Wie wird die Interaktivität für Rollenauswahl und Vorschau-Simulation realisiert?

- **Kontext**:
  Die Landingpage (`/produkt/` bzw. `/` auf Marketing-Domains) unterliegt strengen Qualitäts-, Sicherheits- und Datenschutzanforderungen:
  1. Keine externen CDNs, Tracker oder Dritt-Skripte (DSGVO N1.1, AGENTS.md).
  2. Strikte Content Security Policy (CSP). Der bestehende Test `test_keine_inline_skripte` prüft `assertNotIn("<script", inhalt)`.
  3. Vollständige Funktionalität auch bei deaktiviertem JavaScript (FR-007, SC-002, Progressive Enhancement).
  4. Null Flackern, 0ms Ladezeit, responsive von 360 px bis Desktop (SC-001, SC-004).

- **Entscheidung**:
  **CSS `:checked` Radio-Tab-Architektur mit semantischem HTML** (unterstützt durch optionale, progressive Script-Erweiterung in `static/js/landing.js`, falls Tastatur-Pfeilnavigation erweitert wird, ohne dass Inline-Scripts benötigt werden).
  - Die Rollenauswahl erfolgt über verdeckte `<input type="radio" name="lp-role" id="role-..." class="lp-role-radio">` in Kombination mit voll tastaturfokussierbaren `<label for="role-..." class="lp-role-tab">`.
  - Die interaktiven Mockup-Zustände (z. B. Umschalten zwischen Mahnstufen 1–3 oder Turnierrunden) nutzen denselben robusten Radio-/Checkbox-Mechanismus.
  - Ohne JavaScript funktioniert die gesamte Komponente zu 100 % im Browser.
  - Für Screenreader werden semantische Rollen (`role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-controls`) und aussagekräftige Labels verwendet.

- **Alternativen**:
  1. *JavaScript-Framework (Vue, React, Alpine.js)*:
     Verworfen. Verstößt gegen Einfachheitsregeln (YAGNI, Ponytail-Prinzip), bläht das Bundle auf, benötigt Build-Tools und bricht bei deaktiviertem JS.
  2. *Inline-JavaScript*:
     Verworfen. Verletzt CSP und den Test `test_keine_inline_skripte` in `core/tests/test_produkt.py`.
  3. *Reines `<details>`/`<summary>` Akkordeon*:
     Als Basis-Fallback hervorragend, aber als Hauptdarstellung auf Desktop visuell weniger überzeugend als eine moderne nebeneinandergestellte Rollenleiste mit Live-Mockup. Die gewählte Radio-Tab-Lösung vereint moderne Tab-Optik mit Zero-JS-Resilienz.

---

## 2. Datenstruktur & Konfiguration in `core/produkt.py`

- **Kontext**:
  Gemäß FR-008 und AGENTS.md müssen fachliche Inhalte, Texte und Metriken von der Darstellungslogik getrennt sein. In `core/produkt.py` existieren bereits `FUNKTIONEN`, `PREISSTUFEN`, `FAQ` etc.

- **Entscheidung**:
  Einführung einer zentralen Datenstruktur `ROLLEN_SCHMERZPUNKTE` in `core/produkt.py`.
  Jeder Eintrag enthält:
  - `id`: Eindeutiger Slug (`vorstand`, `kassenwart`, `spielleiter`, `kapitaen`, `mitglieder`).
  - `titel`: Vollständiger Rollenname.
  - `kurztitel`: Kompakter Name für Buttons und Tabs.
  - `icon`: Icon-Name aus `includes/sprite.html` (`shield`, `wallet`, `trophy`, `flag`, `users`).
  - `slogan`: Markanter Kernsatz zum Schmerzpunkt.
  - `ersparnis`: Konkreter quantifizierter Nutzen (z. B. *„~15 Stunden weniger Büroarbeit pro Jahr“*).
  - `schmerzpunkte`: 3 prägnante Vorher/Nachher-Paare:
    - `problem`: Konkreter Frust im Vereinsalltag (*„Vorher: Adressen in Excel, Zahlungen im Kopf der Kassenwartin“*).
    - `loesung`: Wie die Software das löst (*„Mit Schachverwaltung: 1-Klick-Lösung, automatische Beitragsberechnung“*).
    - `detail`: Kurze Erläuterung des technischen Hintergrunds.
  - `vorschau`: Konfigurationsdaten für das interaktive Mockup:
    - `typ`: Simulator-Typ (`dashboard`, `sepa`, `turnier`, `aufstellung`, `dsgvo`).
    - `titel`: Fenstertitel der App-Simulation.
    - `metriken`: 3 statische/dynamische KPI-Badges.
    - `elemente`: Liste simulierter Datensätze (z. B. Partien, Buchungen, Mahnungen).
    - `schalter`: Interaktive Knöpfe (z. B. Stufe 1, 2, 3 oder Runde 1, 2).

- **Vorteile**:
  - Änderungen an Texten oder Schmerzpunkten erfordern keine HTML-/CSS-Änderungen.
  - Vollständige Testbarkeit via Unit-Tests (`assertIn`, Feld-Vollständigkeit).
  - Klare Trennung von Content und Presentation.

---

## 3. Visuelles Design & Responsive-Strategie

- **Kontext**:
  AGENTS.md verlangt strikt:
  - Kein horizontaler Overflow bei 360 px (Mobil) und 1280 px (Desktop).
  - Integration in bestehende Designsprache (`landing.css`, `app.css`).
  - Einhaltung der Barrierefreiheit (WCAG 2.1 AA Kontrast).

- **Entscheidung**:
  1. **Layout-Raster**:
     - Desktop ($\ge 64$rem / 1024px): 2-spaltiges Grid: Links Rollen-Tabs, Schmerzpunkte & Lösungen; rechts das interaktive Live-Mockup im App-Fensterstil (`.lp-mock`).
     - Tablet ($\ge 48$rem / 768px): Vertikal gestapelt mit horizontaler Tab-Leiste.
     - Mobil ($\le 48$rem / < 768px): Horizontale, touch-freundliche Tab-Leiste mit `overflow-x: auto` und weichem Scroll-Snap. Schmerzpunkte als Vorher/Nachher-Karten. Mockup passt sich per relativer Breiten (`100%`, `max-width`) ohne Overflow an.
  2. **Interaktives Mockup Styling**:
     - Nutzt das etablierte `.lp-mock`-Design aus `landing.css` (Browser-/Fensterleiste mit 3 Punkten, Status-Badges, Listen-Look wie das echte Dashboard).
     - Farbleitsystem:
       - Problem / Frust: Subtiles Rot/Ocker (`var(--danger-soft, #fdf2f2)`, `border: 1px solid #fecaca`, rotes Icon).
       - Lösung / Schachverwaltung: Sattes Vereinsgrün & Smaragd (`var(--success-soft, #ecfdf5)`, `border: 1px solid #a7f3d0`, grüner Haken).
       - Highlight & Akzente: Gold (`var(--gold, #b88d3b)`).

---

## 4. Teststrategie (AGENTS.md & PRD)

- **Kontext**:
  Jede Task benötigt Negativtests und Rollen-Tests.
- **Entscheidung**:
  1. **Unit-Tests (`core/tests/test_produkt.py`)**:
     - Vollständigkeitstest für alle 5 Rollen in `ROLLEN_SCHMERZPUNKTE` (alle Pflichtfelder: `id`, `titel`, `icon`, `ersparnis`, `schmerzpunkte`, `vorschau`).
     - Konsistenztest: Jeder Schmerzpunkt hat Problem und Lösung.
     - Rendering-Test: Alle Rollen und Schmerzpunkte werden auf `/` gerendert.
     - Negativ-Test: Ungültige Rollen oder fehlende Felder führen nicht zum Template-Absturz.
     - Sicherheits-Test: Keine `<script>`-Tags, keine externen URLs (0 Tracker, 0 CDNs).
  2. **Automatisierte Layout- & Overflow-Prüfung**:
     - Überprüfung der Viewport-Meta-Tags und CSS-Regeln (`box-sizing: border-box`, `max-width: 100%`, kein statisches `width: > 360px`).
