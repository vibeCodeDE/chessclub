# Tasks: Onboarding für einen neuen Schachverein

**Feature**: Onboarding für einen neuen Schachverein (`002-vereins-onboarding`)  
**Input**: Design-Dokumente aus `specs/002-vereins-onboarding/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`)  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Vorbereitung der Basis-Strukturen und Konstanten für den Onboarding-Assistenten.

- [X] T001 Erstellen der Template-Verzeichnisstruktur für den Wizard in `templates/core/onboarding/base_onboarding.html`
- [X] T002 [P] Definieren der schachspezifischen Standard-Beitragskategorien `DEFAULT_FEE_CATEGORIES` (Erwachsene 72 €, Jugend 36 €, Senioren 50 €, Passiv 30 €) in `core/constants.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Grundlegende Datenmodelle und Migrationen, die vor der Implementierung der User Stories fertiggestellt sein MÜSSEN.

- [X] T003 Erweitern des Modells `ClubProfile` in `core/models.py` um das Feld `zps_nummer = models.CharField("DSB-Vereinskennziffer", max_length=10, blank=True)`
- [X] T004 Erstellen des Singleton-Modells `OnboardingProgress` in `core/models.py` mit `aktueller_schritt` (PositiveSmallIntegerField, default=1, Werte 1-6), `schritte_abgeschlossen` (JSONField, default=list), `ist_abgeschlossen` (BooleanField, default=False), `abgeschlossen_am` (DateTimeField, null=True, blank=True), `abgeschlossen_von` (ForeignKey zu settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=SET_NULL), `checklist_ausgeblendet` (BooleanField, default=False) sowie Hilfsmethoden `get_solo()` und `mark_step_completed()`
- [X] T005 Erstellen des Modells `StaffInvitation` in `core/models.py` mit `email` (EmailField, db_index=True), `vorname` (CharField, max_length=50), `nachname` (CharField, max_length=50), `rolle` (CharField, max_length=20, choices `ADMIN_GROUP` / `KAPITAEN_GROUP`), `token` (CharField, max_length=64, unique=True, db_index=True), `status` (CharField, max_length=20, default="offen"), `gueltig_bis` (DateTimeField, db_index=True), `erstellt_am` (DateTimeField, auto_now_add=True), `angenommen_am` (DateTimeField, null=True, blank=True), `eingeladen_von` (ForeignKey zu settings.AUTH_USER_MODEL, on_delete=CASCADE) und `benutzer` (OneToOneField zu settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=SET_NULL)
- [X] T006 [P] Erstellen und Ausführen der Django-Datenbankmigration für `ClubProfile.zps_nummer`, `OnboardingProgress` und `StaffInvitation` via `core/migrations/`
- [X] T007 Registrieren von `OnboardingProgress` und `StaffInvitation` im Django Admin Panel in `core/admin.py` mit Revisionssperre (Löschschutz)

**Checkpoint**: Datenfundament bereit – die User Stories können nun implementiert und unabhängig getestet werden.

---

## Phase 3: User Story 1 - Geführter Erstkonfigurations-Assistent (Priority: P1) 🎯 MVP

**Goal**: Ein Administrator kann nach Erst-Login per automatischem Redirect einen mehrstufigen Assistenten durchlaufen, Vereinsstammdaten, Modulauswahl und Beitragssätze konfigurieren und die Grundeinrichtung abschließen.

**Independent Test**: Ein Administrator meldet sich an einer frischen Instanz an, wird nach `/onboarding/` geleitet, füllt Schritte 1–3 aus und schließt in Schritt 6 ab; `ClubProfile`, `ModuleSettings` und `FeeCategory` sind gespeichert, `OnboardingProgress.ist_abgeschlossen` ist `True`.

### Tests for User Story 1 🧪
- [X] T008 [P] [US1] Unit-, Negativ- und Workflow-Tests für den Onboarding-Wizard in `core/tests/test_onboarding.py` schreiben (Prüfung von Schrittfolgen, Validierungsfehlern, 403-Schutz für Nicht-Admins und AuditLog-Einträgen)

### Implementation for User Story 1
- [X] T009 [P] [US1] Formulare für die Wizard-Schritte 1 bis 3 in `core/forms_onboarding.py` implementieren (`OnboardingProfileForm`, `OnboardingModulesForm`, `OnboardingDuesForm`)
- [X] T010 [US1] Fachservice-Funktionen in `core/services.py` implementieren: `apply_default_fee_categories(user=None)` und `complete_onboarding(user, cleanup_demodata=False)` mit AuditLog-Eintrag
- [X] T011 [US1] Function-Based Views für den Onboarding-Wizard in `core/views_onboarding.py` implementieren (`onboarding_wizard_entry`, `onboarding_step_1_profile`, `onboarding_step_2_modules`, `onboarding_step_3_dues`, `onboarding_step_6_finish`, `onboarding_step_back`) mit `@role_required(ADMIN_GROUP)`
- [X] T012 [P] [US1] Templates für die Wizard-Schritte 1, 2, 3 und 6 in `templates/core/onboarding/` erstellen (`step_1_profile.html`, `step_2_modules.html`, `step_3_dues.html`, `step_6_finish.html`)
- [X] T013 [US1] URL-Routen für den Wizard in `core/urls.py` registrieren (`/onboarding/`, `/onboarding/schritt/<int:schritt>/`, `/onboarding/zurueck/<int:schritt>/`)
- [X] T014 [US1] Erst-Redirect für Administratoren bei unvollständigen Stammdaten in `core/auth_views.py` (`anmelden`, `zwei_faktor`) und `core/views.py` (`dashboard`) integrieren

**Checkpoint**: User Story 1 (MVP) ist vollständig lauffähig und isoliert testbar (`pytest core/tests/test_onboarding.py`).

---

## Phase 4: User Story 2 - Schnelle Mitglieder- und Bestandsdatenübernahme (Priority: P1)

**Goal**: Im Onboarding-Schritt 4 kann der Administrator flexibel wählen zwischen dem automatischen ZPS-Direktabruf aus dem DSB-Wertungsportal oder dem dateibasierten CSV-Import mit Dry-Run.

**Independent Test**: Für Schritt 4 wird ZPS-Nummer eingegeben -> Mitglieder mit DWZ werden angelegt; alternativ CSV hochgeladen -> Dry-Run zeigt Vorschau und Übernahme legt Datensätze mit verschlüsselten SEPA-Mandaten an.

### Tests for User Story 2 🧪
- [X] T015 [P] [US2] Tests für den ZPS-Initialimport und Onboarding-CSV-Import in `members/tests/test_dsb_initial_import.py` schreiben (Prüfung von API-Mocks, Datenmappings, Dublettenerkennung, Dry-Run-Validierung und AuditLog)

### Implementation for User Story 2
- [X] T016 [US2] Reinen Fachservice `import_dsb_initial(vkz: str, user: User | None = None) -> DSBInitialImportResult` in `members/services/dsb_sync.py` implementieren (Abruf via `fetch_dsb_vereinsliste`, Datentransformation, Dublettenschutz, atomare Speicherung und AuditLog)
- [X] T017 [US2] View-Logik für Onboarding-Schritt 4 in `core/views_onboarding.py` (`onboarding_step_4_members`) implementieren mit Unterstützung für ZPS-Direktimport, CSV-Upload & Dry-Run sowie Überspringen
- [X] T018 [P] [US2] Template für Onboarding-Schritt 4 in `templates/core/onboarding/step_4_members.html` implementieren (Hybrid-Auswahl: ZPS-Eingabe mit Ladezustand vs. Drag-and-Drop CSV-Upload mit tabellarischer Dry-Run-Vorschau)

**Checkpoint**: User Story 2 ist abgeschlossen und kann unabhängig getestet werden (`pytest members/tests/test_dsb_initial_import.py`).

---

## Phase 5: User Story 3 - Interaktive „Erste Schritte“-Checkliste im Dashboard (Priority: P2)

**Goal**: Nach dem Setup zeigt das Vorstandsdashboard eine motivierende Fortschritts-Checkliste (Profil, Beiträge, Mitglieder, Mannschaften, Funktionäre) mit Direktlinks und Ausblend-Funktion.

**Independent Test**: Dashboard zeigt Fortschrittsbalken; nach Erledigung von Schritten wächst der Prozentsatz; Klick auf „Checkliste ausblenden“ persistiert `checklist_ausgeblendet = True` und entfernt das Widget.

### Tests for User Story 3 🧪
- [X] T019 [P] [US3] Tests für das Getting-Started-Dashboard-Widget in `core/tests/test_onboarding_widget.py` schreiben (Prüfung der Berechnungslogik, `assertNumQueries <= 4`, Negativtest: Nicht-Admins sehen Widget nie, Ausblend-POST-Route)

### Implementation for User Story 3
- [X] T020 [US3] Reinen Fachservice `get_onboarding_checklist_status(user=None) -> dict` in `core/services.py` implementieren (performante Aggregate für Profil, Beitragsstufen, Mitglieder, Teams, Funktionäre ohne N+1-Abfragen)
- [X] T021 [US3] Kontext-Injektion in `core/views.py` (`_dashboard_vorstand`) und POST-View `dismiss_onboarding_checklist` in `core/views_onboarding.py` implementieren
- [X] T022 [P] [US3] Template `templates/core/includes/onboarding_widget.html` erstellen und in `templates/core/dashboard.html` einbinden (semantischer Fortschrittsbalken nach WCAG 2.1 AA mit ARIA-Attributen)

**Checkpoint**: User Story 3 ist abgeschlossen und unabhängig verifizierbar (`pytest core/tests/test_onboarding_widget.py`).

---

## Phase 6: User Story 4 - Sanfter Übergang von Testbetrieb zu Produktivdaten (Priority: P2)

**Goal**: Der Onboarding-Assistent erkennt, wenn Demo-Daten aktiv sind, und bietet vor dem Abschluss eine sichere 1-Klick-Bereinigung, die Testdaten löscht, aber echte Stammdaten und Admins schützt.

**Independent Test**: Auf einer Instanz mit Demo-Daten zeigt Schritt 6 die Bereinigungsoption; nach Ausführung sind Testpartien und Testmitglieder gelöscht, während das Vereinsprofil intakt bleibt.

### Tests for User Story 4 🧪
- [X] T023 [P] [US4] Tests für den Übergang von Testbetrieb zu Produktivdaten im Onboarding in `core/tests/test_onboarding_demo_transition.py` schreiben (Prüfung der Demo-Daten-Erkennung, Schutz manuell erfasster Mitglieder vor versehentlicher Löschung, AuditLog)

### Implementation for User Story 4
- [X] T024 [US4] Integration der Demo-Daten-Prüfung (`core.services.get_demo_data_status`) und Bereinigung (`core.services.remove_demo_data`) in die Abschluss-View `onboarding_step_6_finish` in `core/views_onboarding.py`
- [X] T025 [P] [US4] UI-Warn- und Bestätigungs-Banner für Demo-Daten in `templates/core/onboarding/step_6_finish.html` einbetten

**Checkpoint**: User Story 4 ist funktional und unabhängig getestet (`pytest core/tests/test_onboarding_demo_transition.py`).

---

## Phase 7: User Story 5 - Einladung von Funktionären & Vorstandskollegen (Priority: P3)

**Goal**: Im Onboarding (Schritt 5) kann der Admin Funktionäre per E-Mail mit zeitlich befristetem Token einladen; die Eingeladenen vergeben über `/einladung/<token>/` ihr eigenes Passwort und erhalten die korrekte Rolle.

**Independent Test**: Admin verschickt Einladung für `kasse@sc-matt.de` als `admin`; Aufruf des Token-Links erlaubt Passwortvergabe; neuer User wird angelegt und gehört zur Gruppe `admin`.

### Tests for User Story 5 🧪
- [X] T026 [P] [US5] Tests für das Einladungssystem in `core/tests/test_staff_invitation.py` schreiben (Prüfung von Token-Gültigkeit, Token-Ablauf nach 7 Tagen, Passwort-Validierung, Rollenzuweisung, Negativtest: Ungültige Tokens und Nicht-Admin-Zugriff verweigert)

### Implementation for User Story 5
- [X] T027 [US5] Fachservice-Funktionen in `core/services.py` implementieren: `create_staff_invitation(email, vorname, nachname, rolle, invited_by, send_mail=True)` und `accept_staff_invitation(token, username, password)` mit AuditLog-Einträgen
- [X] T028 [US5] View-Logik für Onboarding-Schritt 5 in `core/views_onboarding.py` (`onboarding_step_5_staff`) sowie Annahme-View `accept_invitation` in `core/auth_views.py` implementieren
- [X] T029 [P] [US5] Templates erstellen: Schritt 5 in `templates/core/onboarding/step_5_staff.html` (Einladungsliste & Schnellformular mit Link-Kopierbutton) und Registrierungs-Template `templates/core/invitation_accept.html`
- [X] T030 [US5] URL-Route `path("einladung/<str:token>/", auth_views.accept_invitation, name="accept_invitation")` in `core/urls.py` registrieren

**Checkpoint**: User Story 5 ist vollständig und unabhängig getestet (`pytest core/tests/test_staff_invitation.py`).

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Systemweite Konsistenz, Barrierefreiheit, Performance und Validierung.

- [X] T031 [P] Stylesheet-Erweiterungen in `static/css/app.css` für Wizard-Navigation, Progress-Bar und Touch-Ziele (WCAG 2.1 AA Kontraste, mind. 44x44 px Touch-Ziele, responsiv von 360 px bis 1280 px ohne horizontalen Scrollbalken)
- [X] T032 Menü-Integration des Onboardings/Setups in `templates/core/includes/nav.html` für Administratoren
- [X] T033 Ausführen aller Validierungsszenarien aus `specs/002-vereins-onboarding/quickstart.md` und Verifikation der gesamten Testsuite mit `docker compose exec app pytest`

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Keine Abhängigkeiten – sofort ausführbar.
- **Phase 2 (Foundational)**: Hängt von Phase 1 ab – **BLOCKIERT** alle nachfolgenden User Stories.
- **Phase 3 (User Story 1 - MVP)**: Hängt von Phase 2 ab – Kern-Assistent für das Onboarding.
- **Phase 4 (User Story 2 - Datenübernahme)**: Hängt von Phase 2 ab – erweitert Schritt 4 des Wizards.
- **Phase 5 (User Story 3 - Dashboard-Checkliste)**: Hängt von Phase 2 ab – erweitert das Dashboard.
- **Phase 6 (User Story 4 - Demo-Daten-Übergang)**: Hängt von Phase 3 ab – erweitert Schritt 6 des Wizards.
- **Phase 7 (User Story 5 - Funktionärseinladung)**: Hängt von Phase 2 ab – erweitert Schritt 5 des Wizards.
- **Phase 8 (Polish)**: Hängt vom Abschluss der gewünschten User Stories ab.

### User Story Dependencies & Parallelarbeit
- **US1 (MVP)** kann direkt nach Phase 2 starten.
- **US2 (Datenübernahme)**, **US3 (Dashboard-Widget)** und **US5 (Funktionäre)** können nach Phase 2 parallel bearbeitet werden.
- **US4 (Demo-Daten)** baut auf Schritt 6 aus US1 auf.

---

## Parallel Example: User Story 1 & User Story 2

```bash
# Entwickler A (US1 - Basis-Assistent):
Task T008: "Unit-, Negativ- und Workflow-Tests für den Onboarding-Wizard in core/tests/test_onboarding.py"
Task T009: "Formulare für die Wizard-Schritte 1 bis 3 in core/forms_onboarding.py"
Task T012: "Templates für die Wizard-Schritte 1, 2, 3 und 6 in templates/core/onboarding/"

