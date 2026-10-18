# Implementation Tasks: Saisonverwaltung für den Vereinsvorstand (z. B. 2026/2027)

**Feature**: `004-saison-verwaltung` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Routing-Grundlagen, globaler Template-Kontext und Basis-Formulare für die Saisonverwaltung.

- [x] T001 URL-Routen für die Saisonverwaltung (`/saison/`, `/saison/neu/`, `/saison/<pk>/bearbeiten/`, `/saison/<pk>/aktivieren/`, `/saison/<pk>/abschliessen/`, `/saison/<pk>/loeschen/`, `/saison/<pk>/uebernahme/`) in `teams/urls.py` definieren und Menüeintrag „Saisonverwaltung“ in `templates/includes/navigation.html` für Administratoren (`ADMIN_GROUP`) hinterlegen.
- [x] T002 [P] Globalen Django Context-Processor `season_context` in `teams/context_processors.py` implementieren (`aktive_saison`, `alle_saisons`, `gewaehlte_saison`) und in `config/settings.py` unter `TEMPLATES[0]["OPTIONS"]["context_processors"]` registrieren.
- [x] T003 [P] Basis-Formulare `SeasonForm` (Felder: `name`, `startdatum`, `enddatum`, `notizen`, `als_aktiv_setzen`) und `SeasonRolloverForm` in `teams/forms.py` erstellen.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Datenmodelle für `Season`, Modifikation von `Team`, Datenbank-Migrationen und Admin-Registrierung.

**⚠️ CRITICAL**: Keine User Story kann umgesetzt werden, bevor diese Phase abgeschlossen ist.

- [x] T004 Neues Datenmodell `Season` in `teams/models.py` definieren mit Feldern: `name` (CharField(50), unique=True, verbose_name="Saison"), `slug` (SlugField(60), unique=True), `startdatum` (DateField, verbose_name="Startdatum"), `enddatum` (DateField, verbose_name="Enddatum"), `status` (CharField(20), choices: `vorbereitung`="In Vorbereitung", `aktiv`="Aktiv", `archiviert`="Archiviert", default="vorbereitung"), `ist_aktiv` (BooleanField, default=False, verbose_name="Aktive Hauptsaison"), `notizen` (TextField, blank=True), `erstellt_am` (DateTimeField, auto_now_add=True), `clean()` zur Validierung von `startdatum < enddatum`, sowie Methoden `get_aktive_saison()` und Property `ist_archiviert`.
- [x] T005 Modellerweiterung `Team` in `teams/models.py`: Feld `saison = models.ForeignKey(Season, on_delete=models.PROTECT, related_name="teams", verbose_name="Saison")` hinzufügen, globales `unique=True` auf `name` entfernen und durch `UniqueConstraint(fields=["name", "saison"], name="unique_team_per_saison")` ersetzen.
- [x] T006 Dreistufige Django-Migration für `Season` und `Team.saison` in `teams/migrations/` anlegen: (1) Schema-Migration für Tabelle `Season` und nullable `Team.saison`, (2) Datenmigration zur automatischen Erstellung einer initialen Saison (z. B. "2025/2026") und Zuweisung zu allen Bestandsteams, (3) Schema-Migration für `null=False` auf `Team.saison` und Aktivierung des `UniqueConstraint`.
- [x] T007 [P] Django-Admin-Klasse `SeasonAdmin` mit Spalten `name`, `startdatum`, `enddatum`, `status`, `ist_aktiv`, `anzahl_teams`, Schnellfiltern und schreibgeschützten Zeitstempeln in `teams/admin.py` registrieren.
- [x] T008 [P] Modellerweiterung in `tournaments/models.py`: Feld `saison = models.ForeignKey("teams.Season", on_delete=models.SET_NULL, null=True, blank=True, related_name="turniere", verbose_name="Saison")` hinzufügen und Schema-Migration in `tournaments/migrations/` erstellen.

**Checkpoint**: Datenmodelle und Migrationen bereit – User-Story-Umsetzung kann beginnen.

---

## Phase 3: User Story 1 - Saisons anlegen, konfigurieren & aktive Saison steuern (Priority: P1) 🎯 MVP

**Goal**: Der Vorstand kann neue Saisons (z. B. `2026/2027`) anlegen, bestehende bearbeiten und eine Saison atomar als aktive Hauptsaison für das gesamte System deklarieren.

