# Tasks: Schmerzpunkte, Lösungen & Interaktive Vorschau auf /produkt

**Input**: Design documents from `specs/003-produkt-schmerzpunkte-vorschau/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/ui-contract.md`, `quickstart.md`)  
**Status**: Ready for Implementation  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Grundgerüst für die modularen Daten und View-Integration bereitstellen.

- [X] T001 Konstanten-Grundgerüst für `ROLLEN_SCHMERZPUNKTE` in `core/produkt.py` anlegen
- [X] T002 Kontext-Übergabe von `rollen_schmerzpunkte` in `core/views.py` (`produkt_seite`) einbinden

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Test-Infrastruktur und CSS-Basisklassen, die von allen User Stories benötigt werden.

**⚠️ CRITICAL**: Keine User-Story-Arbeit kann beginnen, bevor diese Basis bereitsteht.

- [X] T003 [P] Datenintegritäts- und Negativ-Tests für `ROLLEN_SCHMERZPUNKTE` in `core/tests/test_produkt.py` schreiben (Validierung aller Pflichtfelder `id`, `titel`, `icon`, `ersparnis`, `schmerzpunkte`, `vorschau` sowie Negativ-Test auf fehlerhafte Daten)
- [X] T004 [P] Basis-Layoutklassen für die Schmerzpunkte-Sektion in `static/css/landing.css` anlegen (`.lp-pains-showcase`, `.lp-role-selector`, `.lp-role-tab`, `.lp-role-panel`, `.lp-panel-grid`)

**Checkpoint**: Basis gelegt – User-Story-Implementierung kann nun starten.

---

## Phase 3: User Story 1 - Rollenbasierter Schmerzpunkte- und Lösungskatalog (Priority: P1) 🎯 MVP

**Goal**: Besucher können zwischen 5 zentralen Vereinsrollen wählen und sehen für jede Rolle typische Schmerzpunkte („Vorher“) und Software-Lösungen („Mit Schachverwaltung“).

**Independent Test**: Aufruf von `/produkt/` oder `/` mit Marketing-Einstellung; Klick auf die 5 Rollen; Verifikation der korrespondierenden Problem- und Lösungsbeschreibungen.

### Tests for User Story 1 🧪
- [X] T005 [P] [US1] Rendering- und Negativ-Tests für alle 5 Rollen und Schmerzpunkte in `core/tests/test_produkt.py` erstellen (stellt sicher, dass alle 5 Rollen im DOM gerendert werden und keine Template-Syntaxfehler auftreten)

### Implementation for User Story 1
- [X] T006 [P] [US1] Vollständige Inhalte für alle 5 Rollen (`vorstand`, `kassenwart`, `spielleiter`, `kapitaen`, `mitglieder`) mit je mindestens 3 konkreten Schmerzpunkten und Lösungen in `core/produkt.py` hinterlegen
- [X] T007 [US1] Schmerzpunkte-Sektion `#loesungen` mit CSS-Radio-Tab-Leiste und Vorher/Nachher-Karten in `core/templates/core/produkt.html` einbauen
- [X] T008 [US1] Styling der Vorher/Nachher-Gegenüberstellung („Vorher“ gedämpft/rot, „Mit Schachverwaltung“ grün/hervorgehoben) in `static/css/landing.css` umsetzen

**Checkpoint**: User Story 1 ist eigenständig lauffähig und demonstrierbar (MVP erreicht).

---

## Phase 4: User Story 2 - Interaktive Vorschau-Komponente (Live-Simulator) (Priority: P1)

**Goal**: Zu jeder gewählten Rolle zeigt ein interaktives App-Mockup typische Arbeitsabläufe (SEPA-Lauf, Schweizer System, Aufstellungsprüfung, DSGVO-Auskunft) mit interaktiven Schaltern ohne Backend-Last.

**Independent Test**: Klick auf die Vorschau-Schalter (z. B. Mahnstufen 1–3 bei Kassenwart, Runden 1–2 bei Spielleiter) im Mockup; sofortige reaktive UI-Aktualisierung im Browser.

### Tests for User Story 2 🧪
- [X] T009 [P] [US2] Tests für die Vorschau-Mockup-Struktur und interaktive Schaltelemente in `core/tests/test_produkt.py` schreiben

### Implementation for User Story 2
- [X] T010 [P] [US2] Mockup-Konfigurationen (`metriken`, `zeilen`, `aktionen`) für alle 5 Rollen in `core/produkt.py` definieren
- [X] T011 [US2] Interaktives Mockup-Fenster (`.lp-mock-interactive`) mit Titelleiste, Kennzahlen-Kacheln und schaltbaren Ansichten in `core/templates/core/produkt.html` integrieren
- [X] T012 [US2] CSS-Regeln für interaktive Schaltzustände innerhalb des Mockups in `static/css/landing.css` implementieren

**Checkpoint**: User Stories 1 und 2 greifen nahtlos ineinander – Schmerzpunkte links, interaktive Lösung rechts.

---

## Phase 5: User Story 3 - Vorher/Nachher-Effizienzrechner & Zeiteinsparung (Priority: P2)

**Goal**: Quantifizierte Zeit- und Nervenersparnis-Plaketten je Rolle sowie ein Gesamtersparnis-Banner für den gesamten Verein.

**Independent Test**: Überprüfung der Ersparnis-Badges („~15 Stunden pro Beitragslauf“) pro Rolle und des aggregierten Banners („Bis zu 80 Stunden Büroarbeit gespart“).

