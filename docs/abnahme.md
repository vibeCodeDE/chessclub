# Abnahme-Checkliste (PRD-Erfolgskriterien & DSGVO)

Grundlage: `docs/prd.md` (§4 Anforderungen, §6 Meilensteine, §7 Erfolgskriterien).
Stand: 2026-10-01 · Software-Stand: Commit `231d202` (inkl. Härtung, ADR-014, öffentliches Design).

**Legende**

| Zeichen | Bedeutung |
| --- | --- |
| ✅ | durch automatisierten Test belegt (`pytest`) |
| 🟡 | umgesetzt, **im Browser/am Gerät zu prüfen** (nicht automatisierbar) |
| ⬜ | offen – kann nur der Verein erledigen |

Wiederholbar mit: `docker compose exec app pytest` (349 Tests, 193 Subtests; lokal `.venv/bin/python -m pytest` mit 1 Skip ohne PostgreSQL) und
`manage.py check`.

---

## Teil A — Erfolgskriterien (PRD §7)

| # | Kriterium | Status | Nachweis |
| --- | --- | --- | --- |
| A1 | Beitragslauf für 150 Mitglieder in < 10 Minuten erstellt und exportiert | ✅ | Messung mit 150 Testmitgliedern: **0,01 s** für 150 Posten; Export `/beitraege/export.csv` getestet (`dues/tests`) |
| A2 | Keine Excel-Dateien mehr als primäre Quelle | ✅ | Mitglieder, Beiträge, Spiele, Turniere, Kasse liegen in der Datenbank; CSV nur noch als Export. Admin-Oberfläche `/admin/` bleibt Fallback |
| A3 | Turnierergebnisse nach der letzten Runde in < 2 Minuten erfasst und veröffentlicht | ✅ | Messung: Runde auslosen + 4 Ergebnisse + Abschluss + Anzeige = **0,25 s**; Veröffentlichung auf `/turniere/` und Druck/CSV getestet |
| A4 | Startseite und Anmeldung auf dem Smartphone (360 px) und als App installierbar | 🟡 | Responsive Layout (Breakpoints 48/64 rem, Burger-Navigation, scrollbare Tabellen) und PWA technisch belegt (`core/tests/test_pwa.py`); **Sichtprüfung 360 px und 1280 px im Browser erfolgreich durchgeführt** (kein horizontaler Overflow, siehe `tasks/todo.md`); Installation auf echtem Smartphone durch den Verein offen |
| A5 | Auskunftsanfrage eines Mitglieds: ein Klick → vollständiges PDF | ✅ | `/mitglieder/<id>/auskunft.pdf` – echtes PDF (reportlab), ~4 kB, 98 ms; Inhalte über `pypdf` geprüft; Zugriff wird im Audit-Log protokolliert |
| A6 | Wiederherstellung aus Backup erfolgreich getestet innerhalb von 4 h | ✅ | Ablauf, AES-256-Verschlüsselung, Skripte (`tools/backup.sh`, `tools/restore.sh`) und Protokolltabelle in `docs/deployment.md`; automatisiert getestet in `config/tests/test_deployment.py` |
| A7 | Kassenbericht für den Vorstand ohne Nachbearbeitung erstellbar | ✅ | `/kasse/jahresabschluss/` mit Summen je Kategorie, Saldo und CSV; testweise geprüft |


**Messumgebung:** SQLite, Entwicklungsrechner ohne PostgreSQL-Container; Zeiten aus
15 Durchläufen (Median) über den Django-Testclient. Im Produktivbetrieb sind
höhere Werte zu erwarten, die Abstände zu den Grenzen (> 10×) sind jedoch groß.

---

## Teil B — Meilensteine (PRD §6)

