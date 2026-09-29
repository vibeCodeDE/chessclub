# Implementation Plan: Schachvereins-Software

## Overview

Selbst gehostete Django-Web-App für einen Schachverein (< 200 Mitglieder): Mitglieder, Beiträge (SEPA-Status), Spielbetrieb, Turniere, Kommunikation, Kassenbuch — DSGVO-konform, deutschsprachig, Deployment per Docker Compose auf Vereinsserver.

## Architecture Decisions

- **Django 5 + PostgreSQL + server-seitige Templates (Tailwind via CDN-freiem lokalem Build oder plain CSS):** Nutzer kennt Django noch nicht — Djangos Admin-Oberfläche übernimmt 60 % der Verwaltungs-UI; Views bleiben einfache Function-Based Views. Keine SPA, kein Node-Build-Zwang im Prod-Betrieb (Tailwind-CLI nur zur Build-Zeit).
- **Rollenmodell über Django Groups:** `admin` (Vorstand), `kapitaen`, `mitglied` — keine eigene Permission-Engine; `@login_required` + Gruppen-Checks.
- **Single-Tenant, eine Organisation:** kein Tenant-Field, kein Multi-Club-Denkwerk.
- **Fachlogik in `apps/`:** getrennte Apps `members`, `dues`, `teams`, `tournaments`, `comms`, `cashbook`, `core` (Dashboard, Audit, DSGVO-Tools).
- **E-Mails über SMTP des Vereins/Providers,** Versand nur aus Gruppenverteilung mit Opt-in-Status.
- **Schweizer Paarung:** zunächst eigene, kleine Implementierung (Buchholz-Wertung) statt exotischer Library — Risiko bewusst minimiert, Formate ≤ 64 Spieler reichen für den Verein.
- **Mobile-First + PWA:** alle Templates responsive ab 360 px (Burger-Menü, scrollbare Tabellen); zusätzlich Web-App-Manifest + Service Worker, damit die App auf dem Homescreen installierbar ist (keine nativen Apps, kein Store).

## Task List

### Phase 1: Fundament

- [x] **T1: Projekt-Scaffold + Docker**
  Django-Projekt, `core`-App, Settings (DEBUG, Postgres), Docker Compose (app + db), Basis-Template **mobile-first (Responsive ab 360 px, Burger-Menü, scrollbare Tabellen)**, Tailwind/Styles, Health-Check-Route.
  *Acceptance:* `docker compose up` → Login-Seite erreichbar; Layout auf 360 px ohne horizontalen Overflow; `pytest` läuft leer grün.
  *Verify:* `docker compose up -d` + `pytest` + Browser-Check 360/768/1280 px · *Files:* `manage.py`, `docker-compose.yml`, `Dockerfile`, `config/`, `core/` · *Scope:* M

- [x] **T2: Auth, Rollen, Navigation**
  Login/Logout, Gruppen `admin/kapitaen/mitglied`, rollenbasierte Menüs, Passwort-Reset für Admin-Versand.
  *Acceptance:* 3 Testnutzer (eine pro Rolle) sehen unterschiedliche Menüs; Nicht-Mitglied wird abgewiesen.
  *Verify:* `pytest core/` · *Files:* `core/views.py`, `core/templates/` · *Deps:* T1 · *Scope:* S

- [x] **T3: Mitgliederstammdaten + Admin**
  Model `Member` (Profilfelder, Status aktiv/passiv/ausgetreten, Ein-/Austrittsdatum), Djangos Admin mit Liste/Suche, Mitgliederliste mit Filter, Detailseite.
  *Acceptance:* Admin legt Mitglied an, listet/filtert es; Statuswechsel historisiert (kein Hard-Delete).
  *Verify:* `pytest members/` · *Files:* `members/models.py`, `members/admin.py`, `members/views.py` · *Deps:* T2 · *Scope:* M

- [x] **T4: Selbstbedienung + Änderungswunsch**
  Mitglied sieht eigene Daten, reicht Änderungswunsch ein (Feld + Wunschwert); Admin-Übersicht mit Freigabe/Ablehnung; Freigabe schreibt Wert + Audit-Eintrag.
  *Acceptance:* Wunsch fliebt von Einreichung bis zur Freigabe; ohne Freigabe ändert sich nichts am Stammdatum.
  *Verify:* `pytest members/` (Workflow-Test) · *Files:* `members/models.py`, `members/views.py`, `members/templates/` · *Deps:* T3 · *Scope:* M

