# Feature Specification: Schmerzpunkte, Lösungen & Interaktive Vorschau auf /produkt

**Feature Branch**: `003-produkt-schmerzpunkte-vorschau`

**Created**: 2026-10-17

**Status**: Specified

**Input**: User description: "ich möchte in /produkt die größten Schmerzpunkte eines Vereines oder Vorstand oder Funktion aufgelistet haben und wie meine App das löst (interaktive vorschau)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rollenbasierter Schmerzpunkte- und Lösungskatalog (Priority: P1)

Ein Besucher der Produkt-Landingpage (`/produkt/` bzw. Startseite `/` auf Marketing-Domains) – typischerweise ein Vereinsvorsitzender, Kassenwart, Spielleiter oder Mannschaftsführer eines Schachvereins – möchte sofort verstehen, welchen konkreten Nutzen die Software für seine spezifischen Vereinsaufgaben bietet. 
Über eine intuitive Rollen-Auswahl („1. Vorsitzender / Vorstand“, „Kassenwart / Finanzen“, „Turnierleiter / Spielleiter“, „Mannschaftsführer / Ligabetrieb“, „Mitglieder & Eltern“) kann der Besucher seine Funktion anklicken. Das System zeigt daraufhin die gravierendsten Schmerzpunkte („Vorher / Typischer Frust“) und stellt diesen direkt die Lösung der Software („Mit Schachverwaltung“) gegenüber.

**Why this priority**: Vereinsfunktionäre suchen nach Lösungen für ihre akuten Schmerzen (z. B. Kassenwart: „Beitragseinzug frisst mein Wochenende“, Mannschaftsführer: „Wer spielt Sonntag an Brett 4?“). Eine zielgerichtete, rollenbasierte Ansprache verwandelt abstrakte Funktionslisten in greifbare Mehrwerte und bildet das Fundament für die Akquise.

**Independent Test**: Ein Nutzer ruft `/produkt/` auf, klickt nacheinander auf die verschiedenen Funktionsrollen und sieht jeweils die spezifischen Frustpunkte und Software-Lösungen übersichtlich strukturiert.

**Acceptance Scenarios**:

1. **Given** ein Besucher auf der Landingpage im Bereich „Schmerzpunkte & Lösungen“, **When** die Seite geladen wird, **Then** ist standardmäßig die Vorstands- bzw. Gesamtsicht aktiv, die die typischen Übergabe- und Haftungsprobleme visualisiert.
2. **Given** die Rollenauswahl, **When** der Besucher auf „Kassenwart“ klickt, **Then** wechseln die angezeigten Schmerzpunkte sofort zu Themen wie Beitragseinzug, SEPA-XML, Mahnwesen und Kassenprüfung samt den zugehörigen Software-Lösungen.
3. **Given** die Rollenauswahl, **When** der Besucher auf „Turnierleiter“ oder „Mannschaftsführer“ klickt, **Then** werden schachspezifische Herausforderungen (Schweizer System, DWZ-Listen, Aufstellungsregeln, Spielberichtsbogen) und deren Lösung dargestellt.
4. **Given** die Ansicht eines Schmerzpunkts, **When** der Besucher den Text liest, **Then** ist klar ersichtlich getrennt: roter/gedämpfter Problembereich („Vorher / Das Problem“) und grüner/hervorgehobener Lösungsbereich („Mit Schachverwaltung / Die Lösung“).

---

### User Story 2 - Interaktive Vorschau-Komponente (Live-Simulator) (Priority: P1)