**Independent Test**: Vorstand legt Saison `2026/2027` (01.08.2026–31.07.2027) an und setzt sie als aktive Hauptsaison; alle anderen Saisons verlieren `ist_aktiv=True`; Negativtest: 403 für Gast/Mitglied/Kapitän, Datumsvalidierung (Start >= Ende) wird abgewiesen; Revisionssicherheit im `AuditLog` bestätigt.

### Tests für User Story 1 🧪
- [x] T009 [P] [US1] Unit-, Rollen- und Negativtests für Saison-CRUD und Hauptsaison-Aktivierung in `teams/tests/test_season.py` schreiben (Negativtests: HTTP 403 für Gast, Mitglied, Kapitän; Formular-Validierungsfehler bei `startdatum >= enddatum` oder Namensdopplung; atomare Umschaltung von `ist_aktiv` via `transaction.atomic`; AuditLog-Prüfung).

### Implementation für User Story 1
- [x] T010 [US1] Reine Service-Funktionen `create_season` und `set_active_season` mit atomarer Transaktion (`transaction.atomic`) und `AuditLog`-Dokumentation in `teams/services.py` implementieren.
- [x] T011 [US1] Views `season_list` (GET), `season_create` (GET/POST), `season_edit` (GET/POST) und `season_activate` (POST) mit Rollenschutz `@role_required(ADMIN_GROUP)` in `teams/views.py` implementieren.
- [x] T012 [P] [US1] Templates `teams/season_list.html` (Übersicht aller Saisons mit Status-Badges, Teams-Zähler und Aktivierungs-Aktion) und `teams/season_form.html` (barrierefreie Eingabemaske nach WCAG 2.1 AA) erstellen.

**Checkpoint**: User Story 1 ist vollständig funktional und unabhängig testbar (MVP).

---

## Phase 4: User Story 2 - Saisonbezogener Spielbetrieb & Historienfilter (Priority: P1)

**Goal**: Mannschaften und Ligaspiele sind isoliert pro Saison abrufbar; der Spielbetrieb filtert standardmäßig auf die aktive Saison und erlaubt die nahtlose Anzeige historischer Spielzeiten.

**Independent Test**: Spielbetrieb zeigt bei aktiver Saison 2026/2027 nur deren Teams; Umschalten des Filters auf 2025/2026 lädt alte Teams und deren Begegnungen im Lesemodus; Negativtest: Spieldaten außerhalb des Saisonfensters werden durch ValidationError abgewiesen; Abfragebudget (`assertNumQueries`) eingehalten.

### Tests für User Story 2 🧪
- [x] T013 [P] [US2] Tests für saisonbezogenen Spielbetrieb und Filterlogik in `teams/tests/test_season_matches.py` schreiben (Negativtest: Spieldatum außerhalb von `saison.startdatum` und `saison.enddatum` wirft ValidationError; `assertNumQueries` für `team_list` und `match_list`; Umschalten via `?saison=<id>`).

### Implementation für User Story 2
- [x] T014 [US2] Validierungsfunktion `validate_match_season_bounds(match)` in `teams/services.py` implementieren und in `LeagueMatch.clean()` in `teams/models.py` einbinden.
- [x] T015 [US2] Views `team_list` und `match_list` in `teams/views.py` um Saisonfilterung via `request.GET.get("saison")` erweitern, `select_related("saison")` optimieren und N+1-Queries eliminieren.
- [x] T016 [P] [US2] Wiederverwendbare Filterkomponente `teams/templates/teams/includes/season_filter.html` erstellen und in `teams/templates/teams/team_list.html` sowie `teams/templates/teams/match_list.html` einbinden.

**Checkpoint**: User Stories 1 und 2 sind funktional und greifen nahtlos ineinander.

---

## Phase 5: User Story 3 - Geführter Saisonwechsel & Mannschaftsübernahme (Rollover) (Priority: P2)

**Goal**: Der Vorstand kann bestehende Mannschaften der Vorsaison mit 1 Klick auswählen, Liga und Besetzung anpassen und als neue Teams für die Folgesaison übernehmen.

**Independent Test**: Rollover von 2 Teams aus 2025/2026 in 2026/2027; neue Teams werden in 2026/2027 mit leerem Spielplan und neuem iCal-Token erzeugt; alte Teams in 2025/2026 bleiben mit allen Spielen unverändert erhalten; Negativtest: HTTP 403 für Nicht-Admins, Duplikatvermeidung bei Mehrfachübernahme.

