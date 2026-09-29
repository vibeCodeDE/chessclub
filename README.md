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
.venv/bin/python -m pytest          # 289 Tests, 1 Skip (nur mit PostgreSQL)
.venv/bin/python manage.py check
```

## Produktivbetrieb

```bash
cp .env.prod.example .env.prod      # Werte ausfüllen
docker compose -f docker-compose.prod.yml up -d --build
```

Betrieb, Backup und Wiederherstellung: `docs/deployment.md`.
Wartung für die Vorstandschaft: `docs/wartung.md`.

Für Demos und Vorschauen läuft die App auch auf Vercel (PostgreSQL über `DATABASE_URL`,
Migrationen im Build): `docs/deployment.md`, Abschnitt 8.

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

## Dokumentation

| Datei | Inhalt |
| --- | --- |
| `docs/prd.md` | Anforderungen und Erfolgskriterien (Ausgangsbasis) |
| `docs/abnahme.md` | Abnahme-Checkliste: Erfolgskriterien, Meilensteine, DSGVO |
| `docs/deployment.md` | Installation, TLS, Backup, Restore, Updates, Vercel-Demo |
| `docs/wartung.md` | Kurzanleitung für wiederkehrende Aufgaben |
| `tasks/plan.md`, `tasks/todo.md` | Arbeitspakete und Umsetzungsstand |

## Datenschutz

Personenbezogene Daten bleiben in der eigenen Datenbank. Auskunft (PDF/JSON),
Verzeichnis der Verarbeitungstätigkeiten (CSV) und die Anonymisierung nach
Austritt sind eingebaut; Details und Restpunkte stehen in `docs/abnahme.md`.
