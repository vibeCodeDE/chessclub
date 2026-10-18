# Feature Specification: Saisonverwaltung für den Vereinsvorstand (z. B. 2026/2027)

**Feature Branch**: `004-saison-verwaltung`

**Created**: 2026-10-17

**Status**: Specified

**Input**: User description: "Saison verwaltung z.b. 2026/2027 für den Vorstand"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Saisons anlegen, konfigurieren & aktive Saison steuern (Priority: P1)

Der Vorstand (1. Vorsitzender, Spielleiter oder Admin) benötigt eine zentrale Übersicht und Steuerung aller Spielzeiten des Vereins. In der Saisonverwaltung kann er eine neue Saison (z. B. „2026/2027“) mit Startdatum (z. B. 01.07.2026 oder 01.08.2026) und Enddatum (z. B. 30.06.2027 oder 31.07.2027) anlegen. Das System schlägt dabei automatisch die passenden Standardzeiträume nach den Regularien der Schachverbände vor. 
Der Vorstand deklariert genau eine Saison als „aktive Hauptsaison“. Diese fungiert im gesamten System (Dashboard, Spielbetrieb, Turniere) als Standard-Filter für alle Mitglieder und Funktionäre. Über einen leicht erreichbaren Saison-Umschalter im Kopfbereich oder in den Bereichsfiltern kann der Vorstand jederzeit zwischen der aktuellen Saison, vergangenen Spielzeiten und bereits in Planung befindlichen Folgesaisons wechseln.

**Why this priority**: Das Fundament des organisierten Schachsports ist die Einteilung in Spielzeiten. Ohne eine saubere Saisonstruktur vermischen sich Spielpläne, Aufstellungen und Bilanzen verschiedener Jahre. Die Definition der aktiven Saison schafft Klarheit für den laufenden Spielbetrieb.

**Independent Test**: Der Vorstand legt eine neue Saison „2026/2027“ mit Beginn zum 01.08.2026 und Ende zum 31.07.2027 an und setzt sie als aktive Saison. Das System speichert die Saison, visualisiert sie als aktiv und übernimmt sie sofort als Standardauswahl in den Modulen.

**Acceptance Scenarios**:

1. **Given** ein angemeldeter Vorstand in der Saisonverwaltung, **When** er auf „Neue Saison anlegen“ klickt, **Then** öffnet sich eine Eingabemaske mit Vorbelegung für das nächste logische Spieljahr (z. B. Bezeichnung „2026/2027“, Start 01.08.2026, Ende 31.07.2027).
2. **Given** valide Angaben für Name, Start- und Enddatum, **When** der Vorstand das Formular speichert, **Then** wird die Saison angelegt und in der chronologischen Saisonübersicht aufgeführt.
3. **Given** mehrere angelegte Saisons, **When** der Vorstand für eine Saison die Aktion „Als aktive Saison festlegen“ wählt, **Then** wird diese Saison als aktuelle Hauptsaison markiert und alle team- und spielbezogenen Übersichten filtern standardmäßig auf diesen Zeitraum.
4. **Given** ein Benutzer auf einer Übersichtsseite (z. B. Spielbetrieb), **When** er den Saison-Filter von „2026/2027“ auf „2025/2026“ umstellt, **Then** aktualisieren sich die angezeigten Daten ohne Seitenabbruch auf die historische Saison.

---

### User Story 2 - Saisonbezogener Spielbetrieb & Historienfilter (Priority: P1)

Mannschaften, Ligaspiele, Spielberichte und Aufstellungen sind fest an eine bestimmte Saison gekoppelt. Wenn Funktionäre oder Vereinsmitglieder den Bereich „Spielbetrieb“ aufrufen, sehen sie standardmäßig ausschließlich die Mannschaften und Begegnungen der aktiven Saison. 
Möchte ein Mannschaftsführer oder Mitglied vergangene Erfolge oder alte Paarungen einsehen, wählt er einfach die gewünschte historische Saison im Filter aus. Das System präsentiert daraufhin den vollständigen, unveränderten Zustand jener Spielzeit inklusive Abschlusstabellen, Brettpunkten und Einzelergebnissen im Lesemodus.

**Why this priority**: Ligen, Staffeleinteilungen und Aufstellungen ändern sich von Jahr zu Jahr (Auf- und Abstiege, wechselnde Gegner, neue Brettanzahlen). Eine strikte saisonale Trennung garantiert saubere Statistiken und verhindert, dass alte Ergebnisse überschrieben werden.