- [x] **T5: Audit-Log + Login-Protokoll**
  Signale loggen Änderungen an personenbezogenen Feldern (Wer, Was, Wann, Alt/Neu) + Login-Ereignisse; Admin-Ansicht.
  *Acceptance:* Jede Mitgliederänderung und jeder Login ist mit Zeit + Benutzer sichtbar.
  *Verify:* `pytest core/` · *Files:* `core/models.py`, `core/signals.py` · *Deps:* T4 · *Scope:* M

**Checkpoint 1:** Alle Tests grün; Rollen-Flow manuell durchklicken (Admin anlegen → Wunsch → Freigabe → Audit-Eintrag). *Review mit Mensch.*

### Phase 2: Beiträge

- [x] **T6: Beitragssätze + Beitragsjahre**
  Models `FeeCategory` (Erwachsene/Jugend/Familie/ermäßigt, Betrag, Jahr), Zuordnung zum Mitglied.
  *Acceptance:* Kategorien pflegen, Beträge je Jahr speichern, Mitglied hat gültige Kategorie.
  *Verify:* `pytest dues/` · *Files:* `dues/models.py`, `dues/admin.py` · *Deps:* T5 · *Scope:* S

- [x] **T7: Beitragslauf**
  Jahreslauf erzeugt für alle aktiven Mitglieder mit Kategorie einen Beitragsposten (idempotent — gleicher Lauf doppelt erzeugt nichts).
  *Acceptance:* Lauf 2027 mit 10 Testmitgliedern → 10 Posten, zweiter Lauf → weiterhin 10.
  *Verify:* `pytest dues/` · *Files:* `dues/views.py`, `dues/services.py` · *Deps:* T6 · *Scope:* S

- [x] **T8: SEPA-Mandate + Zahlungserfassung**
  `SepaMandate` je Mitglied (Referenz, Datum, Status), Zahlungen buchen (SEPA-Einzug/Überweisung/Bar, manuell), offener Betrag je Posten.
  *Acceptance:* Zahlung markiert Posten als bezahlt; offene-Beitrags-Liste stimmt; kein Bank-API-Call im Code.
  *Verify:* `pytest dues/` · *Files:* `dues/models.py`, `dues/views.py` · *Deps:* T7 · *Scope:* M

- [x] **T9: Mahnwesen + Beitrags-Export**
  Offene-Beitragsübersicht mit 1./2. Mahnung (Datum setzen), Mahnbrief als druckbares HTML/PDF, CSV-Export der Jahresbeiträge.
  *Acceptance:* Mahnbrief druckbar für ein Testmitglied; CSV enthält alle Posten des Jahres.
  *Verify:* `pytest dues/` · *Files:* `dues/templates/dues/mahnbrief.html`, `dues/views.py` · *Deps:* T8 · *Scope:* M

- [x] **T10: Dashboard**
  Startseite für Admin: offene Beiträge (Summe + Anzahl), anstehende Termine, letzte Änderungswünsche/Anmeldungen.
  *Acceptance:* Nach Seed-Daten alle drei Kacheln mit echten Zahlen.
  *Verify:* `pytest core/` + manuell · *Files:* `core/views.py`, `core/templates/` · *Deps:* T9 · *Scope:* S

**Checkpoint 2:** Beitragslauf für Testjahr komplett durchgespielt (Lauf → Zahlung → Mahnung → Export). *Review mit Mensch.*

### Phase 3: Spielbetrieb

- [x] **T11: Mannschaften + Ligaspiele**
  Models `Team`, `LeagueMatch` (Datum, Gegner, Heim/Auswärts, Liga), CRUD für Admin.
  *Acceptance:* 2 Mannschaften, 1 Ligspiel anlegbar und listenbar.
  *Verify:* `pytest teams/` · *Files:* `teams/models.py`, `teams/views.py` · *Deps:* T10 · *Scope:* S

