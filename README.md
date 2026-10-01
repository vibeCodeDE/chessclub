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

## Produkt-Landingpage

Die Verkaufsseite für andere Vereine liegt unter `/produkt/` (in der bisherigen Gestaltung;
`/` bleibt die Vereinsseite im neuen Design).
Name und Kontakt kommen aus `PRODUCT_NAME` und `PRODUCT_CONTACT`; Preise, Funktionen und FAQ
stehen in `core/produkt.py`. Die Preise sind **Platzhalter**, `/impressum/` und `/datenschutz/`
enthalten nur Platzhaltertexte und müssen vor dem Livegang ersetzt werden.

## Tests

```bash
.venv/bin/python -m pytest          # 343 Tests (1 Skip: nur mit PostgreSQL)
.venv/bin/python -m ruff check .    # Lint
.venv/bin/python manage.py check
```

Die GitHub-Actions-Pipeline (`.github/workflows/ci.yml`) fährt genau diese
Schritte gegen PostgreSQL 16 plus `manage.py check --deploy` mit den
Produktions-Settings.

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

Oberflächen: öffentliche Vereinsseite (`/`, `/aktuelles/`, `/turniere/`, `/verein/`,
`/mitglied-werden/`), Verwaltungs-Shell (`/dashboard/`) und die Django-Administration
(`/admin/`) als Rückfallebene für den Vorstand.

**Zwei getrennte Design-Systeme** (kein CSS-Buildschritt, keine externen Assets, PRD N1.1):

| Bereich | Stylesheet | Skript | Hülle |
| --- | --- | --- | --- |
| Öffentliche Vereinsseite (inkl. Anmeldung, 2FA, Passwort-Reset) | `static/css/site.css` | `static/js/public.js` | `templates/public_base.html`, `templates/auth_base.html` |
| Verkaufsseite `/produkt/` (bewusst ohne Skript, ADR-014) | `static/css/site.css` | — | `templates/produkt_base.html` |
| Verwaltung/Dashboard/Admin | `static/css/app.css` | `static/js/app.js` | `templates/base.html` |

Der öffentliche Teil folgt der Designsprache aus
`schachclubmanager-modern-web-design (1).zip` – Entscheidung und Details in
[ADR-013](docs/decisions/ADR-013-oeffentliche-designsprache.md) und der
[Spec](docs/superpowers/specs/2026-09-30-oeffentliche-designsprache.md).
Das interne Design wird separat gepflegt; die beiden Stylesheets überschreiben sich nicht.
Beispielbilder liegen unter `static/img/` und sind für echte Vereinsfotos austauschbar.

### Vereinsprofil der öffentlichen Seiten

Diese optionalen Umgebungsvariablen steuern den öffentlichen Auftritt; leere Werte
blenden die betroffene Zeile aus, statt einen Platzhalter zu erfinden (ADR-012):

| Variable | Beispiel | Wirkung |
| --- | --- | --- |
| `CLUB_FOUNDED` | `1978` | „Schachverein seit …“, Vereinsjubiläum-Kachel |
| `CLUB_LOCATION` | `Musterstadt` | Ort in Hero, Fußzeile, Seitentiteln |
| `CLUB_ROOM` | `Vereinsheim Musterstadt, Musterstraße 1` | Treffpunkt auf Startseite, `/verein/` und Beitragsseite |
| `CLUB_NIGHT_HOURS` | `Donnerstags ab 19:00 Uhr` | Klubabend, Wochenband, Mitmach-Abschnitt |
| `CLUB_YOUTH_HOURS` | `Donnerstags 17:30 – 19:00 Uhr` | Jugendtraining |
| `CLUB_DESCRIPTION` | `Schach für alle – vom ersten Bauernzug bis zur Ligapartie.` | Kurztext in der Fußzeile |

`/verein/` ist die öffentliche Vereinsseite (Selbstverständnis, Zeiten, Ligaspielplan);
alle Angaben dort kommen aus der Datenbank bzw. aus den obigen Variablen.

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