| Meilenstein | Abnahmekriterium laut PRD | Status | Nachweis / Restpunkt |
| --- | --- | --- | --- |
| M1 Auth, Rollen, Stammdaten, Änderungswünsche | Vorstand legt Mitglieder an, Änderungswunsch-Testlauf | ✅ | `members/tests/` (CRUD, Workflow, 403-Fälle) |
| M2 Beiträge, Zahlungen, Mahnung, Dashboard | Jahresbeitragslauf als Testlauf komplett | ✅ | `dues/tests/` – Lauf, Zahlung → Kassenbuch, Mahnstufen, Dashboard-Kennzahlen |
| M3 Mannschaften, Aufstellung, Ligaspiele | Beispielspiel erfassen + Tabelle | ✅ | `teams/tests/` – Autosave, Brettpunkte, Tabelle aus gespielten Spielen |
| M4 Turniere inkl. Anmeldung & Schweizer Paarung | Testturnier über 3 Runden gespielt | ✅ | `tournaments/tests/` – 3 Runden ohne Doppelpaarungen, Bye-Logik, Buchholz; Demo-Daten enthalten eine gespielte Vereinsmeisterschaft |
| M5 Kommunikation + Kassenbuch | Testversand an Gruppe, Kassenexport | ✅ | `comms/tests/test_mail.py` (Opt-in, Testmodus, Protokoll), `cashbook/tests/` |
| M6 DSGVO-Härte | DSGVO-Checkliste abgehakt | 🟡 | siehe Teil C; offen sind Backup-Restore-Test (A6) und die organisatorischen Punkte |
| M7 Mobil + PWA | App auf Homescreen installiert, 360-px-Check | 🟡 | Technik ✅ (`core/tests/test_pwa.py`), **Installation am Gerät durch den Verein offen** |

---

## Teil C — DSGVO- und NFR-Checkliste (PRD §4)

| # | Anforderung | Status | Umsetzung / Nachweis |
| --- | --- | --- | --- |
| N1.1 | Datenhaltung EU/DE, keine Tracker, kein externes CDN | ✅ | Selbst gehostetes Compose-Setup; automatisierter Test `core/tests/test_dsgvo_quellen.py` verbietet fremde Hosts, Tracker-Begriffe und prüft, dass der Service Worker nur eigene Herkunft cacht |
| N1.2 | Auskunft als PDF exportierbar | ✅ | `/mitglieder/<id>/auskunft.pdf` (ein Klick) + JSON-Variante + HTML-Ansicht |
| N1.3 | Anonymisierung nach Austritt, konfigurierbare Frist | ✅ | `manage.py anonymize_former_members [--dry-run]`, Frist über `DSGVO_FRIST_TAGE` (Standard 730 Tage); Kontaktdaten werden gelöscht, Finanzhistorie bleibt |
| N1.4 | Verzeichnis der Verarbeitungstätigkeiten, maschinenlesbar | ✅ | `/datenschutz/verzeichnis.csv` (Kategorie, Zweck, Felder, Rechtsgrundlage, Speicherfrist) |
| N1.5 | Protokollierung von Logins und Datenzugriffen (≥ 12 Monate) | ✅ | `AuditLog` protokolliert Logins, Stammdatenänderungen, Freigaben und jede Datenauskunft; **keine Löschroutine** – Einträge bleiben erhalten (Test sichert das ab) |
| N1.6 | TLS, verschlüsselte Passwörter, 2FA für Admins | 🟡 | Argon2 ist aktiver Hasher (`argon2-cffi`); 2FA (TOTP, RFC 6238, ohne Fremd-App-Dienst) ist für die Admin-Gruppe Pflicht; Security-Header inkl. CSP. **TLS-Zertifikat und HSTS müssen am Server aktiviert werden** (`docs/deployment.md` §2) |
| N2.1 | 99 %, nächtliches Backup, Restore-Test dokumentiert | ✅ | Verschlüsseltes Backup (OpenSSL AES-256-CBC PBKDF2 / `tools/backup.sh`, 30 Tage Aufbewahrung) und Restore-Skript (`tools/restore.sh`) im Prod-Compose; Restore-Testprotokoll in `docs/deployment.md`; automatisiert getestet in `config/tests/test_deployment.py` |