### Tests für User Story 3 🧪
- [x] T017 [P] [US3] Tests für den Saison-Rollover in `teams/tests/test_season_rollover.py` schreiben (Transaktionsintegrität, Neugenerierung von `ical_token`, Unveränderlichkeit der Vorsaison-Spiele, Negativtest: HTTP 403 für unberechtigte Rollen, `AuditLog`-Dokumentation).

### Implementation für User Story 3
- [x] T018 [US3] Reine Service-Funktion `rollover_teams(source_season, target_season, teams_payload, user)` mit `transaction.atomic()` und `AuditLog`-Eintrag in `teams/services.py` implementieren.
- [x] T019 [US3] View `season_rollover` (GET/POST) mit Rollenschutz `@role_required(ADMIN_GROUP)` in `teams/views.py` implementieren.
- [x] T020 [P] [US3] Template `teams/season_rollover.html` mit Vorschautabelle aller Vorsaison-Teams, Kontrollkästchen, editierbaren Liga-Feldern und barrierefreien Fokus-Zuständen erstellen.

**Checkpoint**: Saisonwechsel-Assistent ist einsatzbereit und spart Vorständen Stunden an manueller Neueingabe.

---

## Phase 6: User Story 4 - Vereinsturniere nach Saison gliedern (Priority: P2)

**Goal**: Vereinsturniere (z. B. Vereinsmeisterschaft, Vereinspokal) können einer Saison zugeordnet und im Turnierarchiv chronologisch nach Spielzeiten gefiltert werden.

**Independent Test**: Turnier „Vereinsmeisterschaft 2026/2027“ wird Saison 2026/2027 zugewiesen; Turnierliste filtert nach Saison; Negativtest: Löschen einer Saison mit zugewiesenen Turnieren wird abgewehrt.

### Tests für User Story 4 🧪
- [x] T021 [P] [US4] Tests für saisonbezogene Vereinsturniere in `tournaments/tests/test_season_tournaments.py` schreiben (Zuordnung von Turnieren zu Saisons, Filterung im Turnierarchiv via `?saison=<id>`, Unabhängigkeit nicht-zugeordneter Turniere).

### Implementation für User Story 4
- [x] T022 [US4] Turnierformulare in `tournaments/forms.py` und Views in `tournaments/views.py` um das optionale Auswahlfeld `saison` erweitern.
- [x] T023 [P] [US4] Turnierarchiv-Template `tournaments/tournament_list.html` um die barrierefreie Saison-Filterkomponente erweitern.

**Checkpoint**: Vereinsturniere sind sauber in die Saisonhistorie integriert.

---

## Phase 7: User Story 5 - Saisonabschluss, Schreibschutz & Revisionssicherheit (Priority: P3)

**Goal**: Der Vorstand kann beendete Saisons archivieren; die Archivierung aktiviert systemweiten Schreibschutz auf alte Spielberichte und Aufstellungen; eine Löschsperre schützt belegte Saisons vor Datenverlust.

**Independent Test**: Saison mit offenen Spielen warnt beim Abschluss; nach Archivierung wirft Bearbeitung alter Spiele PermissionDenied; Löschversuch einer Saison mit Teams/Spielen wirft ProtectedError; Entsperrung/Statuswechsel wird im AuditLog protokolliert.

### Tests für User Story 5 🧪
- [x] T024 [P] [US5] Tests für Archivierung, Schreibschutz und Löschsperre in `teams/tests/test_season_archival.py` schreiben (Negativtests: PermissionDenied beim Ändern alter Aufstellungen in archivierter Saison, Blockade des Löschens bei vorhandenen Teams/Turnieren via ProtectedError, Warnung bei ungespielten Begegnungen).

### Implementation für User Story 5
- [x] T025 [US5] Service-Funktionen `archive_season`, `reopen_season` und `delete_season` in `teams/services.py` implementieren (Prüfung offener Partien, Audit-Log, ProtectedError-Handling).
- [x] T026 [US5] Views `season_archive` (POST), `season_reopen` (POST) und `season_delete` (POST) mit `@role_required(ADMIN_GROUP)` in `teams/views.py` implementieren.
- [x] T027 [US5] Schreibschutz-Prüfung `check_match_edit_allowed` in `teams/views.py` (Aufstellung, Ergebniserfassung, Absage) integrieren und Archiv-Hinweisbanner in `teams/templates/teams/match_detail.html` einbinden.