**Independent Test**: Für Saison 2025/2026 existieren 3 Mannschaften mit abgeschlossenen Spielen. In Saison 2026/2027 wird eine 4. Mannschaft hinzugefügt. Beim Filtern nach 2025/2026 werden exakt 3 Teams mit ihren alten Bilanzen angezeigt; beim Filtern nach 2026/2027 werden die Teams der neuen Saison dargestellt.

**Acceptance Scenarios**:

1. **Given** die aktive Saison ist „2026/2027“, **When** ein Mitglied die Seite „Spielbetrieb“ aufruft, **Then** werden ausschließlich Mannschaften und Ligaspiele angezeigt, die der Saison 2026/2027 zugeordnet sind.
2. **Given** ein Vorstand ruft eine Mannschaft der Saison 2026/2027 auf, **When** er ein neues Ligaspiel plant, **Then** ist das Spieldatum auf das Zeitfenster der Saison validiert (z. B. zwischen 01.08.2026 und 31.07.2027).
3. **Given** eine historische Saison „2024/2025“, **When** ein Nutzer diese Saison im Filter anwählt, **Then** werden alle damaligen Begegnungen, Aufstellungen und Brettpunkte korrekt und schreibgeschützt wiedergegeben.

---

### User Story 3 - Geführter Saisonwechsel & Mannschaftsübernahme (Rollover) (Priority: P2)

Am Ende einer Spielzeit bereitet der Vorstand die nächste Saison vor. Das System bietet einen intuitiven „Saisonwechsel-Assistenten“ (Rollover), der es erspart, alle Mannschaften, Ligen und Einstellungen für das neue Spieljahr manuell von Grund auf neu einzutippen.
Der Assistent listet alle Mannschaften der aktuellen Saison auf. Der Vorstand kann für jedes Team per Checkbox entscheiden, ob es übernommen wird, und direkt notwendige Anpassungen vornehmen (z. B. Aufstieg der 1. Mannschaft in die „Verbandsliga“, Anpassung der Brettanzahl oder Wechsel des Mannschaftsführers). Die alten Ligaspiele und Spielberichte verbleiben unberührt im Archiv der Vorsaison, während die neue Saison mit frischen Teams und leerem Spielplan startklar ist.

**Why this priority**: Der Saisonübergang im Sommer ist eine der arbeitsintensivsten Phasen für ehrenamtliche Vorstände. Ein 1-Klick-Übernahme-Workflow spart Stunden an repetitiver Dateneingabe und verhindert Inkonsistenzen.

**Independent Test**: Der Vorstand startet den Saisonwechsel von 2025/2026 zu 2026/2027. Er übernimmt die 1. und 2. Mannschaft, ändert für Team 1 die Liga auf „Oberliga“ und lässt ein Jugendteam pausieren. Nach Bestätigung existieren in 2026/2027 genau die zwei übernommenen Teams mit den neuen Einstellungen und leerem Spielplan; 2025/2026 bleibt unverändert erhalten.

**Acceptance Scenarios**:

1. **Given** eine angelegte Folgesaison „2026/2027“, **When** der Vorstand den Saisonwechsel-Assistenten aufruft, **Then** werden alle Teams der Vorsaison mit ihrer bisherigen Liga, Brettanzahl und Mannschaftsleitung zur Übernahme vorgeschlagen.
2. **Given** die Vorschlagsliste, **When** der Vorstand bei Team 1 die Liga auf „Verbandsliga Nord“ ändert und ein nicht mehr antretendes Team abwählt, **Then** werden nur die ausgewählten Teams mit den modifizierten Attributen in die neue Saison übertragen.
3. **Given** die Bestätigung der Übernahme, **When** der Vorgang abgeschlossen ist, **Then** sind die neuen Mannschaften sofort in der Saison 2026/2027 verfügbar, ohne dass historische Spielpläne oder Bilanzen der Vorsaison dupliziert oder beschädigt werden.

---

### User Story 4 - Vereinsturniere nach Saison gliedern (Priority: P2)

Der Turnierleiter und der Vorstand organisieren regelmäßig wiederkehrende Vereinsturniere (z. B. Vereinsmeisterschaft, Vereinspokal, Blitz-Grand-Prix). In der Turnierverwaltung kann jedes Vereinsturnier einer Saison zugeordnet werden. 
Im öffentlichen sowie internen Turnierarchiv können Mitglieder und Besucher gezielt nach Saison filtern (z. B. „Wer wurde Vereinsmeister 2025/2026?“). Turniere ohne feste Saisonzugehörigkeit (z. B. offene Sommerturniere oder Jubiläums-Events) können optional saisonunabhängig geführt werden.

