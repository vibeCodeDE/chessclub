# Schachvereins-Software

Selbst gehostete Web-App für einen Schachverein (< 200 Mitglieder): Mitglieder, Beiträge (SEPA-Status, Mahnwesen), Mannschaften, Turniere, News/E-Mail und Kassenbuch. Deutsch, DSGVO-konform, Single-Tenant.

Stack: Django 5 · PostgreSQL 16 · serverseitige Templates + Tailwind · Docker Compose. Begründung: [ADR-001](docs/decisions/ADR-001-django-stack.md).

## Schnellstart (Entwicklung)

Voraussetzung: Docker mit Compose.

```bash
docker compose up -d --build        # App unter http://localhost:8000, Migrationen laufen beim Start
docker compose exec app python manage.py createsuperuser
docker compose exec app pytest      # Testlauf
```

Die Gruppen `admin`, `kapitaen`, `mitglied` und Platzhalter-Beitragssätze werden per Migration angelegt. Die echten Beitragssätze werden im Django-Admin unter *Dues → Beitragskategorien* eingetragen, bevor der erste echte Beitragslauf startet.

## Befehle

| Befehl | Zweck |
|---|---|
| `docker compose up -d --build` | Stack starten (App + Postgres) |
| `docker compose exec app pytest` | alle Tests |
| `docker compose exec app pytest dues/` | Tests einer App |
| `docker compose exec app python manage.py makemigrations` | Migrationen erzeugen |
| `npm install && npm run build:css` | Tailwind neu bauen (nur bei Style-Änderungen; das gebaute `static/css/tailwind.css` ist eingecheckt) |
| `npm run watch:css` | Tailwind im Watch-Modus |

## Konfiguration

Umgebungsvariablen (Defaults in `config/settings.py`, Dev-Werte in `docker-compose.yml`):

| Variable | Bedeutung |
|---|---|
| `DJANGO_SECRET_KEY` | Secret Key – im Betrieb **zwingend** ändern |
| `DJANGO_DEBUG` | `1` = Debug (nur Entwicklung) |
| `DJANGO_ALLOWED_HOSTS` | kommaseparierte Hostnamen |
| `POSTGRES_DB` / `_USER` / `_PASSWORD` / `_HOST` / `_PORT` | Datenbank |

Ein produktives Compose-Setup (TLS, verschlüsselte Backups) ist mit Task T24 geplant; bis dahin ist der Stack nur für Entwicklung gedacht.

## Projektstruktur

| Ordner | Inhalt |
|---|---|
| `config/` | Django-Projekt (Settings, URLs) |
| `core/` | Auth, Rollen, Navigation, Dashboard, Audit-Log |
| `members/` | Mitgliederstammdaten, Selbstbedienung, Änderungswünsche |
| `dues/` | Beitragssätze, Beitragslauf, Zahlungen, Mahnwesen |
| `verein/` | Vereinsdaten (Absender/Kontakt für Briefe und E-Mail) |
| `templates/`, `static/`, `src/` | Templates, gebautes CSS, Tailwind-Quelle |

Weitere Apps (`teams`, `tournaments`, `comms`, `cashbook`) folgen laut Plan.

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [`docs/prd.md`](docs/prd.md) | Anforderungen, Berechtigungsmatrix (§3.8), Release-Schnitt v1/v1.1 |
| [`tasks/plan.md`](tasks/plan.md) | Implementierungsplan mit Tasks, Acceptance, Traceability; **einzige Quelle für den Task-Status** |
| [`tasks/todo.md`](tasks/todo.md) | Fortschrittsprotokoll mit Verifikationsbelegen, nächste Schritte |
| [`docs/decisions/`](docs/decisions/) | Architekturentscheidungen (ADRs) |
| [`docs/superpowers/specs/`](docs/superpowers/specs/) | Detail-Design je Task |
| [`docs/superpowers/plans/`](docs/superpowers/plans/) | Schritt-für-Schritt-Umsetzungspläne je Task |

Geplant, aber noch nicht vorhanden: `docs/deployment.md` (T24), `docs/wartung.md` (T25), `docs/nfr-pruefung.md` (T25b).

## Arbeitsweise

- Tests zuerst (TDD); jede Task enthält mindestens einen Negativtest.
- Rollen und Rechte folgen der Matrix in PRD §3.8; jede Zeile hat einen Negativtest.
- Personenbezogene Änderungen und Zugriffe laufen über den `AuditLog` (PRD M7.3, N1.5).
- Keine Drittanbieter-Tracker, kein externes CDN (PRD N1.1).
