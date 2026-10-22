# Schachvereins-Verwaltung

Moderne Vereinsverwaltung für Schachvereine (z. B. Schachclub Königsspringer Musterstadt e.V.) – Mitglieder, Beiträge, Spielbetrieb, Turniere, Kommunikation und Kassenbuch in einer Anwendung.
Servergerendert mit Django 5, responsive ab 360 px, DSGVO-konform und betreibbar auf eigener Infrastruktur oder europäischem PaaS (keine Tracker, keine externen CDNs, keine US-Hyperscaler).

Das System dient gleichzeitig als Fundament für das Managed-Angebot [Schachverwaltung.de](https://schachverwaltung.de) ([ADR-014](docs/decisions/ADR-014-preisgestaltung.md), [ADR-018](docs/decisions/ADR-018-branding-schachverwaltung-de.md), [ADR-025](docs/decisions/ADR-025-hosting-eu-ebene-scalingo.md)).

---

## Schnellstart (Entwicklung)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo          # Realistische Demo-Daten
.venv/bin/python manage.py runserver
```

Für die lokale Vorführung ist die Zwei-Faktor-Authentifizierung standardmäßig abgeschaltet; im Produktivbetrieb ist sie für die Vorstandsgruppe verpflichtend (`TWOFA_PFLICHT=1`).

```bash
TWOFA_PFLICHT=0 .venv/bin/python manage.py runserver
```

Alternativ über **Docker Compose** (App plus PostgreSQL 16, automatische Migration beim Start):

```bash
docker compose up -d --build
docker compose exec app pytest
```

### Anmeldung mit Demo-Daten

| Benutzer | Rolle | Passwort | Zuständigkeit |
| --- | --- | --- | --- |
| `vorstand` | Vorstand (Gruppe `admin`) | `schach2026` | Volle Rechte, Vereins-Setup, Stammdaten, Saisons |
| `kassenwart` | Vorstand (Gruppe `admin`) | `schach2026` | Beiträge, SEPA-Export/Verbuchung, Kassenbuch |
| `kapitaen` | Mannschaftsführer (`kapitaen`) | `schach2026` | Aufstellungen, Ligaspiel-Ergebnisse (keine Finanzdaten) |
| `mitglied` | Mitglied (`mitglied`) | `schach2026` | Profil-Selbstbedienung, Änderungswünsche, Spielbetrieb |

Beispieldaten können über die CLI zurückgesetzt werden:
```bash
python manage.py seed_demo --reset
```
Alternativ steht autorisierten Vorständen im Django-Admin unter `/admin/core/demodata/` eine **Web-Steuerung für Demo-Daten** (Ein/Aus mit Revisionsschutz und Prüfung auf echte Bestandsdaten, [ADR-022](docs/decisions/ADR-022-demo-daten-steuerung-im-admin-panel.md)) zur Verfügung.

---

## Marketing- & Vereinsrouting (Schachverwaltung.de)

Das Gesamtsystem unterstützt ein Zwei-Welten-Routing ([ADR-024](docs/decisions/ADR-024-marketing-site-routing-schachverwaltung-de.md)):

1. **Vertriebs- & Marketing-Auftritt:** Auf `schachverwaltung.de` (oder bei `IS_MARKETING_SITE=1`) liefert die Einstiegsroute `/` die Produkt-Landingpage mit Nutzenversprechen, interaktiver Schmerzpunkte- und Feature-Vorschau für fünf Vereinsfunktionen (Vorstand, Kassenwart, Spielleiter, Mannschaftsführer, Mitglieder), Preisstufen und DSGVO/EU-Hosting-Garantie ([ADR-025](docs/decisions/ADR-025-hosting-eu-ebene-scalingo.md)).
2. **Kunden- & Vereinsinstanzen:** Auf Vereins-Domains oder Subdomains rendert `/` die öffentliche Vereinspräsenz (oder leitet bei deaktiviertem Homepage-Modul direkt zum Login bzw. Dashboard weiter, [ADR-023](docs/decisions/ADR-023-vereinshomepage-als-modul.md)).
3. **Kanonische Weiterleitung:** Die frühere URL `/produkt/` leitet per HTTP 301 permanent auf `/` weiter.

---

## Tests & Qualitätssicherung

```bash
pytest                               # > 740 Tests (inkl. Negativ- und Rollentests)
ruff check .                         # Linting
python manage.py check               # Django-Systemprüfung
python manage.py check --deploy      # Produktions-Sicherheitscheck
```

Die GitHub-Actions-Pipeline (`.github/workflows/ci.yml`) führt bei jedem Push und PR Tests gegen PostgreSQL 16, Linting mit Ruff, Migrationsprüfung (`makemigrations --check --dry-run`) sowie `manage.py check --deploy` mit den Produktions-Settings (`config.production`) aus.

---

## Produktivbetrieb & Hosting

* **Docker Compose (Self-Hosting):**
  ```bash
  cp .env.prod.example .env.prod      # Konfigurationswerte ausfüllen
  docker compose -f docker-compose.prod.yml up -d --build
  ```
* **TLS-Reverse-Proxy:** In `docker-compose.prod.yml` ist **Caddy** integriert, der Zertifikate (Let's Encrypt / ZeroSSL) vollautomatisch bezieht, Sicherheits-Header setzt und statische Assets komprimiert ausliefert ([ADR-009](docs/decisions/ADR-009-betrieb-caddy-restic-uptime-kuma.md)).
* **Cloud & PaaS (Scalingo):** Bereitstellung in der Region Europa (Paris `osc-fr1` / Frankfurt `osc-cl1`) mit EU-Datensouveränität und AVV ([ADR-025](docs/decisions/ADR-025-hosting-eu-ebene-scalingo.md)).
* **Verschlüsselte Backups & Monitoring:** Nächtliche Dumps mit OpenSSL AES-256-CBC PBKDF2 (`tools/backup.sh`) und Push-Monitoring via Uptime Kuma ([docs/deployment.md](docs/deployment.md)).
* **Wartung & Betrieb:** Detaillierte Arbeitsanweisungen für Vorstände und Admins in [`docs/wartung.md`](docs/wartung.md).

---

## Architektur & Modulaufbau

### Django-Apps

| App | Funktionsumfang |
| --- | --- |
| `core` | Authentifizierung, Rollenmatrix, Dashboard, AuditLog, DSGVO-Auskunft & Anonymisierung, 2FA (TOTP), Brute-Force-Schutz (`axes`), serverseitiges Rate-Limiting (`django-ratelimit`), Onboarding-Assistent, Modul-Toggles (`ModuleSettings`), Demo-Daten-Verwaltung, PWA-Grundlage. |
| `members` | Mitgliederstammdaten, Statusverlauf (aktiv/passiv/ausgetreten), Profil-Selbstbedienung & Änderungswünsche, DSB-Wertungsportal-Sync (DWZ-Drift-Detection), persönlicher iCal-Feed, CSV-Import mit Dry-Run. |
| `dues` | Beitragskategorien, Jahresbeitragssätze, Beitragslauf, Zahlungen & Storno per Gegenbuchung, druckfähiges Mahnwesen (HTML), SEPA-Mandate (verschlüsselte IBAN), SEPA-XML-Export (pain.008), 1-Klick-Sammelverbuchung. |
| `teams` | Saisonverwaltung (Hauptsaison, 1-Klick-Rollover, Archivierung), Mannschaften, Ligaspiele, Aufstellungen, Tabellenberechnung mit Buchholz-Tiebreak, A4-Spielberichtsbogen, WhatsApp-Ticker, iCal-Spielplansynchronisation. |
| `tournaments` | Schweizer-System-Turniere, Saisonbindung, Rundenaushänge (A4-Druckansicht), öffentliche Online-Anmeldung, Touch-Pills am Brett (WCAG 2.5.5), Buchholz-Wertung, ChessResults-/Swiss-Manager-Export. |
| `comms` | Vereinsankündigungen mit Entwurfs- und Freigabe-Workflow, SMTP-Gruppen-E-Mail-Verteiler mit Opt-in-Zustimmung. |
| `cashbook` | Vereinskassenbuch, GoBD-konformes Stornieren per Gegenbuchung (kein Hard-Delete), Jahresabschluss, CSV-Export. |

### Besondere Merkmale & Funktionen (v1.1)

* **Modul-Toggles im Admin (`ModuleSettings`, [ADR-019](docs/decisions/ADR-019-modul-toggles-im-admin-panel.md)):** Satellitenmodule (`teams`, `tournaments`, `cashbook`, `comms`) können im Django-Admin flexibel de- und aktiviert werden. Nicht genutzte Module verschwinden vollständig aus Menü, Dashboard und Suche; direkte Routenaufrufe liefern HTTP 404.
* **Vereinshomepage als modulares Add-on ([ADR-023](docs/decisions/ADR-023-vereinshomepage-als-modul.md)):** Vereine mit bestehender Homepage können die integrierte Webpräsenz abschalten (`homepage_aktiv=False`). Die Einstiegsroute `/` leitet eingeloggte Mitglieder direkt ins Dashboard und Besucher zum Login weiter.
* **Saisonverwaltung ([ADR-027](docs/decisions/ADR-027-saisonverwaltung-fuer-den-vorstand.md)):** Saubere Trennung von sportlichen Spielzeiten (z. B. `2026/2027`) und dem Beitrags-Kalenderjahr. Atomare Hauptsaison-Umschaltung, Spielplanvalidierung, Schreibschutz für archivierte Saisons und 1-Klick-Team-Rollover.
* **Vereins-Setup & Stammdaten ([ADR-020](docs/decisions/ADR-020-vereinsstammdaten-in-der-datenbank.md)):** Geführtes Browser-Tool unter `/verein/setup/` für Vereinsangaben (`ClubProfile`), Beitragssätze, Mannschaften und CSV-Mitgliederimport inklusive Muster-Download, Zeilen-Mapping und Dry-Run-Validierung.
* **DSB- / DWZ-Synchronisation ([ADR-016](docs/decisions/ADR-016-dsb-schnittstellen-architektur.md)):** Direkte Anbindung an die DSB-Wertungsportal-API mit 24-Stunden-Cache, Drift-Erkennung (abweichende DWZ, fehlende Spieler) und selektiver Stammdatenaktualisierung.
* **SEPA-XML-Download (pain.008) & Sammelverbuchung ([ADR-017](docs/decisions/ADR-017-sepa-xml-export-pain-008.md)):** Manuelle Abgabe von Lastschriften bei Banken/Sparkassen ohne unsichere Drittanbieter-Bank-APIs ([ADR-002](docs/decisions/ADR-002-kein-automatisierter-sepa-einzug.md)).
* **Admin Import/Export ([ADR-021](docs/decisions/ADR-021-django-import-export-im-admin.md)):** Revisionssicherer CSV/TSV/JSON-Import und -Export für Mitglieder und Kassenbuch im Django-Admin ohne Löschberechtigung.
* **Operative Spieltagsworkflows & Print-Engine:** Touch-Pills am Brett (≥ 44×44 px nach WCAG 2.5.5), A4-Spielberichtsbögen mit Unterschriftsfeldern, Rundenaushänge für den Spielabend und persönliche iCal-Kalenderabonnements für Spieler.

---

## Design-Systeme

Das System nutzt zwei vollständig voneinander isolierte handgeschriebene CSS-Architekturen ohne Node.js-Buildschritt oder externe CDN-Abhängigkeiten (PRD N1.1):

| Bereich | Stylesheet | Skripte | Basis-Templates |
| --- | --- | --- | --- |
| **Öffentliche Vereinsseite & Auth** (inkl. Anmeldung, 2FA, Passwort-Reset) | `static/css/site.css` | `static/js/public.js` | `templates/public_base.html`, `templates/auth_base.html` |
| **Interne Verwaltung & Dashboard** | `static/css/app.css` | `static/js/app.js` | `templates/base.html` |
| **Marketing-Landingpage** | `static/css/landing.css` | *kein JS erforderlich* | `core/templates/core/produkt.html` |

Das öffentliche Design folgt [ADR-013](docs/decisions/ADR-013-oeffentliche-designsprache.md); das interne Design bietet optimierte A4-Drucklayouts (`@media print`), klassische Schachserifen und WCAG-konforme AAA-Kontraste.

### Vereinsprofil & Stammdaten

Vereinsdaten werden vorrangig in der Datenbank über das Singleton-Modell `ClubProfile` verwaltet und können im Einrichtungs-Assistenten (`/verein/setup/`) oder im Django Admin angepasst werden ([ADR-020](docs/decisions/ADR-020-vereinsstammdaten-in-der-datenbank.md)). Bei nicht konfigurierten Feldern greift das System transparent auf die optionalen Umgebungsvariablen zurück:

| Variable | Beispiel | Bedeutung / Fallback |
| --- | --- | --- |
| `CLUB_NAME` | `Schachclub Königsspringer Musterstadt e.V.` | Offizieller Vereinsname |
| `CLUB_SHORT` | `SC Königsspringer` | Kurzname für Navigation und Tabellen |
| `CLUB_FOUNDED` | `1978` | Gründungsjahr für Vereinsjubiläum |
| `CLUB_LOCATION` | `Musterstadt` | Stadt/Ort im Header und Footer |
| `CLUB_ROOM` | `Vereinsheim Musterstadt, Musterstraße 1` | Spiellokal und Adresse |
| `CLUB_NIGHT_HOURS` | `Donnerstags ab 19:00 Uhr` | Spielabend Erwachsene |
| `CLUB_YOUTH_HOURS` | `Donnerstags 17:30 – 19:00 Uhr` | Trainingszeiten Jugend |
| `CLUB_CONTACT` | `vorstand@schachverein-musterstadt.de` | Kontakt-E-Mail |

---

## Datenschutz & Sicherheitsarchitektur

* **Hosting & Infrastruktur:** 100 % EU-Hosting (Scalingo SAS Frankreich/Deutschland bzw. Hetzner Online GmbH Deutschland). Keine externen CDNs, Fonts, Tracking-Pixel oder US-Hyperscaler (PRD N1.1, [ADR-025](docs/decisions/ADR-025-hosting-eu-ebene-scalingo.md)).
* **DSGVO-Selbstauskunft & Löschung:** 1-Klick-Datenauskunft je Mitglied als HTML, PDF und JSON. Automatische Anonymisierung nach Vereinsaustritt (`manage.py anonymize_former_members`) mit Erhalt der anonymisierten Finanzhistorie (§ 147 AO, PRD N1.2–N1.4).
* **Audit-Trail (PRD N1.5):** Revisionssicheres `AuditLog` für alle personenbezogenen Datenänderungen, Logins, Detail-Zugriffe, Exporte und Konfigurationsänderungen.
* **Finanzdaten-Integrität:** Finanz- und Beitragsdaten werden niemals physisch gelöscht; Korrekturen erfolgen ausschließlich durch Storno per Gegenbuchung ([ADR-005](docs/decisions/ADR-005-beitragsposten-idempotenz-und-momentaufnahme.md), [ADR-006](docs/decisions/ADR-006-storno-per-gegenbuchung.md)).
* **Verschlüsselung sensibler Daten:** Bankverbindungen (IBAN) werden mit symmetrischem Fernet (AES-128-CBC / SHA256) verschlüsselt gespeichert ([ADR-010](docs/decisions/ADR-010-iban-verschluesselt-in-der-datenbank.md)). Kein Klartext in Logs, Dumps oder Listen.
* **Brute-Force- & DoS-Schutz:**
  - Login-Schutz mit `django-axes` ([ADR-015](docs/decisions/ADR-015-brute-force-schutz-und-dev-profiling.md)).
  - Serverseitiges Rate-Limiting (`django-ratelimit`, 5 Requests/Min.) für öffentliche POST-Endpunkte (Schnupper-Formular, Gastturnieranmeldung, Passwort-Reset) mit verifizierter Proxy-IP-Ermittlung (SEC-05, [ADR-028](docs/decisions/ADR-028-rate-limiting-mit-django-ratelimit.md)).
  - Dateigrößen-Begrenzung beim CSV-Upload (max. 2 MB) zum Schutz vor Memory Exhaustion (T31b).
  - Bereinigung physischer Dateien bei Datensatzlöschung via `django-cleanup` ([ADR-026](docs/decisions/ADR-026-dateibereinigung-mit-django-cleanup.md)).
* **Formula-Injection-Schutz (CWE-1236 / SEC-06):** Flächendeckende Maskierung potenzieller Tabellen-Kalkulationsbefehle (`=`, `+`, `-`, `@`) in allen CSV-Exporten (T25c).
* **2FA, Step-Up & Open-Redirect-Schutz:** Zwei-Faktor-Authentifizierung (TOTP) für Vorstände verpflichtend; 2FA-Erzwingung bei Einladungsannahme (T26c), Passwortbestätigung (Step-Up) beim Gerätewechsel (T26d) und Open-Redirect-Schutz (CWE-601) mit strikter Host- und Schemavalidierung (T26e).

---

## Dokumentation & Referenzen

| Dokument | Beschreibung |
| --- | --- |
| [`docs/prd.md`](docs/prd.md) | Fachliches Lastenheft, Berechtigungsmatrix (§3.8), Release-Schnitt v1 / v1.1 |
| [`docs/funktionen.md`](docs/funktionen.md) / [HTML](docs/funktionen.html) | Lückenlose Modul- und Funktionsübersicht aller Vereins- und Schutzmechanismen |
| [`docs/anschreiben_testverein.md`](docs/anschreiben_testverein.md) | Formulierungsvorlagen für die Erstansprache von Vorständen für den Pilotbetrieb |
| [`docs/abnahme.md`](docs/abnahme.md) | Abnahmekriterien, DSGVO-Erfüllungsnachweis und Meilensteine |
| [`docs/deployment.md`](docs/deployment.md) | Produktiv-Deployment, TLS-Setup mit Caddy, verschlüsselte Backups, Restore-Test & Uptime Kuma |
| [`docs/ersteinrichtung.md`](docs/ersteinrichtung.md) | Leitfaden für die erstmalige Inbetriebnahme und Datenübernahme |
| [`docs/wartung.md`](docs/wartung.md) | Django-Wartungsprimer und wiederkehrende Aufgaben für den Vorstand |
| [`docs/nfr-pruefung.md`](docs/nfr-pruefung.md) | Messwerte zu Performance, Barrierefreiheit (WCAG 2.1 AA) und Responsive Design |
| [`docs/einfuehrung_testverein.md`](docs/einfuehrung_testverein.md) | Pilotkonzept, Schulungsplan und Rollout-Strategie |
| [`docs/avv_muster.md`](docs/avv_muster.md) | Muster-Auftragsverarbeitungsvertrag gem. Art. 28 DSGVO (inkl. Scalingo SAS / Hetzner) |
| [`docs/pilotvereinbarung_muster.md`](docs/pilotvereinbarung_muster.md) | Vereinbarungsvorlage für Pilot- und Testvereine |
| [`tasks/plan.md`](tasks/plan.md) | Vollständiger Implementierungsplan mit Task-Status und Traceability |
| [`tasks/todo.md`](tasks/todo.md) | Fortschrittsprotokoll mit Verifikationsbelegen erledigter Aufgaben |
| [`docs/decisions/`](docs/decisions/) | Architekturentscheidungen ([ADR-001](docs/decisions/ADR-001-django-stack.md) bis [ADR-029](docs/decisions/ADR-029-lizenz-agplv3-und-open-source-strategie.md)) |
| [`docs/superpowers/specs/`](docs/superpowers/specs/) | Detaillierte Spezifikationen zu den einzelnen Funktionsblöcken |

---

## Lizenz & Support-Modell

Dieses Projekt ist freie Software unter der **[GNU Affero General Public License v3.0](LICENSE)** (AGPL-3.0) — siehe [ADR-029](docs/decisions/ADR-029-lizenz-agplv3-und-open-source-strategie.md).

* **Community-Support (Self-Hosting):**
  Fragen, Fehlerberichte und Austausch zum eigenständigen Betrieb erfolgen über die öffentlichen [GitHub Issues](https://github.com/vibeCodeDE/chessclub/issues) und Discussions. Für selbst gehostete Instanzen gibt es keinen garantierten SLA- oder individuellen Einrichtungssupport.
* **Managed Hosting & Vorstands-Support ([Schachverwaltung.de](https://schachverwaltung.de)):**
  Für Vereine, die sich nicht um Server, Updates, PostgreSQL, TLS und DSGVO-konforme Backups kümmern möchten, bieten wir die schlüsselfertige Bereitstellung inklusive persönlichem Support und SLA im Monats-/Jahresabonnement an ([ADR-014](docs/decisions/ADR-014-preisgestaltung.md), [ADR-025](docs/decisions/ADR-025-hosting-eu-ebene-scalingo.md)).