Begleitend zu den gelisteten Schmerzpunkten und Lösungen möchte der Besucher die Software direkt auf der Landingpage „anfassen“, ohne sich erst registrieren oder einloggen zu müssen. 
Die Seite bietet eine interaktive Vorschau-Komponente (Mini-App-Simulator / interaktive Vorschaukarten), die zu jeder ausgewählten Rolle einen echten, interaktiven Programmausschnitt demonstriert:
- **Kassenwart**: Interaktiver SEPA-Lauf-Simulator (Klick auf „Beitragslauf berechnen“, Umschalten zwischen Mahnstufen 1–3, Vorschau des SEPA-XML-Exports).
- **Turnierleiter**: Interaktives Auslosungs-Mockup (Schweizer System Runde 1 vs. Runde 2 per Knopfdruck auslosen, Ergebniseingabe simulieren).
- **Mannschaftsführer**: Interaktiver Aufstellungsplaner (Spieler per Klick aufstellen, automatische Ranglisten-/DWZ-Prüfung bei Ersatzgestellung).
- **Vorstand**: Interaktive 1-Klick-DSGVO-Datenauskunft und Audit-Protokoll-Ansicht.

**Why this priority**: „Show, don't tell.“ Eine interaktive Vorschau baut sofortiges Vertrauen in die intuitive Bedienung auf und beweist, dass die Software keine theoretische Spielerei ist, sondern praxiserprobtes Schachvereins-Handwerk.

**Independent Test**: Der Besucher interagiert mit der Vorschaukomponente (z. B. wechselt in der Kassenwart-Vorschau eine Mahnstufe oder schaltet im Turniermodus eine Paarung um) und sieht sofort die reaktive visuelle Rückmeldung der App-Oberfläche.

**Acceptance Scenarios**:

1. **Given** die interaktive Vorschau auf der Landingpage, **When** der Benutzer eine Rolle anwählt, **Then** passt sich die Vorschau-Box dem jeweiligen Kontext an (z. B. Kassenbuch-/Beitragsmaske bei Kassenwart, Paarungsliste bei Spielleiter).
2. **Given** die Kassenwart-Vorschau, **When** der Nutzer auf Tabs/Buttons wie „Mahnung Stufe 1“ oder „SEPA-Vorschau generieren“ klickt, **Then** aktualisiert sich das simulierte Interface nahtlos mit realistischen Beispieldaten.
3. **Given** die Spielleiter-Vorschau, **When** der Nutzer zwischen „Runde 1“ und „Runde 2“ oder Ergebnissen umschaltet, **Then** aktualisiert sich die Paarungstabelle dynamisch im Mockup.
4. **Given** die Interaktion in der Vorschau, **When** Aktionen ausgeführt werden, **Then** werden keine Daten an den Server gesendet (rein clientseitige, sichere und performante Simulation).

---

### User Story 3 - Vorher/Nachher-Effizienzrechner & Zeiteinsparung (Priority: P2)

Der Besucher möchte quantifizierbar erkennen, wie viel Zeit und ehrenamtlicher Aufwand durch den Einsatz der Software eingespart wird.
Zu jeder Rolle wird ein prägnanter Vorher/Nachher-Vergleich mit Zeitschätzungen präsentiert (z. B. „Beitragseinzug: Vorher 16 Stunden manueller Abgleich → Jetzt 15 Minuten 1-Klick-SEPA“ oder „Turnierauslosung: Vorher 45 Minuten Zettelwirtschaft zwischen den Runden → Jetzt 30 Sekunden Schweizer System“).

**Why this priority**: Viele Vorstandsentscheidungen über Vereinsausgaben scheitern daran, dass der Return on Investment (ROI) für ehrenamtliche Freizeit nicht greifbar ist. Die klare Zeiteinsparung liefert dem Vorstand die besten Argumente für die Mitgliederversammlung.

**Independent Test**: Ein Besucher betrachtet den Effizienz-Vergleich und sieht für jede Rolle die aggregierte Zeit- und Nervenersparnis pro Monat oder Jahr.

**Acceptance Scenarios**:

