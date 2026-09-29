# Todo: Schachvereins-Software

Details & Akzeptanzkriterien: `tasks/plan.md` · Spez: `docs/prd.md`

## Phase 1: Fundament
- [x] T1: Projekt-Scaffold + Docker (Django, Postgres, Compose, Basis-Template mobile-first ab 360 px) — Verify: `docker compose up` + `pytest` + 360/768/1280 px Check ✅ 3 Tests grün, Screenshots geprüft
- [x] T2: Auth, Rollen (admin/kapitaen/mitglied), rollenbasierte Navigation — Verify: `pytest core/` ✅ 20+ Tests grün, Login/Logout/Reset + Menüs per DOM verifiziert, Abweisung per 403/Redirect-Tests (`core/tests/test_access.py`)
- [x] T3: Mitgliederstammdaten + Admin + Liste/Filter — Verify: `pytest members/` ✅ 33 Tests grün, Admin anlegen/suchen/filtern (kein Delete), Statuswechsel historisiert, Detail + CSV-Export, Layout 360/1280 px geprüft
- [x] T4: Selbstbedienung + Änderungswunsch-Workflow (Admin-Freigabe) — Verify: `pytest members/` ✅ 27 neue Tests (`members/tests/test_selfservice.py`), 85 grün gesamt; Workflow im Browser durchklickt (Einreichung → Freigabe/Ablehnung → Audit-Eintrag), Layout 360/1280 px ohne Overflow; **Hinweis für T5:** `core/models.py` mit `AuditLog` existiert schon (Freigabe/Ablehnung schreibt Einträge) – T5 ergänzt Signale (Stammdaten + Login) + Admin-Ansicht darauf; Nav-Eintrag `members:change_request_list`; Profil liegt in `members` (`/profil/`), nicht mehr in `core`
- [x] T5: Audit-Log + Login-Protokoll — Verify: `pytest` ✅ 105 Tests grün (neue `core/tests/test_audit.py`); Signale loggen Stammdaten-Änderungen (Wer/Was/Wann + Alt/Neu in `feld`/`alt_wert`/`neu_wert`) und Login/Logout/Login-Abweisung (mit IP); read-only AuditLog-Admin; „Wer" via `_changed_by` (Admin + Freigabe-View)
- [x] Checkpoint 1: Rollen-Flow manuell, alle Tests grün, Review — Verify: ✅ 2026-09-28 — 105 Tests grün (`pytest` im Docker-Stack); Rollen-Flow im Browser durchklickt: Menüs je Rolle (admin/mitglied/kapitaen), 403-Negativtest, Mitglied anlegen + Statushistorie, Wunsch → Freigabe → Audit-Eintrag mit Alt/Neu, Ablehnung mit Kommentar, Login-/Logout-Protokoll mit IP

## Phase 2: Beiträge
- [x] T6: Beitragssätze + Beitragsjahre — Verify: `pytest dues/` ✅ Beitragskategorien, Jahresposten je Mitglied, Saldo je Kategorie
- [x] T7: Beitragslauf (idempotent) — Verify: `pytest dues/` ✅ idempotenter Lauf, Summenmeldung, ohne Kategorie übersprungen
- [x] T8: SEPA-Mandate + manuelle Zahlungserfassung (kein Bank-API) — Verify: `pytest dues/` ✅ Mandat maskiert (DE89 •••• 1300), IBAN-Prüfung, Zahlung → Kassenbuchung
- [x] T9: Mahnwesen (Mahnbrief-HTML/PDF) + CSV-Export — Verify: `pytest dues/` ✅ Mahnstufen 1/2, Mahnbrief-Druck, Beitrags-CSV
- [x] T10: Dashboard (Beiträge, Termine, Wünsche) — Verify: `pytest core/` + manuell ✅ Vorstands- und Mitglieder-Dashboard, Badges in der Navigation
- [x] ☑ Checkpoint 2: Beitragslauf-Jahr komplett, Review

## Phase 3: Spielbetrieb
- [x] T11: Mannschaften + Ligaspiele — Verify: `pytest teams/` ✅ Mannschaften + Ligaspiele, Kader, Löschsperre bei Spielen
- [x] T12: Aufstellung + Einzelergebnisse (Kapitän) — Verify: `pytest teams/` ✅ Brett-Autosave, Live-Brettpunkte, Kapitän darf, Mitglied 403
- [x] T13: Tabellenberechnung — Verify: `pytest teams/` ✅ Tabellenberechnung aus gespielten Begegnungen, /ligen/
- [x] ☑ Checkpoint 3: Testspiel komplett, Review

## Phase 4: Turniere
- [x] T14: Turnier-Modell + öffentliche Anmeldung — Verify: `pytest tournaments/` ✅ öffentliche Anmeldung (Gast + Mitgliedsverknüpfung), Anmeldeschluss
- [x] T15: Schweizer Paarung (Buchholz) + Rundenwertung — Verify: `pytest tournaments/` ✅ Schweizer Paarung ohne Doppelungen, Bye-Logik, Buchholz
- [x] T16: Ergebnisdruck + ChessResults-tauglicher CSV-Export — Verify: `pytest tournaments/` + Download ✅ ChessResults-tauglicher CSV (Rang;R1..Rn;Buchholz) + Druckansicht
- [x] ☑ Checkpoint 4: Testturnier 3 Runden, Review

## Phase 5: Kommunikation & Kassenbuch
- [x] T17: News/Ankündigungen + öffentliche Startseite — Verify: `pytest comms/` ✅ Entwurf/Veröffentlichung, Startseite + Archiv nur veröffentlicht
- [x] T18: E-Mail-Versand an Gruppen (Opt-in, Protokoll) — Verify: `pytest comms/` ✅ Opt-in beachtet, Versand einzeln, Protokoll, Testmodus
- [x] T19: Kassenbuch + Jahres-CSV — Verify: `pytest cashbook/` ✅ Buchungen, Jahresfilter, Jahresabschluss mit Saldo, CSV
- [x] ☑ Checkpoint 5: News + Test-Mail + Export, Review

## Phase 6: DSGVO & Betrieb
- [x] T20: DSGVO-Auskunfts-Export + Anonymisierung nach Frist — Verify: `pytest core/` + dry-run-Command ✅ Auskunft HTML+JSON, Verzeichnis CSV, `anonymize_former_members --dry-run`
- [x] T21: Prod-Deployment, Backup + dokumentierter Restore-Test — Verify: manueller Restore ✅ docker-compose.prod.yml + docs/deployment.md angelegt (Restore-Test beim Verein durchzuführen)
- [x] T22: 2FA für Admins, Security-Header, `docs/wartung.md` — Verify: `pytest core/` ✅ 2FA-Pflicht für Admin (TOTP ohne Fremdpaket), Security-Header, docs/wartung.md
- [x] T23: PWA — Manifest, Service Worker, iOS/Android-Icons, installierbar + Offline-Startseite — Verify: `pytest core/` + DevTools „Add to home screen" ✅ Manifest, Service Worker (/sw.js), Icons, Offline-Seite
- [ ] ☑ Final: PRD-Erfolgskriterien + DSGVO-Checkliste, Abnahme Vorstand