# Entwickler B (US2 - Verbands- & CSV-Import):
Task T015: "Tests für den ZPS-Initialimport und Onboarding-CSV-Import in members/tests/test_dsb_initial_import.py"
Task T016: "Reinen Fachservice import_dsb_initial(...) in members/services/dsb_sync.py"
Task T018: "Template für Onboarding-Schritt 4 in templates/core/onboarding/step_4_members.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Phase 1 (Setup) ausführen (T001, T002).
2. Phase 2 (Foundational) ausführen (T003 bis T007).
3. Phase 3 (User Story 1) umsetzen (T008 bis T014).
4. **STOP & VALIDATE**: Testen mit `pytest core/tests/test_onboarding.py`. Der Basis-Wizard ist damit bereits vollständig produktionsfähig.

### Inkrementelle Auslieferung
1. **Inkrement 1**: Setup + Foundation + US1 (MVP: Stammdaten, Module, Beiträge, Go-Live).
2. **Inkrement 2**: US2 (Hybrid-Datenübernahme ZPS / CSV).
3. **Inkrement 3**: US3 (Dashboard Getting-Started-Checkliste).
4. **Inkrement 4**: US4 (Demo-Daten-Bereinigung im Wizard).
5. **Inkrement 5**: US5 (Funktionärseinladung per E-Mail & Token).
6. **Inkrement 6**: Polish & Gesamtprüfung (T031 bis T033).