**Checkpoint**: Vollständige historische Revisionssicherheit und Schutz vor Fehlbedienung gewährleistet.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Revisionssicherheit, Barrierefreiheit, mobile Responsivität und Gesamtabnahme.

- [x] T028 [P] Audit-Log-Integration für alle Saison-Aktionen (Anlage, Aktivierung, Archivierung, Rollover) in `teams/services.py` verifizieren und mit vollständigen Parametern (`aktion`, `feld`, `alt_wert`, `neu_wert`) ausstatten.
- [x] T029 [P] Mobile Responsivitäts- und Accessibility-Prüfung (WCAG 2.1 AA) bei 360 px und 1280 px ohne horizontalen Scrollbalken für alle neuen Templates (`season_list.html`, `season_form.html`, `season_rollover.html`) durchführen.
- [x] T030 Alle 5 Validierungsszenarien aus `specs/004-saison-verwaltung/quickstart.md` durchführen und dokumentieren.
- [x] T031 Gesamte Testsuite ausführen (`docker compose exec app pytest teams/ tournaments/`) und Query-Budgets (`assertNumQueries`) verifizieren.

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Keine Abhängigkeiten – kann sofort beginnen.
- **Foundational (Phase 2)**: Hängt von Setup ab – **BLOCKIERT alle User Stories**.
- **User Stories (Phase 3 bis 7)**: Hängen alle vom Abschluss der Foundational-Phase ab.
  - US 1 (P1): Basis für Saisonverwaltung – keine Story-Abhängigkeiten.
  - US 2 (P1): Hängt logisch an US 1 (benötigt aktive Saison).
  - US 3 (P2): Hängt an US 1 & US 2 (übernimmt Teams in Ziel-Saison).
  - US 4 (P2): Hängt an US 1 (ordnet Turniere zu).
  - US 5 (P3): Hängt an US 1 & US 2 (schützt beendete Saisons).
- **Polish (Phase 8)**: Hängt vom Abschluss aller gewünschten User Stories ab.

### Within Each User Story
- Tests MÜSSEN zuerst geschrieben werden und fehlschlagen (Test-First gem. AGENTS.md).
- Reine Servicefunktionen in `teams/services.py` vor den Views implementieren.
- Dünne Function-Based Views vor den Templates erstellen.
- Story als vollständiges Inkrement vor dem nächsten Meilenstein abschließen.

---

## Parallel Execution Opportunities

- In Phase 1: T002 (Context Processor) und T003 (Forms) können parallel zu T001 laufen.
- In Phase 2: T007 (Admin) und T008 (Tournaments Model) können parallel ausgeführt werden.
- In jeder User Story: Tests ([P]) und Templates ([P]) können parallel zu Backend-Services entwickelt werden.
- User Story 3 (Rollover) und User Story 4 (Turniere) können parallel implementiert werden, sobald Phase 4 (US 2) abgeschlossen ist.

---

## Parallel Example: User Story 1

```bash
# Tests parallel anlegen:
Task: "T009 [P] [US1] Unit-, Rollen- und Negativtests in teams/tests/test_season.py"

# Template parallel vorbereiten:
Task: "T012 [P] [US1] Templates teams/season_list.html und season_form.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Phase 1 (Setup) abschließen.
2. Phase 2 (Foundational: Model, Migrationen) abschließen.
3. Phase 3 (User Story 1: Anlegen & Aktivieren) abschließen.
4. **Validieren**: Vorstand kann die Saison 2026/2027 anlegen und als aktiv schalten.

### Inkrementelle Auslieferung
1. **Inkrement 1 (MVP)**: Saisons anlegen, bearbeiten, aktivieren (US 1).
2. **Inkrement 2**: Spielbetrieb saisonal isolieren & filtern (US 2).
3. **Inkrement 3**: 1-Klick-Saisonwechsel & Rollover für Mannschaften (US 3).
4. **Inkrement 4**: Vereinsturniere nach Spielzeiten gliedern (US 4).
5. **Inkrement 5**: Archivierungssperre & Revisionssicherheit (US 5).