**Why this priority**: Schachvereine leben von ihrer Tradition und sportlichen Chronik. Die saubere Zuordnung von Vereinsturnieren zu Spielzeiten ermöglicht eine lückenlose Vereinshistorie und verhindert Verwechslungen bei jährlich wiederkehrenden Turniertiteln.

**Independent Test**: Der Spielleiter erstellt das Turnier „Vereinsmeisterschaft 2026/2027“ und ordnet es der Saison 2026/2027 zu. Im Turnierarchiv filtert ein Mitglied nach „2026/2027“ und sieht exakt dieses Turnier; beim Wechsel auf „2025/2026“ erscheint die Vorjahresmeisterschaft.

**Acceptance Scenarios**:

1. **Given** die Turnieranlage, **When** der Turnierleiter ein Turnier erfasst, **Then** steht ein Auswahlfeld „Saison“ bereit, das standardmäßig die aktive Saison vorauswählt.
2. **Given** ein Turnier mit Saisonzugehörigkeit, **When** das Turnierarchiv geöffnet wird, **Then** kann die Übersicht über ein Saison-Dropdown gefiltert werden.
3. **Given** die öffentliche Vereinsseite oder das Mitgliederportal, **When** historische Siegerlisten aufgerufen werden, **Then** sind die Turniere chronologisch nach Spielzeiten gruppiert.

---

### User Story 5 - Saisonabschluss, Schreibschutz & Revisionssicherheit (Priority: P3)

Wenn alle Wettkämpfe und Turniere einer Spielzeit ausgetragen sind, kann der Vorstand die Saison offiziell abschließen und archivieren (`Status: Archiviert`). Vor dem Abschluss führt das System einen automatischen Konsistenz-Check durch (z. B. Prüfung auf noch offene, ungespielte Ligabegegnungen oder unvollständige Brettpunkte).
Eine archivierte Saison erhält einen wirksamen Schreibschutz: Spielberichte, Aufstellungen und Rundenergebnisse können nicht mehr versehentlich editiert oder gelöscht werden. Falls im Ausnahmefall eine nachträgliche Verbandskorrektur nötig ist, kann ein Administrator die Saison mit expliziter Begründung temporär entsperren, was revisionssicher protokolliert wird.

**Why this priority**: Schützt die historische Datenintegrität des Vereins. Ein versehentlicher Klick in alten Spielberichten darf nicht unbemerkt die Vereinschronik oder Spielberechtigungs-Statistiken verfälschen.

**Independent Test**: Der Vorstand schließt die Saison 2025/2026 ab. Das System wechselt den Status auf „Archiviert“. Ein Versuch eines Mannschaftsführers, eine alte Aufstellung in dieser Saison zu bearbeiten, wird unterbunden.

**Acceptance Scenarios**:

1. **Given** eine laufende Saison mit beendeten Spielen, **When** der Vorstand auf „Saison abschließen“ klickt, **Then** prüft das System offene Termine und zeigt eine Zusammenfassung (Anzahl absolvierte Spiele, Meistertitel/Bilanzen) zur Bestätigung an.
2. **Given** eine archivierte Saison, **When** ein Mannschaftsführer oder Admin eine Aufstellung oder ein Ergebnis dieser Saison aufruft, **Then** sind alle Eingabefelder deaktiviert und ein Hinweisbanner informiert über den Archivstatus.
3. **Given** eine archivierte Saison, **When** ein Administrator die Saison über eine gesicherte Aktion entsperrt, **Then** wird diese Entsperrung mit Zeitstempel und Begründung im Audit-Log dokumentiert.

---

### Edge Cases