- [x] **T12: Aufstellung + Einzelergebnisse**
  Kapitän trägt Aufstellung (Reihenfolge Mitglieder) ein; Ergebnis je Brett (1/0/½) → Mannschaftsergebnis automatisch summieren; Frist-Status.
  *Acceptance:* Nur Kapitän/Admin kann aufstellen; Summe der Bretter = Mannschaftsergebnis.
  *Verify:* `pytest teams/` · *Files:* `teams/views.py`, `teams/templates/` · *Deps:* T11 · *Scope:* M

- [x] **T13: Tabellenberechnung**
  Liga-Tabelle aus allen Ergebnissen (Satz 1/½/0, Buchholz als Beiordner), Anzeige je Liga.
  *Acceptance:* 4 Mannschaften × 3 Spiele → korrekte Reihenfolge (Testdatensatz mit bekanntem Ergebnis).
  *Verify:* `pytest teams/` · *Files:* `teams/services.py` · *Deps:* T12 · *Scope:* S

**Checkpoint 3:** Testspiel komplett (Aufstellung → Ergebnis → Tabelle). *Review mit Mensch.*

### Phase 4: Turniere

- [x] **T14: Turnier-Modell + öffentliche Anmeldung**
  `Tournament` (Datum, Ort, Format, Anmeldeschluss, Startgeld-Status), öffentliche Detailseite + Anmeldeformulare (Mitglied/Gast mit Name + E-Mail), Teilnehmerliste.
  *Acceptance:* Öffentliche Seite ohne Login erreichbar; Anmeldung landet in Teilnehmerliste.
  *Verify:* `pytest tournaments/` · *Files:* `tournaments/models.py`, `tournaments/views.py` · *Deps:* T13 · *Scope:* M

- [x] **T15: Schweizer Paarung + Rundenwertung**
  Paarungsservice (Buchholz, Bye-Handling, Remis-Regeln), Runden anlegen, Paarungen erzeugen, Ergebnisse je Partie erfassen, Zwischenstand.
  *Acceptance:* 8 Testspieler, 3 Runden: Paarungen ohne Doppel-Partien, Stand korrekt (Referenzrechnung im Test).
  *Verify:* `pytest tournaments/` (Paarungs-Tests) · *Files:* `tournaments/pairing.py`, `tournaments/views.py` · *Deps:* T14 · *Scope:* L → bleibt in einer Session, da reine Funktionslogik + 1 View

- [x] **T16: Turnierexport**
  Ergebnisliste druckansicht + CSV-Export (ChessResults-tauglich: Spieler, Wertung, Punkte, Runden).
  *Acceptance:* CSV importtestweise in ChessResults-Parser/Excel; Druckansicht A4-freundlich.
  *Verify:* `pytest tournaments/` + manueller Download · *Files:* `tournaments/views.py`, Templates · *Deps:* T15 · *Scope:* S

**Checkpoint 4:** Testturnier über 3 Runden vollständig gespielt. *Review mit Mensch.*

### Phase 5: Kommunikation & Kassenbuch

- [x] **T17: News/Ankündigungen**
  `NewsPost` (Titel, Text, Datum, Entwurf/veröffentlicht), öffentliche Startseite zeigt veröffentlichte Posts, Admin-CRUD, Archiv.
  *Acceptance:* Entwurf nicht öffentlich, nach Veröffentlichung auf Startseite + Archiv.
  *Verify:* `pytest comms/` · *Files:* `comms/models.py`, `comms/views.py` · *Deps:* T16 · *Scope:* S

- [x] **T18: E-Mail-Versand an Gruppen**
  Opt-in-Flag je Mitglied, Formular „E-Mail an Gruppe" (Betreff, Text, Empfängergruppe), Versand via SMTP, Versandprotokoll (An, Wann, Status).
  *Acceptance:* Testversand an 3 Empfänger mit Nur-Test-Modus (Console-Backend); Protokollierung korrekt; Opt-out wird übersprungen.
  *Verify:* `pytest comms/` · *Files:* `comms/views.py`, `comms/services.py` · *Deps:* T17 · *Scope:* M

- [x] **T19: Kassenbuch**
  `CashEntry` (Einnahme/Ausgabe, Kategorie, Betrag, Datum, Notiz), Liste + Jahresfilter, CSV-Export für Steuerberater.
  *Acceptance:* Buchungen anlegen/filtern; Jahres-CSV summiert korrekt.
  *Verify:* `pytest cashbook/` · *Files:* `cashbook/models.py`, `cashbook/views.py` · *Deps:* T18 · *Scope:* S