1. **Given** die Detailansicht einer Rolle, **When** der Nutzer die Kennzahlen betrachtet, **Then** sieht er neben den qualitativen Punkten eine prägnante Zeit- und Aufwandsersparnis-Plakette.
2. **Given** die Gesamtzusammenfassung, **When** alle Rollen betrachtet werden, **Then** fasst ein prägnanter Banner die jährliche Zeitersparnis für den gesamten Verein zusammen (z. B. „Bis zu 80 Stunden weniger Büroarbeit pro Jahr“).

---

### User Story 4 - Barrierefreiheit, Tastaturbedienung & Mobile Responsiveness (Priority: P2)

Viele Vereinsfunktionäre und Vorstände besuchen die Website über Smartphones oder Tablets (z. B. während des Vereinsabends oder von unterwegs). Zudem müssen öffentliche Seiten barrierefrei und tastaturbedienbar sein.
Die Schmerzpunkte- und Vorschaukomponente ist vollständig responsiv gestaltet (von 360 px bis 4K) und verfügt über eine standardkonforme WAI-ARIA-Implementierung (Tabs mit Pfeiltasten bedienbar, Screenreader-Unterstützung).

**Why this priority**: Eine hakelige Bedienung auf Mobilgeräten oder horizontaler Overflow schreckt Vorstände sofort ab. Gemäß AGENTS.md muss das Layout bei 360 px und 1280 px makellos ohne horizontalen Overflow funktionieren.

**Independent Test**: Test der Seite bei einer Bildschirmbreite von 360 px und 1280 px sowie reine Tastaturbedienung mit `Tab`, `ArrowLeft`, `ArrowRight`, `Enter` und `Space`.

**Acceptance Scenarios**:

1. **Given** ein Smartphone mit 360 px Bildschirmbreite, **When** der Nutzer die Schmerzpunkte-Sektion aufruft, **Then** gibt es keinen horizontalen Overflow, alle Texte brechen lesbar um und die Rollen-Auswahl lässt sich bequem per Fingerbedienung steuern.
2. **Given** ein Benutzer navigiert ausschließlich per Tastatur, **When** er die Rollen-Tabs fokussiert, **Then** kann er mit Pfeiltasten zwischen den Rollen wechseln und mit Enter/Leertaste die Auswahl aktivieren.
3. **Given** Screenreader-Nutzer, **When** die Komponente ausgelesen wird, **Then** sind semantische Rollen (`role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-selected`, `aria-controls`) korrekt gesetzt.

---

### User Story 5 - Kontextbezogene Demo-Anfrage mit Rollen-Fokus (Priority: P3)

Wenn ein Besucher von einer bestimmten Lösung überzeugt ist (z. B. als Kassenwart von der Beitragsabwicklung), möchte er mit einem einzigen Klick eine Demo anfragen, die seinen Schwerpunkt bereits berücksichtigt.
Am Fuß der interaktiven Vorschau befindet sich eine Aktionsschaltfläche „Kostenlose Demo für [Rolle] anfragen“, die eine vorausgefüllte E-Mail oder Kontaktanfrage mit dem Betreff „Demo-Anfrage: Schwerpunkt [Rollen-Titel]“ öffnet.

**Why this priority**: Verringert die Kontakthürde und ermöglicht dem Anbieter, die Demo-Präsentation exakt auf die dringlichsten Bedürfnisse des Interessenten zuzuschneiden.

**Independent Test**: Der Nutzer wählt die Rolle „Kassenwart“ aus und klickt auf „Demo anfragen“. Der generierte E-Mail-Link enthält Betreff und Vorlagentext mit dem Bezug zum Kassenwesen.

**Acceptance Scenarios**:

1. **Given** die aktivierte Rolle „Kassenwart / Finanzen“, **When** der Besucher auf „Demo für diesen Bereich anfragen“ klickt, **Then** öffnet sich der E-Mail-Client mit `mailto:info@schachverwaltung.de?subject=Demo-Anfrage%20Schwerpunkt%20Kassenwart%20%26%20Finanzen`.
2. **Given** ein Wechsel der Rolle auf „Turnierleiter“, **When** der Button betrachtet wird, **Then** passt sich die Aktionsbeschriftung und der Link-Inhalt dynamisch der neuen Rolle an.

