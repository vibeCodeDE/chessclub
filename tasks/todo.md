# Todo: Schachvereins-Software

Details & Akzeptanzkriterien: `tasks/plan.md` · Spez: `docs/prd.md`

## Phase 1: Fundament
- [x] T1: Projekt-Scaffold + Docker (Django, Postgres, Compose, Basis-Template mobile-first ab 360 px) — Verify: `docker compose up` + `pytest` + 360/768/1280 px Check ✅ 3 Tests grün, Screenshots geprüft
- [x] T2: Auth, Rollen (admin/kapitaen/mitglied), rollenbasierte Navigation — Verify: `pytest core/` ✅ 20+ Tests grün, Login/Logout/Reset + Menüs per DOM verifiziert, Abweisung per 403/Redirect-Tests (`core/tests/test_access.py`)
- [x] T3: Mitgliederstammdaten + Admin + Liste/Filter — Verify: `pytest members/` ✅ 33 Tests grün, Admin anlegen/suchen/filtern (kein Delete), Statuswechsel historisiert, Detail + CSV-Export, Layout 360/1280 px geprüft
- [ ] T4: Selbstbedienung + Änderungswunsch-Workflow (Admin-Freigabe) — Verify: `pytest members/`
- [ ] T5: Audit-Log + Login-Protokoll — Verify: `pytest core/`
- [ ] ☑ Checkpoint 1: Rollen-Flow manuell, alle Tests grün, Review

## Phase 2: Beiträge
- [ ] T6: Beitragssätze + Beitragsjahre — Verify: `pytest dues/`
- [ ] T7: Beitragslauf (idempotent) — Verify: `pytest dues/`
- [ ] T8: SEPA-Mandate + manuelle Zahlungserfassung (kein Bank-API) — Verify: `pytest dues/`
- [ ] T9: Mahnwesen (Mahnbrief-HTML/PDF) + CSV-Export — Verify: `pytest dues/`
- [ ] T10: Dashboard (Beiträge, Termine, Wünsche) — Verify: `pytest core/` + manuell
- [ ] ☑ Checkpoint 2: Beitragslauf-Jahr komplett, Review

## Phase 3: Spielbetrieb
- [ ] T11: Mannschaften + Ligaspiele — Verify: `pytest teams/` (NAV-Eintrag `teams:team_list` in `core/context_processors.py` wieder ergänzen)
- [ ] T12: Aufstellung + Einzelergebnisse (Kapitän) — Verify: `pytest teams/`
- [ ] T13: Tabellenberechnung — Verify: `pytest teams/`
- [ ] ☑ Checkpoint 3: Testspiel komplett, Review

## Phase 4: Turniere
- [ ] T14: Turnier-Modell + öffentliche Anmeldung — Verify: `pytest tournaments/`
- [ ] T15: Schweizer Paarung (Buchholz) + Rundenwertung — Verify: `pytest tournaments/`
- [ ] T16: Ergebnisdruck + ChessResults-tauglicher CSV-Export — Verify: `pytest tournaments/` + Download
- [ ] ☑ Checkpoint 4: Testturnier 3 Runden, Review

## Phase 5: Kommunikation & Kassenbuch
- [ ] T17: News/Ankündigungen + öffentliche Startseite — Verify: `pytest comms/`
- [ ] T18: E-Mail-Versand an Gruppen (Opt-in, Protokoll) — Verify: `pytest comms/`
- [ ] T19: Kassenbuch + Jahres-CSV — Verify: `pytest cashbook/`
- [ ] ☑ Checkpoint 5: News + Test-Mail + Export, Review

## Phase 6: DSGVO & Betrieb
- [ ] T20: DSGVO-Auskunfts-Export + Anonymisierung nach Frist — Verify: `pytest core/` + dry-run-Command
- [ ] T21: Prod-Deployment, Backup + dokumentierter Restore-Test — Verify: manueller Restore
- [ ] T22: 2FA für Admins, Security-Header, `docs/wartung.md` — Verify: `pytest core/`
- [ ] T23: PWA — Manifest, Service Worker, iOS/Android-Icons, installierbar + Offline-Startseite — Verify: `pytest core/` + DevTools „Add to home screen"
- [ ] ☑ Final: PRD-Erfolgskriterien + DSGVO-Checkliste, Abnahme Vorstand