- **Parallele Vorbereitung der neuen Saison bei laufendem Spielbetrieb**: Oft plant der Vorstand die neue Saison (z. B. 2026/2027) bereits im Mai/Juni, während die laufende Saison 2025/2026 noch bis Juli aktiv ist. Das System unterstützt die Koexistenz beliebig vieler Saisons im Status „In Vorbereitung“, ohne dass die aktive Hauptsaison vorzeitig umgeschaltet werden muss.
- **Ungültige oder überlappende Zeiträume**: Das Enddatum einer Saison darf nicht vor oder am Startdatum liegen. Das System validiert Datumsbereiche und warnt verständlich, falls sich Saisondaten überschneiden.
- **Eindeutigkeit des Saisonnamens**: Der Name einer Saison (z. B. „2026/2027“) muss eindeutig sein, um Verwechslungen in Auswertungen und Menüs auszuschließen.
- **Löschschutz bei verknüpften Datensätzen**: Eine Saison, der bereits Mannschaften, Begegnungen, Spielberichte oder Turniere zugeordnet sind, darf unter keinen Umständen gelöscht werden (Schutz vor Kaskadenverlust). Es ist ausschließlich eine Archivierung zulässig. Lediglich versehentlich erstellte, völlig leere Saisons dürfen gelöscht werden.
- **Erstmigration auf bestehenden Systemen**: Existieren im System bereits Mannschaften oder Begegnungen aus früheren Tasks ohne explizite Saisonzugehörigkeit, ordnet ein automatischer Migrationsschritt diese Daten rückwirkend einer initialen Standardsaison (z. B. der aktuellen Spielzeit) zu, sodass keine verwaisten Daten entstehen.
- **Klare Abgrenzung zum Beitrags- und Geschäftsjahr**: Im Schachverein laufen Spielsaisons typischerweise von Spätsommer bis Frühsommer (z. B. 01.08.2026 bis 31.07.2027), während das Beitrags- und Kassenbuchwesen an das steuerliche Kalenderjahr (01.01. bis 31.12. gem. PRD §3.2 und §3.6) gebunden ist. Das System trennt diese Domänen strikt, damit SEPA-Beitragsläufe und GoBD-Kassenberichte nicht mit dem sportlichen Saisonwechsel kollidieren.
- **Rechteprüfung**: Nur Mitglieder mit Vorstands-/Administratorrechten (`@role_required(ADMIN_GROUP)`) haben Zugriff auf das Anlegen, Bearbeiten, Aktivieren und Archivieren von Saisons. Mannschaftsführer und reguläre Mitglieder besitzen reine Leserechte auf die jeweiligen Saisondaten.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Das System MUSS dem Vorstand eine zentrale Übersichts- und Verwaltungsansicht für Saisons bereitstellen (`/saison/` bzw. integriert im Vorstandsbereich).
- **FR-002**: Das System MUSS die Neuanlage und Bearbeitung von Saisons mit den Attributen Name (z. B. „2026/2027“), Startdatum, Enddatum, Status („In Vorbereitung“, „Aktiv“, „Archiviert“) und optionalem Notizfeld ermöglichen.
- **FR-003**: Das System MUSS bei der Neuanlage einer Saison automatisch das nächste reguläre Spieljahr mit Standard-Datumsbereichen (Start: 01.08., Ende: 31.07. des Folgejahres) als vorausgefüllten Standard vorschlagen.
- **FR-004**: Das System MUSS sicherstellen, dass stets genau eine Saison als „aktive Hauptsaison“ gekennzeichnet ist, die systemweit als Standardfilter für Spielbetrieb, Aufstellungen und Dashboards dient.
- **FR-005**: Das System MUSS dem Vorstand erlauben, die aktive Hauptsaison per Ein-Klick-Aktion auf eine andere definierte Saison umzuschalten.
- **FR-006**: Das System MUSS in den Bereichen Spielbetrieb, Mannschaften und Turniere ein einheitliches Saison-Auswahlelement (Dropdown/Filter) bereitstellen, über das Benutzer historische oder zukünftige Saisons ansteuern können.
- **FR-007**: Das System MUSS Mannschaften (`Team`) und Ligabegegnungen (`LeagueMatch`) einer konkreten Saison zuordnen, sodass Ligazugehörigkeiten, Bilanzen und Spieltage pro Saison isoliert und historisiert bleiben.
- **FR-008**: Das System MUSS einen geführten Saisonwechsel-Assistenten (Rollover) bereitstellen, mit dem Mannschaften der aktuellen Saison ausgewählt, im Bedarfsfall in Liga oder Besetzung angepasst und als neue Team-Entitäten für die Folgesaison übernommen werden können.
- **FR-009**: Das System MUSS Vereinsturniere (`Tournament`) optional mit einer Saison verknüpfen und im Turnierarchiv die Filterung nach Saison ermöglichen.
- **FR-010**: Das System MUSS die Archivierung beendeter Saisons unterstützen und bei archivierten Saisons einen systemweiten Schreibschutz für zugehörige Spielberichte, Aufstellungen und Ergebnisse aktivieren.
- **FR-011**: Das System MUSS das Löschen einer Saison technisch blockieren, wenn dieser bereits Mannschaften, Begegnungen oder Turniere zugeordnet sind.
- **FR-012**: Sämtliche Änderungen an Saisons (Anlage, Datumsänderung, Wechsel der aktiven Saison, Archivierung, Entsperrung) MÜSSEN manipulationssicher mit Zeitstempel und ausführendem Vorstand im zentralen `AuditLog` protokolliert werden.
- **FR-013**: Alle Ansichten und Formulare der Saisonverwaltung MÜSSEN die Vorgaben von WCAG 2.1 AA erfüllen (ausreichende Kontraste ≥ 4.5:1, vollständige Tastaturfokussierbarkeit, semantische HTML-Struktur) und responsiv von 360 px (Smartphone) bis 1280 px (Desktop) ohne horizontalen Overflow nutzbar sein.

