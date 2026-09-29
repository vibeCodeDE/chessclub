# Schachvereins-Verwaltung

Vereinsverwaltung für den Schachclub Königsspringer Musterstadt e.V. – Mitglieder,
Beiträge, Spielbetrieb, Turniere, Kommunikation und Kassenbuch in einer Anwendung.
Servergerendert mit Django, Datenhaltung ausschließlich auf eigener Infrastruktur
(keine Tracker, keine externen CDNs).

## Schnellstart (Entwicklung)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo          # realistische Demo-Daten
.venv/bin/python manage.py runserver
```

Für die lokale Vorführung ist Zwei-Faktor abgeschaltet; im Produktivbetrieb ist sie
für die Vorstandsgruppe verpflichtend.

```bash
TWOFA_PFLICHT=0 .venv/bin/python manage.py runserver
```

Alternativ über Docker Compose (App plus PostgreSQL, Migrationen laufen beim Start):

```bash
docker compose up -d --build
docker compose exec app pytest
```

### Anmeldung mit Demo-Daten

| Benutzer | Rolle | Passwort |
| --- | --- | --- |
| `vorstand` | Vorstand (Rolle admin) | `schach2026` |
| `kassenwart` | Vorstand (Rolle admin) | `schach2026` |
| `kapitaen` | Mannschaftsführer | `schach2026` |
| `mitglied` | Mitglied | `schach2026` |

`manage.py seed_demo --reset` löscht die Demo-Daten und legt sie neu an.

## Tests

```bash
.venv/bin/python -m pytest          # 252 Tests, 1 Skip (nur mit PostgreSQL)
.venv/bin/python manage.py check
```

## Produktivbetrieb

```bash
cp .env.prod.example .env.prod      # Werte ausfüllen
docker compose -f docker-compose.prod.yml up -d --build
```

Betrieb, Backup und Wiederherstellung: `docs/deployment.md`.
Wartung für die Vorstandschaft: `docs/wartung.md`.

## Aufbau

| App | Inhalt |
| --- | --- |
| `core` | Rollen, Navigation, Dashboard, Audit-Protokoll, Suche, DSGVO, 2FA, PWA |
| `members` | Mitgliederstammdaten, Statusverlauf, Änderungswunsch-Workflow |
| `dues` | Beitragskategorien, Beitragslauf, Zahlungen, Mahnwesen, SEPA-Mandate |
| `teams` | Mannschaften, Ligaspiele, Aufstellungen, Tabellenberechnung |
| `tournaments` | Turnierverwaltung, öffentliche Anmeldung, Schweizer Paarung |
| `comms` | Ankündigungen mit Entwurfs-Workflow, Gruppen-E-Mails mit Opt-in |
| `cashbook` | Kassenbuch, Jahresabschluss, CSV-Export |

Oberflächen: öffentliche Vereinsseite (`/`), Verwaltungs-Shell (`/dashboard/`) und
die Django-Administration (`/admin/`) als Rückfallebene für den Vorstand.

Styles liegen als handgeschriebenes Design-System in `static/css/app.css`; es gibt
keinen CSS-Buildschritt und keine externen Assets (PRD N1.1).

## Dokumentation

| Datei | Inhalt |
| --- | --- |
| `docs/prd.md` | Anforderungen, Berechtigungsmatrix (§3.8), Release-Schnitt v1/v1.1 |
| `docs/abnahme.md` | Abnahme-Checkliste: Erfolgskriterien, Meilensteine, DSGVO |
| `docs/deployment.md` | Installation, TLS, Backup, Restore, Updates |
| `docs/wartung.md` | Kurzanleitung für wiederkehrende Aufgaben |
| `tasks/plan.md` | Implementierungsplan mit Tasks, Acceptance, Traceability; **einzige Quelle für den Task-Status** |
| `tasks/todo.md` | Fortschrittsprotokoll mit Verifikationsbelegen, nächste Schritte |
| `docs/decisions/` | Architekturentscheidungen (ADRs) |
| `docs/superpowers/specs/` | Detail-Design je Task |
| `docs/superpowers/plans/` | Schritt-für-Schritt-Umsetzungspläne je Task |
| `docs/abnahmen/` | Abnahmebelege je abgeschlossener Task |

## Datenschutz

Personenbezogene Daten bleiben in der eigenen Datenbank. Auskunft (PDF/JSON),
Verzeichnis der Verarbeitungstätigkeiten (CSV) und die Anonymisierung nach
Austritt sind eingebaut; Details und Restpunkte stehen in `docs/abnahme.md`.
Es gibt keinen Bank-API-Zugriff und keinen automatisierten SEPA-Einzug
([ADR-002](docs/decisions/ADR-002-kein-automatisierter-sepa-einzug.md)).

## Arbeitsweise

- Tests zuerst (TDD); jede Task enthält mindestens einen Negativtest.
- Rollen und Rechte folgen der Matrix in PRD §3.8; jede Zeile hat einen Negativtest.
- Personenbezogene Änderungen und Zugriffe laufen über den `AuditLog` (PRD N1.5).
- Keine Drittanbieter-Tracker, kein externes CDN (PRD N1.1).
- Finanzdaten werden nie gelöscht, sondern per Gegenbuchung korrigiert
  ([ADR-006](docs/decisions/ADR-006-storno-per-gegenbuchung.md)).