**Checkpoint 5:** News veröffentlichen + Test-Mail + Kassenexport. *Review mit Mensch.*

### Phase 6: DSGVO & Betrieb

- [x] **T20: DSGVO-Export + Löschfristen**
  Ein-Klick-PDF/HTML-Auskunft je Mitglied (alle personenbezogenen Daten), automatische Anonymisierung nach Austritt + konfigurierbarer Frist (Management-Command), Maschinenlesbarer Export der Datenkategorien.
  *Acceptance:* Auskunft enthält alle Felder; Anonymisierung löscht Kontaktdaten, behält Finanzhistorie.
  *Verify:* `pytest core/` + `python manage.py anonymize_former_members --dry-run` · *Files:* `core/views.py`, `core/management/commands/` · *Deps:* T19 · *Scope:* M

- [x] **T21: Deployment + Backup + Restore-Doku**
  Produktions-Compose (TLS-Vorbereitung Reverse Proxy), nächtliches DB-Backup (pg_dump-Container), `docs/deployment.md` inkl. Restore-Anleitung und Restore-Test-Protokoll.
  *Acceptance:* Restore-Test dokumentiert und einmal erfolgreich (< 4 h).
  *Verify:* Manuell: Backup → leere DB → Restore → Daten da · *Files:* `docker-compose.prod.yml`, `docs/deployment.md` · *Deps:* T20 · *Scope:* M

- [x] **T22: Härtung: 2FA, Headers, Fehlalarme**
  2FA für Admin-Gruppe (django-otp), Sicherheits-Header (HSTS, X-Frame, CSRF), Fehlerbenachrichtigung per E-Mail an Admin, Wartungsdoku `docs/wartung.md` (Django-Primer für den Nutzer).
  *Acceptance:* Admin-Login erfordert 2FA; Sicherheits-Header per Response-Check; Nutzer kann alle Wartungsschritte aus `docs/wartung.md` nachvollziehen.
  *Verify:* `pytest core/` + `docker compose -f docker-compose.prod.yml config` · *Files:* `config/settings.py`, `docs/wartung.md` · *Deps:* T21 · *Scope:* M

- [x] **T23: PWA — installierbare App**
  `manifest.webmanifest` (Name, Icons, `display: standalone`, Farbschema), Service Worker (App-Shell + Startseite/News aus Cache, Network-First für den Rest), iOS-Meta-Tags (apple-touch-icon, Statusbar), Registrierung im Basis-Template, Versions-/Cache-Invalidierung bei Deploy.
  *Acceptance:* „Zum Homescreen hinzufügen" auf Android + „Zum Bildschirm hinzufügen" auf iOS funktioniert; App öffnet sich ohne Browser-UI; Startseite lädt offline aus dem Cache; Update löscht alten Cache.
  *Verify:* `pytest core/` (SW-Route, Manifest-Route) + manuell Chrome DevTools → Application → Add to home screen · *Files:* `core/templates/`, `static/manifest.webmanifest`, `static/sw.js` · *Deps:* T22 · *Scope:* M

**Checkpoint Final:** Alle PRD-Erfolgskriterien durchgegangen, DSGVO-Checkliste (PRD §4.1 N1.1–N1.6) abgehakt, Abnahme durch Vorstand.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Django unbekannt beim Nutzer | Med | Admin-first-Ansatz, `docs/wartung.md`, keine exotischen Packages |
| Schweizer Paarung falsch implementiert | Hoch | Referenz-Tests mit bekannten Turnierdaten; manuelle Abnahme 3 Runden |
| E-Mail-Zustellung selbst gehostet (SPF/DKIM) | Med | Versand-Protokoll + Konzentrationsrat in `docs/deployment.md`; optional SMTP des Providers |
| Umfang zu groß für eine Session | Med | Klare Task-Größen S/M, Checkpoints nach je 3–5 Tasks |
| Datenverlust auf Vereinsserver | Hoch | T21: tägliche Backups + dokumentierter Restore-Test |

## Open Questions

- SMTP-Zugangsdaten des Vereins (vor T18 nötig — vorerst Django-Console-Backend im Dev)
- Exakte Beitragssätze und Kategorien des Vereins (vor T6)
- Domain/Hostname für das Deployment (vor T21)