### Key Entities *(include if feature involves data)*

- **Saison (Season)**: Repräsentiert das sportliche Spieljahr des Schachvereins. Kernattribute: Name (eindeutig, z. B. „2026/2027“), Startdatum, Enddatum, Status (Vorbereitung, Aktiv, Archiviert), Ist-Aktiv-Flag (genau einmal wahr), Bemerkung, Erstellungsdatum.
- **Mannschafts-Saison-Zuordnung (Team Season Context)**: Verknüpfung der Mannschaft mit der jeweiligen Saison inklusive saisonspezifischer Liga/Klasse, Brettanzahl und Mannschaftsleitung.
- **Saison-Ligaspiel (Season League Match)**: Spieltage, Paarungen, Aufstellungen und Brettpunkte innerhalb des zeitlichen Rahmens der jeweiligen Saison.
- **Saison-Turnier (Tournament Season Association)**: Verknüpfung von Vereinsturnieren (z. B. Vereinsmeisterschaft) mit der entsprechenden Spielzeit zur Archivierung und Siegerchronik.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Der Vorstand kann eine neue Saison (z. B. „2026/2027“) im System in unter 60 Sekunden fehlerfrei anlegen und zur Bearbeitung öffnen.
- **SC-002**: Beim Saisonübergang können bis zu 6 Vereinsmannschaften über den Rollover-Assistenten in unter 2 Minuten vollständig in die neue Saison übertragen werden.
- **SC-003**: 100 % der historischen Spielergebnisse, Aufstellungen und Tabellen früherer Spielzeiten bleiben nach einem Saisonwechsel unverändert und schreibgeschützt abrufbar.
- **SC-004**: Bei 100 % der Versuche, eine Saison mit vorhandenen Spielen oder Teams zu löschen, wird die Aktion sicher abgewehrt und der Nutzer auf die Archivierungsfunktion verwiesen.
- **SC-005**: Das Filtern und Umschalten zwischen verschiedenen Saisons im Spielbetrieb erfolgt für den Anwender ohne spürbare Verzögerung (Ladezeit < 500 ms).
- **SC-006**: Sämtliche Oberflächen der Saisonverwaltung sind auf Mobilgeräten ab 360 px Breite ohne horizontalen Bildlauf und zu 100 % per Tastatur bedienbar.

## Assumptions

- **A-001**: Eine reguläre Schachsaison im Ligabetrieb erstreckt sich in der Regel über zwei Kalenderjahre von Spätsommer bis Frühsommer (z. B. 01.08.2026 bis 31.07.2027 oder 01.07.2026 bis 30.06.2027).
- **A-002**: Das Beitrags- und Finanzwesen (SEPA-Beitragsläufe, Kassenbuch gem. PRD §3.2 und §3.6) ist an das gesetzliche Kalenderjahr (01.01. bis 31.12.) gebunden und wird getrennt von der sportlichen Spielsaison geführt.
- **A-003**: Die Konfiguration von Saisons ist Vorstandsangelegenheit und streng auf die Benutzergruppe „Admin / Vorstand“ gem. Berechtigungsmatrix PRD §3.8 beschränkt.
- **A-004**: Bei bestehenden Altdaten im System wird die aktuellste vorhandene Spielzeit als initiale aktive Saison etabliert, sodass bestehende Teams und Ligaspiele nahtlos weiterfunktionieren.
- **A-005**: Das System erlaubt die parallele Vorbereitung einer kommenden Saison (z. B. Anlegen von Teams, Spielplänen und Turnieren für 2026/2027), während die aktuelle Saison (2025/2026) bis zum offiziellen Stichtag aktiv bleibt.
- **A-006**: Für den E-Mail- oder Benachrichtigungsversand gelten die bestehenden Kommunikationskanäle der Anwendung; es werden keine externen Cloud-Dienste benötigt (DSGVO-konform, N1.1).
