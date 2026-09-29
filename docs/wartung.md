# Wartung – Kurzanleitung für die Vorstandschaft (T22)

Diese Anleitung erklärt die wiederkehrenden Aufgaben **ohne Entwicklerwissen**.
Alle Befehle laufen im Projektordner auf dem Vereinsserver.

```bash
cd /opt/schachverein
alias dc="docker compose -f docker-compose.prod.yml"
```

## Täglicher Blick (2 Minuten)

| Prüfung | Befehl | Erwartet |
| --- | --- | --- |
| Läuft die App? | `curl -fsS http://127.0.0.1:8000/health/` | `{"status": "ok"}` |
| Letzte Fehler | `dc logs --since 24h app \| grep ERROR` | keine Zeilen |
| Letztes Backup | `ls -lh backups/ \| tail -3` | Datei von heute/gestern |

Fehler landen zusätzlich als E-Mail bei den in `DJANGO_ADMINS` eingetragenen
Personen (Abschnitt „Monitoring“ in `docs/deployment.md`).

## Anmeldung des Vorstands (Zwei-Faktor)

1. `/anmelden/` → Benutzername und Passwort.
2. Beim **ersten** Login zeigt die App einen Schlüssel und einen `otpauth://`-Link.
   Beides in eine Authenticator-App übertragen (z. B. Aegis, FreeOTP, Google
   Authenticator) oder den Link am Handy öffnen.
3. Den 6-stelligen Code der App eintragen → fertig.
4. Bei Handywechsel: nach dem Passwort-Login auf „Abbrechen“ verzichten und
   `/anmelden/zwei-faktor/neu/` aufrufen (oder in der Django-Administration das
   Gerät löschen) – danach neu einrichten.

> Ohne Code kein Zugriff auf Vorstandsfunktionen. Geht das Handy verloren, kann
> eine zweite Vorstandsperson das Gerät in `/admin/core/twofactordevice/` löschen.

## Häufige Aufgaben

**Mitglied anlegen/ändern** – Menü „Mitglieder“ → „Mitglied anlegen“ bzw. Zeile
öffnen → „Bearbeiten“. Austritte werden erfasst, nie gelöscht.

**Beitragslauf für ein Jahr** – „Beiträge“ → Jahr wählen → „Beitragslauf starten“.
Der Lauf ist wiederholbar; bereits vorhandene Posten werden übersprungen.

**Zahlung buchen** – „Beiträge“ → Zeile → „Zahlung erfassen“. Betrag und Datum
eintragen; die Buchung erscheint automatisch im Kassenbuch (Kategorie Beiträge).

**Mahnung** – „Mahnwesen“ → Zeile → „Mahnen“. Stufe 1/2 wird gesetzt, der
Mahnbrief ist unter „Brief“ druckbar (bitte vorher IBAN/Mandat prüfen – der
Einzug erfolgt manuell über die Bank).

**Rundmail** – „E-Mail-Versand“ → Betreff, Gruppe, Text. „Testversand an“ mit
eigener Adresse nutzen, um vorher zu prüfen. Ohne Opt-in wird niemand
angeschrieben; jede Sendung steht im Protokoll.

**Turnier** – „Turnierverwaltung“ → Turnier anlegen → Teilnehmer erfassen →
„Runde auslosen“ → Ergebnisse eintragen. Die Tabelle rechnet Live-Wertung
(Punkte, Buchholz); Druck- und CSV-Ausgabe für ChessResults liegen bereit.

## Jährliche Pflichten

```bash
# 1. Ausgetretene Mitglieder nach Frist anonymisieren – erst prüfen:
dc exec app python manage.py anonymize_former_members --dry-run
#    ... dann wirklich ausführen:
dc exec app python manage.py anonymize_former_members

# 2. Verzeichnis der Verarbeitungstätigkeiten aktualisieren (CSV):
#    Menü „System“ → „Verzeichnis Verarbeitungstätigkeiten“  (bzw. /datenschutz/verzeichnis.csv)

# 3. Backup-Restore-Test durchführen und in docs/deployment.md eintragen.
```

## Update einspielen

```bash
git pull
dc up -d --build                      # migriert automatisch
dc exec app python manage.py migrate --check    # muss leer bleiben
```

Vorher manuell sichern (siehe `docs/deployment.md`, Abschnitt 5).

## Notfälle

| Problem | erste Hilfe |
| --- | --- |
| Seite zeigt 502/„Bad Gateway“ | `dc ps`, dann `dc restart app` |
| „Service Unavailable“ nach Update | `dc logs app \| tail -50`, Migration prüfen |
| Login geht nicht mehr | Passwort-Reset über `/passwort/aendern/`; 2FA-Gerät ggf. in `/admin/` löschen |
| Daten versehentlich geändert | `/audit/` zeigt Wer/Was/Wann; Backup-Restore laut Doku |
| Verdacht auf Datenabfluss | Backup sichern, Zugänge sperren, Vorstand informieren (DSGVO-Meldefrist 72 h) |

## Wo finde ich was?

| Bereich | Adresse |
| --- | --- |
| Dashboard | `/dashboard/` |
| Audit-Protokoll | `/audit/` |
| Django-Administration (Notfall) | `/admin/` |
| Systemzustand | `/health/` |
| Verzeichnis Verarbeitungstätigkeiten | `/datenschutz/verzeichnis.csv` |

Technische Details für eine Nachfolge im Vorstand: `docs/prd.md` (Anforderungen),
`docs/deployment.md` (Betrieb), `tasks/plan.md` (umgesetzte Pakete).
