# Implementation Plan: Schachvereins-Software

## Overview

Selbst gehostete Django-Web-App für einen Schachverein (< 200 Mitglieder): Mitglieder, Beiträge (SEPA-Status), Spielbetrieb, Turniere, Kommunikation, Kassenbuch — DSGVO-konform, deutschsprachig, Deployment per Docker Compose auf Vereinsserver.

## Architecture Decisions

- **Django 5 + PostgreSQL + server-seitige Templates (Tailwind via CDN-freiem lokalen Build oder plain CSS):** Nutzer kennt Django noch nicht — Djangos Admin-Oberfläche übernimmt 60 % der Verwaltungs-UI; Views bleiben einfache Function-Based Views. Keine SPA, kein Node-Build-Zwang im Prod-Betrieb (Tailwind-CLI nur zur Build-Zeit).
- **Rollenmodell über Django Groups:** `admin` (Vorstand), `kapitaen`, `mitglied` — keine eigene Permission-Engine; `@login_required` + Gruppen-Checks; **verbindliche Matrix in PRD §3.8**.
- **Single-Tenant, eine Organisation:** kein Tenant-Field, kein Multi-Club-Denkwerk.
- **Fachlogik in `apps/`:** getrennte Apps `members`, `dues`, `teams`, `tournaments`, `comms`, `cashbook`, `core` (Dashboard, Audit, DSGVO-Tools).
- **E-Mails über SMTP des Vereins/Providers,** Versand nur aus Gruppenverteilung mit Opt-in-Status.
- **Schweizer Paarung:** zunächst eigene, kleine Implementierung (Buchholz-Wertung) statt exotischer Library — Risiko bewusst minimiert, Formate ≤ 64 Spieler reichen für den Verein. Erst in v1.1, wenn Handpaarungen (v1) laufen.
- **Mobile-First + PWA:** alle Templates responsive ab 360 px (Burger-Menü, scrollbare Tabellen); zusätzlich Web-App-Manifest + Service Worker, damit die App auf dem Homescreen installierbar ist (keine nativen Apps, kein Store).

## Konventionen

