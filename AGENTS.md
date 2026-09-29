# AGENTS.md

Schachvereins-Software (Django 5, PostgreSQL, Docker Compose). Einstieg und Befehle: `README.md`.

## Quellen der Wahrheit

- Anforderungen: `docs/prd.md` (Berechtigungsmatrix §3.8 ist verbindlich).
- Task-Status: **nur** `tasks/plan.md` (Checkboxen). `tasks/todo.md` ist nur das Protokoll erledigter Tasks mit Belegen.
- Entscheidungen: `docs/decisions/` (ADRs) und `docs/superpowers/specs/`.

## Regeln

- Sprache: Deutsch (UI, Daten, Doku). Code-Bezeichner wie im Bestand.
- Tests zuerst; jede Task braucht mindestens einen **Negativtest** (403, Randfall, Dry-Run). Rollen-Tests je Zeile der Matrix.
- Regelbasis als reine Funktionen in `services.py` bzw. Fachmodulen (ohne HTTP-Kontext, keine N+1-Abfragen, `assertNumQueries` im Test); Views bleiben dünn (Function-Based Views).
- Finanzdaten werden nie gelöscht: Korrektur per Gegenbuchung/Audit-Spur (ADR-005, ADR-006).
- Kein Bank-API-Zugriff, keine IBAN im System (ADR-002); keine Netzwerk-Imports in `dues`.
- Personenbezogene Änderungen/Zugriffe gehen in den `AuditLog`.
- Keine Drittanbieter-Assets (CDN, Fonts, Tracker) – DSGVO N1.1.

## Doku-Pflege

- **Traceability:** Jede PRD-ID gehört genau einer Task. Änderungen an Anforderungen und Plan im selben Commit nachziehen.
- Task-IDs nie wiederverwenden; Nachträge mit `b`-/`c`-Suffix (T11b).
- Design-Details gehören in eine Spec oder ADR, in `plan.md` nur ein Absatz plus Link. Keine Wiederholung in `todo.md`.
- Neue bedeutende Entscheidung → neue ADR (`docs/decisions/ADR-NNN-titel.md`); alte ADRs nicht löschen, sondern per neuer ADR ablösen.
- PRD-Änderungen im Änderungsverlauf (§9) vermerken.

## Verifikation vor „fertig“

`docker compose exec app pytest` muss grün sein; bei UI-Änderungen zusätzlich Browser-Check bei 360 px und 1280 px ohne horizontalen Overflow.