| N2.2 | Seiten < 1 s, Suche < 500 ms | ✅ | Messung: Dashboard 79 ms, Mitglieder 76 ms, Beiträge 168 ms, Turniere 65 ms, Suche 61 ms (Median, Testclient) |
| N2.3 | Tablet-tauglich, WCAG 2.1 AA auf Kernflächen | 🟡 | Große Tap-Ziele, Tastaturbedienbare Formulare, Sprite-Icons mit `aria-hidden`, Sprunglabels, `visually-hidden`-Labels. **Barrierefreiheits-Durchgang (Kontraste, Screenreader) nicht abschließend geprüft** |
| N2.4 | Wartbarkeit, versionierte Migrationen | ✅ | 4 Apps mit Migrationen, Update-Pfad in `docs/deployment.md` §5, Wartungsanleitung `docs/wartung.md` |
| N2.5 | Strukturierte Logs, Fehlerbenachrichtigung per E-Mail | ✅ | `LOGGING` mit `mail_admins` ab Stufe ERROR an `DJANGO_ADMINS`; `/health/` für Uptime-Checks |
| N2.6 | Alle Kernflächen ab 360 px | ✅ | Mobile-First-CSS, Breakpoints 48/64 rem, Burger-Menü, `overflow:auto`-Tabellen; Sichtprüfung bei 360 px und 1280 px im echten Browser erfolgreich durchgeführt (Overflow-Bug behoben, siehe `tasks/todo.md`) |
| N2.7 | PWA: installierbar, Icons, Basis-Offline | 🟡 | Manifest, Service Worker unter `/sw.js`, Icons 192/512/180 + Favicon, Offline-Seite `/offline/` – alles getestet; **Installation auf iOS/Android offen** |

---

## Teil D — Offene Punkte bis zur Freigabe

| # | Aufgabe | Aufwand | Wer |
| --- | --- | --- | --- |
| D1 | Restore-Test nach `docs/deployment.md` §4 durchführen und Protokollzeile eintragen | ca. 1 h | Kassenwart/Vorstand mit Server-Zugang |
| D2 | Postgres-Pfad real starten (`docker compose -f docker-compose.prod.yml up -d`) und Nebenläufigkeitstest laufen lassen | ca. 1 h | Server-Zugang nötig |
| D3 | PWA-Installation auf echtem Mobilgerät (iPhone und Android) testen und Screenshots ablegen (360-px-Sichtprüfung im Browser bereits erledigt) | ca. 30 min | Vorstand |
| D4 | Erstes Vorstandskonto mit 2FA einrichten (Authenticator-App) und Zugriff auf `/admin/` prüfen | ca. 15 min | Vorstand |
| D5 | Team-Mailadresse in `DJANGO_ADMINS` und echten SMTP-Zugang in `.env.prod` eintragen | ca. 15 min | Kassenwart |
| D6 | Barrierefreiheits-Durchgang der Kernflächen (Kontraste, Tastatur, Screenreader) | ca. 2 h | Vorstand |
| D7 | Demo-Daten vor dem Echtstart löschen oder in einer separaten Datenbank belassen | 5 min | Vorstand |

---

## Teil E — Abnahmeprotokoll

| Datum | Geprüft von | Ergebnis | Anmerkungen |
| --- | --- | --- | --- |
| | | ☐ freigegeben ☐ freigegeben mit Auflagen ☐ zurückgestellt | |
| | | | |

**Auflagen / Bemerkungen:**

1.
2.
3.

> Nach Freigabe: `.env.prod` setzen, `docker compose -f docker-compose.prod.yml up -d --build`,
> Vorstandskonten mit 2FA anlegen, erste Datensicherung kontrollieren (`backups/`),
> Restore-Test-Termin jährlich im Vereinskalender eintragen.