- **Größe:** Task-Größe einer Session: `S` klein, `M` mittel, `L` groß. *(Früher als „Scope" geführt — hat sich mit PRD-Priorität S vermischt.)*
- **PRD:** Verweis auf die Anforderung im PRD (`M2.2`, `S3.4`, `N1.5` …). Dort gilt M = Muss, S = Sollte, K = Kann.
- **Release:** `v1` = Kernrelease (alle M-Anforderungen) · `v1.1` = ergänzende S-Anforderungen, **erst nach v1-Abnahme**.
- Jeder Testblock enthält zwingend mindestens einen **Negativtest** (verweigerter Zugriff, Randfall, Dry-Run) und für Daten-/Wiederherstellungs-Tasks einen **Integrationstest** (End-to-End-Fluss).
- **Traceability-Regel:** Jede PRD-Anforderungs-ID (M/S/K/N) ist genau einer Task zugeordnet. Beim Anlegen oder Umnummerieren einer Anforderung wird die Zuordnung hier und in `docs/prd.md` im selben Commit nachgezogen. Unzugeordnete IDs sind ein Review-Blocker.
- **Nummernvergabe:** Aufgaben-IDs werden **nicht** wiederverwendet. Nachträge im mittleren Plan erhalten ein `b`-Suffix (T11b, T25b), damit bestehende Verweise in `tasks/todo.md` und im Code gültig bleiben.
- **Status:** Checkboxen `[x]`/`[ ]` stehen **ausschließlich** in dieser Datei. `tasks/todo.md` führt nur das Fortschrittsprotokoll (erledete Tasks mit Verifikationsbelegen) und verlinkt auf die Task hier.

## Task List

### Phase 1: Fundament

- [x] **T1: Projekt-Scaffold + Docker**
  Django-Projekt, `core`-App, Settings (DEBUG, Postgres), Docker Compose (app + db), Basis-Template **mobile-first (Responsive ab 360 px, Burger-Menü, scrollbare Tabellen)**, Tailwind/Styles, Health-Check-Route.
  *Acceptance:* `docker compose up` → Login-Seite erreichbar; Layout auf 360 px ohne horizontalen Overflow; `pytest` läuft leer grün.
  *Verify:* `docker compose up -d` + `pytest` + Browser-Check 360/768/1280 px · *Files:* `manage.py`, `docker-compose.yml`, `Dockerfile`, `config/`, `core/` · *Größe:* M · *PRD:* N2.6, M7.2 · *Release:* v1

- [x] **T2: Auth, Rollen, Navigation**
  Login/Logout, Gruppen `admin/kapitaen/mitglied`, rollenbasierte Menüs, Passwort-Reset für Admin-Versand.
  *Acceptance:* 3 Testnutzer (eine pro Rolle) sehen unterschiedliche Menüs; Nicht-Mitglied wird abgewiesen.
  *Verify:* `pytest core/` · *Files:* `core/views.py`, `core/templates/` · *Größe:* S · *PRD:* M1.2, M7.2, N1.5 · *Release:* v1 · *Deps:* T1

- [x] **T3: Mitgliederstammdaten + Admin**
  Model `Member` (Profilfelder, Status aktiv/passiv/ausgetreten, Ein-/Austrittsdatum), Djangos Admin mit Liste/Suche, Mitgliederliste mit Filter, Detailseite.
  *Acceptance:* Admin legt 3 Testmitglieder an; Liste zeigt alle 3, Filter nach Status "aktiv" liefert genau 2; Statuswechsel auf "ausgetreten" erzeugt einen Historieneintrag, das Mitglied selbst bleibt per Datensatz-ID auffindbar (kein Hard-Delete); CSV-Export enthält die 3 Testmitglieder.
  *Verify:* `pytest members/` — **Negativtest:** Rolle „mitglied" erhält 403 auf der Admin-Detailseite eines fremden Mitglieds; Lösch-Aktion ist im Admin nicht vorhanden. · *Files:* `members/models.py`, `members/admin.py`, `members/views.py` · *Größe:* M · *PRD:* M1.1, M1.3, M1.5, M1.6 · *Release:* v1 · *Deps:* T2

- [x] **T4: Selbstbedienung + Änderungswunsch**
  Mitglied sieht eigene Daten, reicht Änderungswunsch ein (Feld + Wunschwert); Admin-Übersicht mit Freigabe/Ablehnung; Freigabe schreibt Wert + Audit-Eintrag.
  *Acceptance:* Wunsch fließt von Einreichung bis zur Freigabe; ohne Freigabe ändert sich nichts am Stammdatum.
  *Verify:* `pytest members/` (Workflow-Test) · *Files:* `members/models.py`, `members/views.py`, `members/templates/` · *Größe:* M · *PRD:* M1.4 · *Release:* v1 · *Deps:* T3

- [x] **T5: Audit-Log + Login-Protokoll**
  Signale loggen Änderungen an personenbezogenen Feldern (Wer, Was, Wann, Alt/Neu) + Login-Ereignisse; Admin-Ansicht.
  *Acceptance:* Jede Mitgliederänderung und jeder Login ist mit Zeit + Benutzer sichtbar.
  *Verify:* `pytest core/` · *Files:* `core/models.py`, `core/signals.py` · *Größe:* M · *PRD:* M7.3, N1.5 · *Release:* v1 · *Deps:* T4

**Checkpoint 1:** Alle Tests grün; Rollen-Flow manuell durchklicken (Admin anlegen → Wunsch → Freigabe → Audit-Eintrag). *Review mit Mensch.*

### Phase 2: Beiträge + Dashboard

- [x] **T6: Dashboard-Gerüst**
  Startseite für Admin mit Kachel-Gerüst (offene Beiträge, anstehende Termine, letzte Änderungswünsche/Anmeldungen) — **bewusst vor den Beitrags-Tasks**, weil M7.1 ein Muss ist. Beitrags-Kacheln bleiben Platzhalter bis T11.
  *Acceptance:* Wunsch-Kachel zeigt die echte Anzahl offener Wünsche (aus Testdaten); Beitrags-Kachel zeigt „verfügbar nach Beitragslauf"; **Termine- und Anmeldungs-Kacheln sind bewusst Platzhalter** bis T16/T19 (Ligaspiele/Turniere) — Entscheidung 2026-09-28: kein Termin-Modell in T6, damit der Scope klein bleibt.
  *Verify:* `pytest core/` (View + Kachel-Kontext) + manuell · *Files:* `core/views.py`, `core/templates/` · *Größe:* S · *PRD:* M7.1 · *Release:* v1 · *Deps:* T5

- [ ] **T7: Beitragssätze + Beitragsjahre**
  Models `FeeCategory` (Erwachsene/Jugend/Familie/ermäßigt, Betrag, Jahr), Zuordnung zum Mitglied.
  *Acceptance:* 4 Kategorien (Erwachsene/Jugend/Familie/ermäßigt) mit je einem Betrag für 2026 und 2027 angelegt; Betrag 2027 ändert den 2026-Wert nicht; Mitglied ohne Kategorie wird beim Beitragslauf (T8) übersprungen, nicht mit 0 € gebucht.
  *Verify:* `pytest dues/` — **Negativtest:** negativer Betrag wird abgelehnt; Mitglied mit Status „ausgetreten" kann keiner Kategorie zugeordnet werden. · *Files:* `dues/models.py`, `dues/admin.py` · *Größe:* S · *PRD:* M2.1 · *Release:* v1 · *Deps:* T5

- [ ] **T8: Beitragslauf**
  Jahreslauf erzeugt für alle aktiven Mitglieder mit Kategorie einen Beitragsposten (idempotent — gleicher Lauf doppelt erzeugt nichts).
  *Acceptance:* Lauf 2027 mit 10 Testmitgliedern → 10 Posten, zweiter Lauf → weiterhin 10.
  *Verify:* `pytest dues/` · *Files:* `dues/views.py`, `dues/services.py` · *Größe:* M · *PRD:* M2.2 · *Release:* v1 · *Deps:* T7

- [ ] **T9: SEPA-Mandate + Zahlungserfassung**
  `SepaMandate` je Mitglied (Referenz, Datum, Status), Zahlungen buchen (SEPA-Einzug/Überweisung/Bar, manuell, Zahlungsart je Buchung), offener Betrag je Posten.
  *Acceptance:* Zahlung markiert Posten als bezahlt; offene-Beitrags-Liste stimmt; kein Bank-API-Call im Code; Überzahlung wird als offener Gutschrift angezeigt, nicht gekappt.
  *Verify:* `pytest dues/` — **Negativtest:** Zahlung für ein Mitglied ohne Mandat bei Zahlungsart „SEPA-Einzug" wird abgelehnt. · *Files:* `dues/models.py`, `dues/views.py` · *Größe:* M · *PRD:* M2.3, M2.4 · *Release:* v1 · *Deps:* T8

- [ ] **T10: Mahnwesen + Beitrags-Export**
  Offene-Beitragsübersicht mit 1./2. Mahnung (Datum setzen), Mahnbrief als druckbares HTML/PDF, CSV-Export der Jahresbeiträge.
  *Acceptance:* Mahnbrief druckbar für ein Testmitglied; CSV enthält alle Posten des Jahres.
  *Verify:* `pytest dues/` — **Negativtest:** Nicht-Admin erhält 403 auf Mahnungsübersicht + Export; **Inhaltstest:** CSV enthält nur die erlaubten Felder (keine Adressen Dritter); zweiter Export identisch. · *Files:* `dues/templates/dues/mahnbrief.html`, `dues/views.py` · *Größe:* M · *PRD:* M2.5 · *Release:* v1 · *Deps:* T9

- [ ] **T11: Dashboard-Erweiterung offene Beiträge**
  Beitrags-Kacheln befüllen (offene Summe + Anzahl) sobald der Beitragslauf existiert.
  *Acceptance:* Nach Seed + Lauf zeigt die Beitrags-Kachel die echte offene Summe; ohne Lauf bleibt die Platzhalter-Anzeige (kein Crash bei Null).
  *Verify:* `pytest core/` + manuell · *Files:* `core/views.py`, `core/templates/` · *Größe:* S · *PRD:* M7.1 · *Release:* v1 · *Deps:* T10

- [ ] **T11b: Kassenbuch-Sicht Beiträge (Jahresübersicht)**
  Reine Lese-Sicht für den Kassenbericht: Zahlungen je Mitglied für ein gewähltes Jahr, Jahressumme Einnahmen aus Beiträgen, Offene-Posten zum Stichtag. Kein eigenes Buchungssystem — das bleibt S6.1/S6.2 (v1.1, T15).
  *Acceptance:* Für Jahr X mit 10 Mitgliedern und 8 Zahlungen zeigt die Übersicht 8 Zeilen; Jahressumme = Summe der 8 Beträge; Jahr ohne Daten zeigt „keine Buchungen" statt 0 €-Zeilen; Export CSV summiert identisch zur Anzeige.
  *Verify:* `pytest dues/` — **Negativtest:** Rolle „kapitaen" und „mitglied" erhalten 403; **Referenztest:** Jahressumme wird gegen eine im Test berechnete Modellsumme verglichen, nicht gegen einen festen Wert. · *Files:* `dues/views.py`, `dues/templates/dues/kassenbericht.html` · *Größe:* S · *PRD:* M2.6 · *Release:* v1 · *Deps:* T10

- [ ] **T12: Zugriffsprotokoll Detailansicht**
  Protokolliert den Aufruf einer Mitglieder-Detailansicht (Wer, Wann, welche Person) als Lese-„Zugriff" im AuditLog — schließt die Lücke zwischen PRD N1.5 („Zugriffe") und T5 (nur Änderungen + Logins).
  *Acceptance:* Detailaufruf erzeugt AuditLog-Eintrag; Auskunfts-Export (T23) wird ebenfalls protokolliert; Einträge sind nach 12 Monaten Löschfrist markierbar.
  *Verify:* `pytest core/` + `pytest members/` — **Negativtest:** Listenansicht erzeugt **keinen** Lese-Eintrag; fremdes Mitglied (Rolle „mitglied") darf Detailseite nicht öffnen (403). · *Files:* `core/signals.py` / `members/views.py`, `core/models.py` · *Größe:* S · *PRD:* N1.5 · *Release:* v1 · *Deps:* T5

**Checkpoint 2:** Beitragslauf für Testjahr komplett durchgespielt (Lauf → Zahlung → Mahnung → Export); Dashboard zeigt echte Zahlen. *Review mit Mensch.*

### Phase 3: Kommunikation (öffentliche Präsenz)

> Bisher hinter den Turnieren — die App **ist** die öffentliche Startseite (PRD §2), deshalb News vor Turnieranmeldungen.

- [ ] **T13: News/Ankündigungen + öffentliche Startseite**
  `NewsPost` (Titel, Text, Datum, Entwurf/veröffentlicht), öffentliche Startseite zeigt veröffentlichte Posts, Admin-CRUD, Archiv.
  *Acceptance:* 2 Beiträge (1 Entwurf, 1 veröffentlicht) angelegt; Startseite zeigt genau 1 Beitrag; Archiv listet beide nach Datum sortiert, Entwurf nur für Admin sichtbar.
  *Verify:* `pytest comms/` — **Negativtest:** Entwurf für Gast nicht sichtbar (nicht in Liste, 404 auf Detail); Nicht-Admin darf weder anlegen noch veröffentlichen (403). · *Files:* `comms/models.py`, `comms/views.py` · *Größe:* S · *PRD:* M5.1 · *Release:* v1 · *Deps:* T11

- [ ] **T14: E-Mail-Versand an Gruppen**
  Opt-in-Flag je Mitglied, Formular „E-Mail an Gruppe" (Betreff, Text, Empfängergruppe), Versand via SMTP, Versandprotokoll (An, Wann, Status).
  *Acceptance:* Testversand an drei Empfänger im Nur-Test-Modus (Console-Backend); Versandprotokoll enthält alle 3 mit Zeitpunkt und Status; 1 opt-out-Mitglied in der Gruppe wird übersprungen.
  *Verify:* `pytest comms/` — **Negativtest:** Opt-out-Mitglied erhält keine Mail; Nicht-Admin darf nicht versenden (403); leerer Empfänger-Wurf bricht mit klarer Meldung ab, statt 0 Mails still zu senden. · *Files:* `comms/views.py`, `comms/services.py` · *Größe:* M · *PRD:* M5.2 · *Release:* v1 · *Deps:* T13

- [ ] **T15: Kassenbuch** *(v1.1)*
  `CashEntry` (Einnahme/Ausgabe, Kategorie, Betrag, Datum, Notiz), Liste + Jahresfilter, CSV-Export für Steuerberater.
  *Acceptance:* Buchungen anlegen/filtern; Jahres-CSV summiert korrekt.
  *Verify:* `pytest cashbook/` — **Negativtest:** Nicht-Admin erhält 403 auf Liste + Export; **Inhaltstest:** CSV-Summe stimmt für gefiltertes Jahr (Vergleich mit Model-Berechnung). · *Files:* `cashbook/models.py`, `cashbook/views.py` · *Größe:* S · *PRD:* S6.1, S6.2 · *Release:* v1.1 · *Deps:* T14

**Checkpoint 3:** News veröffentlichen + Test-Mail; Kassenbuch (v1.1) separat. *Review mit Mensch.*

### Phase 4: Spielbetrieb

- [ ] **T16: Mannschaften + Ligaspiele**
  Models `Team`, `LeagueMatch` (Datum, Gegner, Heim/Auswärts, Liga), CRUD für Admin.
  *Acceptance:* 2 Mannschaften und 1 Ligspiel (Heim, Gegner, Datum) angelegt und in der Liste sichtbar; Spiel erscheint in der Liste der eigenen Mannschaft.
  *Verify:* `pytest teams/` — **Negativtest:** Rollen „mitglied" und „kapitaen" erhalten 403 auf Anlegen/Bearbeiten; Änderung eines Spiels im Status „abgeschlossen" wird abgelehnt. · *Files:* `teams/models.py`, `teams/views.py` · *Größe:* S · *PRD:* M4.1, M4.2 · *Release:* v1 · *Deps:* T14 · *Note:* NAV-Eintrag `teams:team_list` in `core/context_processors.py` wieder ergänzen

- [ ] **T17: Aufstellung + Einzelergebnisse**
  Kapitän trägt Aufstellung (Reihenfolge Mitglieder) ein; Ergebnis je Brett (1/0/½) → Mannschaftsergebnis automatisch summieren; Frist-Status.
  *Acceptance:* Nur Kapitän/Admin kann aufstellen; Summe der Bretter = Mannschaftsergebnis.
  *Verify:* `pytest teams/` — **Negativtest (PRD §3.8):** Kapitän einer **anderen** Mannschaft erhält 403; Rolle „mitglied" darf nicht aufstellen. · *Files:* `teams/views.py`, `teams/templates/` · *Größe:* M · *PRD:* M4.3, M4.4 · *Release:* v1 · *Deps:* T16

- [ ] **T18: Tabellenberechnung** *(v1.1)*
  Liga-Tabelle aus allen Ergebnissen (Satz 1/½/0, Buchholz als Hilfswertung/Tiebreak), Anzeige je Liga.
  *Acceptance:* 4 Mannschaften × 3 Spiele → korrekte Reihenfolge (Testdatensatz mit bekanntem Ergebnis).
  *Verify:* `pytest teams/` (Referenzrechnung; Umgang mit ungespielten/Abgesagten Spielen als Negativfall). · *Files:* `teams/services.py` · *Größe:* S · *PRD:* S4.5 · *Release:* v1.1 · *Deps:* T17

**Checkpoint 3b:** Testspiel komplett (Aufstellung → Ergebnis); Tabelle erst in v1.1. *Review mit Mensch.*

### Phase 4b: Turniere

- [ ] **T19: Turnier-Modell + öffentliche Anmeldung**
  `Tournament` (Datum, Ort, Format, Anmeldeschluss, Startgeld-Status), öffentliche Detailseite + Anmeldeformulare (Mitglied/Gast mit Name + E-Mail), Teilnehmerliste.
  *Acceptance:* Öffentliche Seite ohne Login erreichbar; 1 Mitgliedsanmeldung + 1 Gastanmeldung landen in der Teilnehmerliste; Gast mit 3 Brettern im Paarungsraster, sobald die Runde existiert.
  *Verify:* `pytest tournaments/` — **Negativtest:** Anmeldung nach Anmeldeschluss abgewiesen; doppelte Anmeldung derselben E-Mail unterbunden; Gast-Daten erscheinen nur in der Turnierverwaltung, nicht in der Mitgliederliste und nicht in der Mitgliedersuche (N1.7). · *Files:* `tournaments/models.py`, `tournaments/views.py` · *Größe:* M · *PRD:* M3.1, M3.2, N1.7 · *Release:* v1 · *Deps:* T17

- [ ] **T20: Runden + Ergebniserfassung + Zwischenwertung**
  Runden anlegen, Paarungen **manuell** erfassen, Ergebnisse je Partie (1/0/½), Zwischenstand (Punkte, Buchholz) — handpaarierbarer Kern des Schweizer Systems, damit v1 ohne automatische Paarung auskommt.
  *Acceptance:* 8 Testspieler, 3 Runden manuell gepaart → Zwischenstand korrekt (Referenzrechnung im Test).
  *Verify:* `pytest tournaments/` — **Negativtest:** Ergebnis ändern nur für Turnierverwalter; Doppelpartien in einer Runde abgewiesen. · *Files:* `tournaments/views.py`, `tournaments/scoring.py` · *Größe:* M · *PRD:* M3.3 · *Release:* v1 · *Deps:* T19

- [ ] **T21: Schweizer Paarung** *(v1.1)*
  Paarungsservice (Buchholz, Bye-Handling, Remis-Regeln), automatische Paarung je Runde — entkoppelt von der Ergebniserfassung (T20).
  *Acceptance:* 8 Testspieler, 3 Runden: Paarungen ohne Doppel-Partien, Stand korrekt (Referenzrechnung).
  *Verify:* `pytest tournaments/` (Paarungs-Tests) — **Negativtest:** Spielerzahl ohne Bye-Regel → klare Fehlermeldung statt stummer Fehlpaarung. · *Files:* `tournaments/pairing.py`, `tournaments/views.py` · *Größe:* L · *PRD:* S3.4 · *Release:* v1.1 · *Deps:* T20

- [ ] **T22: Turnierexport** *(v1.1)*
  Ergebnisliste druckansicht + CSV-Export (ChessResults-tauglich: Spieler, Wertung, Punkte, Runden).
  *Acceptance:* CSV importtestweise in ChessResults-Parser/Excel; Druckansicht A4-freundlich.
  *Verify:* `pytest tournaments/` + manueller Download — **Negativtest:** Nicht-Admin erhält 403 auf CSV-Export; **Inhaltstest:** CSV enthält keine Privatanschriften/Telefonnummern, nur Turnierfelder. · *Files:* `tournaments/views.py`, Templates · *Größe:* S · *PRD:* S3.5 · *Release:* v1.1 · *Deps:* T20

**Checkpoint 4:** Testturnier über 3 Runden manuell gespielt (Handpaarung → Ergebnisse → Zwischenstand); automatische Paarung + Export erst in v1.1. *Review mit Mensch.*

### Phase 5: DSGVO & Betrieb

- [ ] **T23: DSGVO-Auskunfts-Export + Löschfristen**
  Ein-Klick-PDF/HTML-Auskunft je Mitglied (alle personenbezogenen Daten), automatische Anonymisierung nach Austritt + konfigurierbarer Frist (Default 36 Monate, Management-Command), maschinenlesbarer Export der Datenkategorien (Verzeichnis von Verarbeitungstätigkeiten); Auskunfts-Export wird im AuditLog protokolliert (N1.5).
  *Acceptance:* Auskunft enthält alle Felder; Anonymisierung löscht Kontaktdaten, behält Finanzhistorie anonymisiert (nur Mitglied-ID); Frist konfigurierbar.
  *Verify:* `pytest core/` + `python manage.py anonymize_former_members --dry-run` — **Integrationstest:** Vollzyklus Austritt → Frist abgelaufen → Command → alle Felder geprüft; **Negativtest:** `--dry-run` ändert nichts; nach Anonymisierung ist Suche nach Name/E-Mail **leer**, Finanzhistorie aber intakt und anonymisiert. · *Files:* `core/views.py`, `core/management/commands/` · *Größe:* M · *PRD:* N1.2, N1.3, N1.4 · *Release:* v1 · *Deps:* T12

- [ ] **T24: Deployment + Backup + Restore-Doku**
  Produktions-Compose (TLS-Vorbereitung Reverse Proxy), nächtliches DB-Backup (pg_dump-Container, komprimiert + **verschlüsselt**, Schlüssel getrennt vom DB-Host), `docs/deployment.md` inkl. Restore-Anleitung, Restore-Test-Protokoll, Updatepfad (`docker compose pull` + `migrate`) und Nachweis des EU/DE-Hoststandorts.
  *Acceptance:* Restore-Test dokumentiert und einmal erfolgreich (< 4 h), inklusive Entschlüsselung; ein Update auf eine neue Image-Version läuft per dokumentiertem Ablauf ohne Datenverlust; `docs/deployment.md` nennt Server/Provider mit EU/DE-Standort und erklärt, warum damit N1.1 erfüllt ist (keine Tracker, kein externes CDN, keine Drittanbieter-Fonts/-CDN in den Templates).
  *Verify:* **Integrationstest:** Backup → leere DB → Restore → Daten da + Integritäts-Abgleich (Zeilenanzahl/Stichprobe); **Negativtest:** korruptes Backup bzw. fehlender Schlüssel wird mit klarem Fehler abgewiesen statt stillschweigend leeren Datenbestand zu schreiben; **Update-Test:** Pull + `migrate` gegen eine frisch befüllte Kopie, danach Zeilenanzahl unverändert. · *Files:* `docker-compose.prod.yml`, `docs/deployment.md` · *Größe:* M · *PRD:* N2.1, N2.4, N1.1 · *Release:* v1 · *Deps:* T23

- [ ] **T25: Härtung: Header, Fehlalarme, Wartungsdoku**
  Sicherheits-Header (HSTS, X-Frame, CSRF), Fehlerbenachrichtigung per E-Mail an Admin, Wartungsdoku `docs/wartung.md` (Django-Primer für den Nutzer). *(2FA ausgeschlossen → T26, v1.1)*
  *Acceptance:* Jeder der 3 Header per Response-Check nachgewiesen; erzwungener Serverfehler erzeugt genau eine E-Mail an die Admin-Adresse mit Traceback im Log (nicht im Mail-Body); Nutzer kann jeden Wartungsschritt aus `docs/wartung.md` nachvollziehen.
  *Verify:* `pytest core/` (Header-Test je Header, Fehlermail-Test) + `docker compose -f docker-compose.prod.yml config` · *Files:* `config/settings.py`, `docs/wartung.md` · *Größe:* M · *PRD:* N2.5 · *Release:* v1 · *Deps:* T24

- [ ] **T25b: NFR-Nachweis — Performance + Barrierefreiheit**
  Messung statt Behauptung: Performance-Messskript für die Kernflächen (Login, Dashboard, Mitgliederliste+Suche, Aufstellung, Turnieranmeldung) und ein WCAG-2.1-AA-Auditschnitt über genau diese Flächen. Ergebnis wird in `docs/nfr-pruefung.md` festgehalten (Messwert, Messmethode, Datum, Uhrzeit/Netzwerk).
  *Acceptance:* Für jede der 5 Kernflächen liegt ein Messwert vor; Seitenladen < 1 s und Suche < 500 ms auf dem Vereinsserver; Kontraste, Formular-Labels, Tastaturbedienung und Fokus-Reihenfolge geprüft — schwere Verstöße (A/AA) sind 0, oder als dokumentierte Ausnahme mit Begründung im PRD-§7-Erfolgskriterium vermerkt.
  *Verify:* `pytest core/` (automatisierbare Teilprüfungen: Label-Zuordnung je Formular, Kontrast der Textfarben, fehlende Alt-Texte) + manueller Audit-Durchgang mit Tastatur · **Negativtest:** Auf 360 px darf kein horizontales Overflow entstehen (bereits in T1 angelegt, hier für alle Kernflächen bestätigt). · *Files:* `core/tests/test_a11y.py`, `scripts/measure_perf.py`, `docs/nfr-pruefung.md` · *Größe:* M · *PRD:* N2.2, N2.3 · *Release:* v1 · *Deps:* T25

- [ ] **T26: 2FA für Admins** *(v1.1)*
  2FA für Admin-Gruppe (django-otp) — PRD N1.6 führt es als Sollte; Härtungs-Grundlage (T25) läuft in v1.
  *Acceptance:* Admin-Login erfordert 2FA; Bestätigung/Verfahrens-Setup im Admin-Profil.
  *Verify:* `pytest core/` — **Negativtest:** Admin-Login ohne gültiges Token abgewiesen; Rollen „mitglied"/„kapitaen" bleiben ohne 2FA. · *Files:* `config/settings.py`, `core/` · *Größe:* S · *PRD:* N1.6 · *Release:* v1.1 · *Deps:* T25

- [ ] **T27: PWA — installierbare App**
  `manifest.webmanifest` (Name, Icons, `display: standalone`, Farbschema), Service Worker (App-Shell + Startseite/News aus Cache, Network-First für den Rest), iOS-Meta-Tags (apple-touch-icon, Statusbar), Registrierung im Basis-Template, Versions-/Cache-Invalidierung bei Deploy.
  *Acceptance:* „Zum Homescreen hinzufügen" auf Android + „Zum Bildschirm hinzufügen" auf iOS funktioniert; App öffnet sich ohne Browser-UI; Startseite lädt offline aus dem Cache; Update löscht alten Cache.
  *Verify:* `pytest core/` (SW-Route, Manifest-Route) + manuell Chrome DevTools → Application → Add to home screen — **Negativtest:** nach Deploy ist der alte Cache invalidiert (neue Version sichtbar, kein „stale content"); offline erscheint nur Startseite/News, **keine** angeforderten Seiten werden mit veralteten Daten aus Cache bedient. · *Files:* `core/templates/`, `static/manifest.webmanifest`, `static/sw.js` · *Größe:* M · *PRD:* N2.7 · *Release:* v1 · *Deps:* T25

**Checkpoint Final (v1):** Alle PRD-Erfolgskriterien durchgegangen, DSGVO-Checkliste (PRD §4.1 N1.1–N1.5, N1.7) abgehakt, NFR-Nachweis (T25b) in `docs/nfr-pruefung.md` abgelegt, Traceability-Tabelle oben abgeglichen, Berechtigungsmatrix (§3.8) gegen die Tests geprüft, Abnahme durch Vorstand. **Danach erst v1.1-Tasks:** T15, T18, T21, T22, T26 (+ optional Newsletter S5.3).

## Release-Schnitt

- **v1 (Kern — alle M-Anforderungen):** T1–T14 (inkl. T11b), T16, T17, T19, T20, T23, T24, T25, T25b, T27
- **v1.1 (S-Anforderungen — erst nach v1-Abnahme):** T15 Kassenbuch, T18 Tabellen, T21 Paarung, T22 Turnierexport, T26 2FA
- **Out of scope (K):** DSB-Meldeformate (K3.6), SMS/Erinnerungen (K5.4), DATEV (K6.3)

**Traceability-Check (bei jedem Checkpoint):** Jede M- und N-ID aus `docs/prd.md` ist genau einer v1-Task zugeordnet.

| PRD-ID | Task |
|---|---|
| M1.1–M1.6 | T3 (Stammdaten/Liste/CSV), T2 (Rollen), T4 (Selbstbedienung) |
| M2.1 / M2.2 / M2.3 / M2.4 / M2.5 / M2.6 | T7 / T8 / T9 / T9 / T10 / T11b |
| M3.1 / M3.2 / M3.3 | T19 / T19 / T20 |
| M4.1 / M4.2 / M4.3 / M4.4 | T16 / T16 / T17 / T17 |
| M5.1 / M5.2 | T13 / T14 |
| M7.1 / M7.2 / M7.3 | T6 + T11 / T1 + T2 / T5 |
| N1.1 | T24 (Hoststandort + kein CDN/Tracker) |
| N1.2 / N1.3 / N1.4 | T23 |
| N1.5 | T5 (Logins/Änderungen) + T12 (Detail-Zugriffe) |
| N1.6 | T26 *(v1.1 — im PRD als S geführt)* |
| N1.7 | T19 |
| N2.1 / N2.4 | T24 |
| N2.2 / N2.3 | T25b |
| N2.5 | T25 |
| N2.6 / N2.7 | T1 / T27 |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Django unbekannt beim Nutzer | Med | Admin-first-Ansatz, `docs/wartung.md`, keine exotischen Packages |
| Schweizer Paarung falsch implementiert | Med (v1.1) | Handpaarung als v1-Fallback; Referenz-Tests mit bekannten Turnierdaten; manuelle Abnahme 3 Runden |
| E-Mail-Zustellung selbst gehostet (SPF/DKIM) | Med | Versand-Protokoll; Provider-/Zusteller-Doku (SPF, DKIM, DMARC) in `docs/deployment.md`, Abschnitt „E-Mail-Versand"; optional SMTP des Hosters |
| Umfang zu groß für eine Session | Med | **v1/v1.1-Split:** v1 = alle M-Tasks, v1.1 = S-Tasks erst nach Abnahme; Checkpoints nach je 3–5 Tasks |
| Datenverlust auf Vereinsserver | Hoch | T24: tägliche verschlüsselte Backups + dokumentierter Restore-Test inkl. Entschlüsselung |
| DSGVO-Anforderung („Zugriffe") unvollständig umgesetzt | Med | T12 protokolliert Detailansichten; N1.5 definiert „Zugriff" konkret; Audit-Logs ≥ 12 Monate; Berechtigungsmatrix §3.8 mit Negativtests |
| NFRs (Performance, WCAG, Updatepfad) behauptet, aber nie gemessen — Abnahme verläuft auf Datenlage | Med | T25b misst die 5 Kernflächen und schreibt Messwert/Methodik/Datum in `docs/nfr-pruefung.md`; T24 testet den Updatepfad; T25b zählt zu v1, nicht zu v1.1 |
| Gastdaten (Name/E-Mail aus Turnieranmeldung) als Personendaten Dritter übersehen | Med | N1.7 definiert Zweck, Sichtbarkeit und Löschfrist; T19 prüft explizit, dass Gastdaten in Mitgliedersuche/-listen nicht auftauchen |

## Open Questions

- SMTP-Zugangsdaten des Vereins (vor T14 nötig — vorerst Django-Console-Backend im Dev)
- Exakte Beitragssätze und Kategorien des Vereins (vor T7)
- Domain/Hostname für das Deployment (vor T24)
- Aufbewahrungsfristen mit Steuerberater bestätigen (vor T23): Default 36 Monate bis Anonymisierung, 8 Jahre anonymisierte Finanzhistorie (GoBD/§ 147 AO)