### Tests for User Story 3 🧪
- [X] T013 [P] [US3] Test für die korrekte Anzeige der Zeiteinsparungs-Badges und des Ersparnis-Banners in `core/tests/test_produkt.py` hinzufügen

### Implementation for User Story 3
- [X] T014 [US3] Zeiteinsparungs-Badges je Rolle und Gesamtersparnis-Banner in `core/templates/core/produkt.html` einfügen
- [X] T015 [US3] Styling für Zeiteinsparungs-Badges (`.lp-time-badge`, Gold-Akzente) in `static/css/landing.css` ergänzen

**Checkpoint**: Der wirtschaftliche und ehrenamtliche Nutzen ist auf einen Blick quantifiziert.

---

## Phase 6: User Story 4 - Barrierefreiheit, Tastaturbedienung & Mobile Responsiveness (Priority: P2)

**Goal**: Barrierefreie WAI-ARIA-Semantik, vollständige Tastatur-Navigation, Responsive Darstellung bei 360 px und 1280 px ohne horizontalen Overflow sowie sauberes Progressive-Enhancement ohne JavaScript.

**Independent Test**: Test der Seite bei 360 px und 1280 px; Überprüfung der Tastaturbedienung mit `Tab` und Pfeiltasten; Deaktivierung von JavaScript im Browser.

### Tests for User Story 4 🧪
- [X] T016 [P] [US4] Tests für CSP-Konformität (keine Inline-Skripte) und Barrierefreiheits-Attribute in `core/tests/test_produkt.py` schreiben

### Implementation for User Story 4
- [X] T017 [US4] WAI-ARIA-Attribute (`role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-selected`, `aria-controls`) und Fokus-Stile (`:focus-visible`) in `core/templates/core/produkt.html` und `static/css/landing.css` absichern
- [X] T018 [US4] Mobile Optimierung (horizontales wischbares Tab-Band mit `overflow-x: auto`, kein Layout-Overflow) für Viewports ab 360 px in `static/css/landing.css` umsetzen

**Checkpoint**: Vollständige mobile Perfektion und Barrierefreiheit ohne Fremdbibliotheken.

---

## Phase 7: User Story 5 - Kontextbezogene Demo-Anfrage mit Rollen-Fokus (Priority: P3)

**Goal**: Jeder Rollenbereich bietet eine direkte 1-Klick-Demoanfrage mit vorausgefülltem Schwerpunkt im Betreff.

**Independent Test**: Klick auf „Demo anfragen“ unter einer Rolle erzeugt den Link `mailto:...&subject=Demo-Anfrage%20Schwerpunkt%20[Rolle]`.

### Tests for User Story 5 🧪
- [X] T019 [P] [US5] Test für die Generierung rollenspezifischer Demo-Links in `core/tests/test_produkt.py` erstellen

### Implementation for User Story 5
- [X] T020 [US5] Kontextuelle Aktions-Buttons mit vorausgefülltem `mailto`-Betreff je Rolle in `core/templates/core/produkt.html` einbinden

**Checkpoint**: Vollständiger Konvertierungstrichter vom Schmerzpunkt direkt zur Demo-Anfrage.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verifikation, Dokumentation und abschließende Qualitätskontrolle.

- [X] T021 [P] Gesamte Test-Suite mit `docker compose exec app pytest core/tests/test_produkt.py` ausführen und Dokumentation in `docs/` nachziehen
- [X] T022 Manuellen/automatisierten Browser-Check bei 360 px und 1280 px auf horizontalen Overflow durchführen (`scrollWidth <= clientWidth`)

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1: Setup (T001, T002)
   │
   ▼
Phase 2: Foundational (T003, T004) [BLOCKIERT ALLE STORIES]
   │
   ├───────────────────────────────┐
   ▼                               ▼
Phase 3: User Story 1 (P1)     Phase 4: User Story 2 (P1)
(T005 ─► T006, T007, T008)     (T009 ─► T010, T011, T012)
   │                               │
   └───────────────┬───────────────┘
                   ▼
         Phase 5: User Story 3 (P2) (T013 ─► T014, T015)
                   │
                   ▼
         Phase 6: User Story 4 (P2) (T016 ─► T017, T018)
                   │
                   ▼
         Phase 7: User Story 5 (P3) (T019 ─► T020)
                   │
                   ▼
         Phase 8: Polish (T021, T022)
```

### Parallel Opportunities

- **Setup & Foundation**: T003 und T004 können parallel bearbeitet werden.
- **Innerhalb User Story 1**: T005 (Tests) und T006 (Datenformulierung) können parallel bearbeitet werden.
- **User Story 1 & User Story 2**: Nach Phase 2 können US1 (Schmerzpunkte) und US2 (Mockup-Daten) parallel entwickelt werden.
- **Tests**: Alle mit `[P]` gekennzeichneten Test-Tasks laufen unabhängig voneinander.

---

## Implementation Strategy

### MVP First (User Story 1 & 2)

1. Phase 1 (Setup: T001, T002) abschließen.
2. Phase 2 (Foundational: T003, T004) abschließen.
3. Phase 3 & 4 (User Story 1 & 2: T005–T012) implementieren.
4. **STOP & VALIDATE**: Testen, dass Schmerzpunkte und interaktive Vorschau im Browser perfekt harmonieren.
5. Inkrementell Phase 5 (Zeitersparnis), Phase 6 (A11y/Mobile) und Phase 7 (CTA) ergänzen.