---

### Edge Cases

- **JavaScript im Browser deaktiviert**: 
  Die Seite bleibt über Progressive Enhancement vollständig nutzbar. Ohne JavaScript werden alle Schmerzpunkte und Lösungen aller Rollen in übersichtlichen, standardkonformen `<details>`-Akkordeons oder semantischen Blöcken angezeigt. Es entsteht kein leerer Kasten oder kaputtes UI.
- **Sehr kleine Bildschirme (320px–360px)**:
  Die Rollen-Tabs werden entweder als horizontales, wischbares Tab-Band mit sichtbarem Scroll-Indikator dargestellt oder brechen um, ohne Seitenelemente abzuschneiden. Die interaktive Vorschau skaliert proportional und nutzt kompakte Schriftgrößen.
- **Sehr schneller Klickwechsel zwischen Rollen**:
  Kein Flackern, keine asynchronen Race Conditions oder doppelt eingeblendeten Panels, da der Zustandswechsel rein synchron im Client erfolgt.
- **Keine Drittanbieter-Ressourcen**:
  Es werden keinerlei externe Skripte, CDNs, Webfonts oder Tracking-Tools eingebunden (strikt DSGVO- und AGENTS.md-konform). Alle Symbole stammen aus dem vorhandenen SVG-Sprite (`includes/sprite.html`).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Das System MUSS auf der Produkt-Präsentationsseite (`/produkt/` bzw. der Einstiegsseite für Interessenten) eine dedizierte Sektion für die Schmerzpunkte von Schachvereinen und deren Lösung bereitstellen.
- **FR-002**: Das System MUSS mindestens 5 zentrale Vereinsrollen und deren Schmerzpunkte abdecken:
  1. *Vorstand / 1. Vorsitzender* (Haftung, Datenverlust bei Übergabe, DSGVO-Auskunft, Satzung)
  2. *Kassenwart / Schatzmeister* (SEPA-Lastschriften, Mahnwesen, Beitragsrückstände, Kassenprüfung)
  3. *Turnierleiter / Spielleiter* (Schweizer System, DWZ-Listen, Paarungschaos, Ergebniszettel)
  4. *Mannschaftsführer* (Aufstellungsregeln, Stamm-/Ersatzspieler, kurzfristige Absagen, Spielberichtsbogen)
  5. *Mitglieder & Eltern* (Intransparenz, Adress-/Kontoänderungen per Papier, fehlende mobile Termine)
- **FR-003**: Zu jeder Rolle MUSS die Gegenüberstellung von „Vorher (Problem / Frust)“ und „Mit Schachverwaltung (Lösung / Entlastung)“ klar verständlich visualisiert werden.
- **FR-004**: Das System MUSS eine interaktive Vorschau-Komponente bereitstellen, die das Aussehen und typische Aktionen der realen Software-Masken für die gewählte Rolle simuliert (Dashboard, SEPA/Beiträge, Turnierauslosung, Mannschaftsaufstellung).
- **FR-005**: Das System MUSS für jede Rolle eine quantifizierte Nutzen-/Zeitersparnis-Angabe darstellen (z. B. Zeiteinsparung in Stunden pro Saison).
- **FR-006**: Das System MUSS die interaktiven Zustände (aktiver Tab, Interaktion in der Vorschau) barrierefrei mit korrekter Zugänglichkeits-Semantik (Tabs, Tabpanels, Statusmeldungen) und vollständiger Tastaturnavigation unterstützen.
- **FR-007**: Das System MUSS bei deaktiviertem JavaScript eine vollständige, lesbare Fallback-Darstellung aller Schmerzpunkte und Lösungen gewährleisten (Progressive Enhancement).
- **FR-008**: Die Daten für Schmerzpunkte, Lösungen, Rollen und Vorschau-Inhalte MÜSSEN in einer zentralen Inhaltskonfiguration gepflegt werden, getrennt von Darstellungs- und Template-Code.
- **FR-009**: Das System MUSS sicherstellen, dass keinerlei externe CDNs, Web-Schriften, Tracking-Pixel oder Cookies geladen werden (DSGVO-Konformität).
- **FR-010**: Das System MUSS auf Geräten ab 360 px Bildschirmbreite und auf Desktops (1280 px+) ohne horizontalen Overflow dargestellt werden.

---

### Key Entities & Data Structures

- **RollenProfil (`RoleProfile`)**:
  - `id`: Eindeutiger Bezeichner (z. B. `vorstand`, `kassenwart`, `spielleiter`, `kapitaen`, `mitglied`).
  - `titel`: Vollständiger Rollenname (z. B. „Kassenwart & Schatzmeister“).
  - `kurztitel`: Kompakter Tab-Titel (z. B. „Kasse & Finanzen“).
  - `icon`: Name des Icons im internen SVG-Sprite (z. B. `wallet`, `trophy`, `users`, `shield`, `flag`).
  - `slogan`: Einprägsamer Kernsatz (z. B. „Schluss mit Excel-Tabellen und unbezahlten Beiträgen“).
  - `zeitersparnis`: Konkreter Nutzenwert (z. B. „~15 Stunden Ersparnis pro Beitragslauf“).
  - `schmerzpunkte`: Liste von Frust-Szenarien des Vereinsalltags (Problembeschreibung).
  - `loesungen`: Liste der korrespondierenden Software-Lösungen mit Nutzenargumentation.
  - `vorschau_daten`: Strukturierte Daten für die interaktive Mockup-Box (z. B. simulierte Kennzahlen, Beispiellisten, schaltbare Zustände).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Besucher können mit genau 1 Interaktion (Klick oder Tastendruck) die für sie relevante Vereinsfunktion wählen; der Inhalts- und Vorschauwechsel erfolgt in unter 50 Millisekunden ohne Seiten-Neuladen.
- **SC-002**: 100 % der Schmerzpunkte und Software-Lösungen sind auch bei vollständig deaktiviertem JavaScript im Browser lesbar und zugänglich.
- **SC-003**: Die gesamte Seite lädt ohne externe HTTP-Anfragen (0 externe Domains, 0 Cookies, 0 Tracker).
- **SC-004**: Das Layout weist im automatisierten und visuellen Test weder bei 360 px noch bei 1280 px Breite einen horizontalen Scrollbalken auf (`scrollWidth <= clientWidth`).
- **SC-005**: Alle interaktiven Tabs und Schaltelemente sind vollständig per Tastatur erreichbar und erfüllen den WCAG 2.1 AA Kontraststandard (> 4,5:1 für Fließtext).
- **SC-006**: Mindestens 3 verschiedene Schmerzpunkte pro Rolle werden klar benannt und durch eine direkte Funktion der App nachweislich gelöst.

---

## Assumptions

- Die interaktive Vorschau ist ein leichtgewichtiger Client-Simulator auf der Landingpage und benötigt keine Backend-Datenbank-Queries für Testdaten.
- Die Inhalte werden im bestehenden `core/produkt.py` Modul strukturiert abgelegt, analog zu den bestehenden `FUNKTIONEN`, `PREISSTUFEN` und `FAQ`.
- Das bestehende Farbschema (Grüntöne `#12281e`, `#1b3d2f`, Gold `#d4a373` / `#c89560`, Warnung/Fehler `#9e2a2b` / `#d90429`, hellgraue Hintergründe `#f4f6f5`) und die Typografie des Projekts werden nahtlos weitergeführt.
- Die Schmerzpunkte-Sektion ersetzt bzw. erweitert den bisherigen rudimentären Textabschnitt `#problem` auf der Produktseite (`core/templates/core/produkt.html`).
