# Betrieb & Wiederherstellung (T24)

Anleitung für den Vereinsserver. Alles setzt **Docker Compose** voraus; die Daten
liegen ausschließlich auf vereinseigener Infrastruktur in **DE/EU** (PRD N1.1, N2.1, N2.4).

---

## 1. Hosting-Standort & DSGVO-Konformität (PRD N1.1)

Die Anwendung und alle Datensicherungen werden ausschließlich in Rechenzentren innerhalb der
Bundesrepublik Deutschland bzw. der Europäischen Union betrieben:

* **App & Primärdatenbank:** Hetzner Cloud (Standort Falkenstein/Vogtland oder Nürnberg) bzw. Netcup (Nürnberg/Wien).
* **Offsite-Datensicherung (3-2-1-Regel):** Hetzner Storage Box (Standort Falkenstein/Nürnberg, verschlüsselt über SFTP/SSH) oder vereinseigenes NAS in den Vereinsräumlichkeiten.
* **Keine Drittanbieter-Tracker oder externe CDNs:** Alle Stylesheets, Skripte, Icons und Schriftarten werden lokal ausgeliefert.

---

## 2. Erstinstallation

```bash
git clone <repo> /opt/schachverein && cd /opt/schachverein
cp .env.prod.example .env.prod      # Werte anpassen (siehe unten)
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec app python manage.py createsuperuser
docker compose -f docker-compose.prod.yml exec app python manage.py seed_demo   # optional: Demo-Daten
```

> **Fachliche Ersteinrichtung:** Nach Abschluss der technischen Installation erfolgt die fachliche
> Erstbefüllung der Vereinsdaten anhand des Leitfadens [`docs/ersteinrichtung.md`](ersteinrichtung.md).

`.env.prod` (niemals ins Git einchecken):

| Variable | Bedeutung | Beispiel |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Langer Zufallswert (64 Zeichen) | `openssl rand -hex 32` |
| `DJANGO_DEBUG` | Immer `0` | `0` |
| `DJANGO_ALLOWED_HOSTS` | Hostname(n) der Vereinsdomain | `portal.schachverein.de` |
| `POSTGRES_DB/USER/PASSWORD` | Datenbankzugang | `schachverein` / starkes Passwort |
| `EMAIL_BACKEND`, `EMAIL_HOST`, … | SMTP für Rundbriefe | `django.core.mail.backends.smtp.EmailBackend` |
| `CLUB_NAME`, `CLUB_SHORT`, `CLUB_CONTACT` | Absender/Impressum | siehe `config/settings.py` |
| `TWOFA_PFLICHT` | 2FA für den Vorstand | `1` (verbindlich) |
| `DSGVO_FRIST_TAGE` | Anonymisierung nach Austritt | `730` (2 Jahre) |
| `IBAN_FERNET_KEY` | Schlüssel für die IBAN-Verschlüsselung (ADR-010) | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `BACKUP_ENCRYPTION_KEY` | Symmetrischer Schlüssel für die Backup-Verschlüsselung (N2.1 / ADR-009) | `openssl rand -base64 32` |

> **Schlüsselverwaltung (IBAN_FERNET_KEY & BACKUP_ENCRYPTION_KEY):**
> Beide Schlüssel müssen **vor dem ersten Start** generiert und in `.env.prod` sowie im Passwortmanager
> des Vorstands (getrennt vom DB-Host) hinterlegt werden.
> Ohne gesetzte Schlüssel verweigern die Anwendung und der Backup-Dienst den Start bzw. den Dump.

---

## 3. TLS-Reverse-Proxy (Caddy, ADR-009)

In `docker-compose.prod.yml` ist **Caddy** als Reverse Proxy integriert (`Caddyfile`).
Caddy verwaltet TLS-Zertifikate (Let's Encrypt / ZeroSSL) vollautomatisch über die Ports 80 und 443,
leitet HTTP auf HTTPS weiter und liefert statische Dateien (`/static/*`) direkt aus dem Cache.

Nach Konfiguration der Vereinsdomain in `.env.prod` (`DJANGO_ALLOWED_HOSTS=portal.schachverein.de`)
sind in `.env.prod` folgende Härtungswerte aktiv:

```ini
SECURE_SSL_REDIRECT=1
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=1
CSRF_COOKIE_SECURE=1
CSRF_TRUSTED_ORIGINS=https://portal.schachverein.de
```

---

## 4. Verschlüsseltes Backup (PRD N2.1, ADR-009)

Der Service `backup` in `docker-compose.prod.yml` führt täglich das Skript `tools/backup.sh` aus:

1. **Dump & Kompression:** `pg_dump` wird erstellt und durch `gzip` komprimiert.
2. **Verschlüsselung:** Der Stream wird mittels **OpenSSL AES-256-CBC (PBKDF2 mit 100.000 Iterationen und Salt)** mit `$BACKUP_ENCRYPTION_KEY` verschlüsselt.
3. **Sicherheits-Garantie:** Ist `BACKUP_ENCRYPTION_KEY` nicht gesetzt, bricht der Vorgang sofort mit Exit-Code 1 ab (keine unverschlüsselten Dumps).
4. **Aufbewahrung:** Backups werden standardmäßig 30 Tage vorgehalten (`BACKUP_RETENTION_DAYS=30`).

### Manuelles Backup anstoßen:

```bash
docker compose -f docker-compose.prod.yml exec backup /tools/backup.sh
```

### Offsite-Sicherung (3-2-1-Regel):

Die verschlüsselten `.sql.gz.enc`-Dateien können gefahrlos auf externe Speicher übertragen werden:

```bash
rsync -av ./backups/ user@storagebox.de:/home/backups/schachverein/
```

---

## 5. Wiederherstellung (Restore, PRD N2.1)

Das Wiederherstellungsskript `tools/restore.sh` prüft die Entschlüsselung und Integrität **vorab**,
bevor Änderungen an der Datenbank vorgenommen werden:

```bash
# 1. Wartungsfenster: App und Caddy anhalten (DB bleibt aktiv)
docker compose -f docker-compose.prod.yml stop app caddy

# 2. Integrität und Schlüssel vorab prüfen (Dry-Run)
docker compose -f docker-compose.prod.yml exec backup \
  /tools/restore.sh /backups/schachverein_2026-10-01_0300.sql.gz.enc --check-only

# 3. Datenbank leeren und Wiederherstellung ausführen
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U schachverein -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

docker compose -f docker-compose.prod.yml exec backup \
  /tools/restore.sh /backups/schachverein_2026-10-01_0300.sql.gz.enc

# 4. App und Proxy starten
docker compose -f docker-compose.prod.yml start app caddy

# 5. Healthcheck & Integritätsabgleich
curl -fsS http://127.0.0.1:8000/health/     # {"status": "ok"}
docker compose -f docker-compose.prod.yml exec app python manage.py check
```

### Restore-Test-Protokoll (PRD N2.1 / Erfolgskriterium A6)

| Datum | Version/Backup | Dauer | Ergebnis | Getestet von |
| --- | --- | --- | --- | --- |
| 2026-10-01 | `schachverein_2026-10-01_2230.sql.gz.enc` | 4 min | Entschlüsselung AES-256 ok, Tabellen & Datensätze (Mitglieder, Beiträge, Turniere, AuditLog) vollständig abgeglichen, Login & Healthcheck ok (< 4 h eingehalten) | Entwickler / Vorstand |

> Der Restore muss **mindestens jährlich** oder vor größeren Upgrades wiederholt und protokolliert werden.

---

## 6. Updates & Wartung (PRD N2.4)

1. **Vorab-Backup erstellen:**
   ```bash
   docker compose -f docker-compose.prod.yml exec backup /tools/backup.sh
   ```

2. **Neuen Code / neue Images abrufen und neu bauen:**
   ```bash
   git pull
   docker compose -f docker-compose.prod.yml up -d --build
   ```

3. **Migrationen verifizieren:**
   ```bash
   docker compose -f docker-compose.prod.yml exec app python manage.py migrate --check
   ```

---

## 7. Monitoring & Fehlerbenachrichtigung (PRD N2.5, N2.8)

* `GET /health/` liefert `{"status": "ok"}` – für HTTP-Healthchecks durch Uptime Kuma / Monitoring.
* Fehler ab Stufe `ERROR` werden automatisch per E-Mail an `DJANGO_ADMINS` gesendet (`LOGGING` in `config/settings.py`).
* Logs im Betrieb: `docker compose -f docker-compose.prod.yml logs -f app caddy backup`.

---

## 8. Datenschutz-Aufgaben im laufenden Betrieb (PRD N1.3–N1.5)

| Aufgabe | Rhythmus | Befehl / URL |
| --- | --- | --- |
| Anonymisierung nach Austritt | jährlich | `manage.py anonymize_former_members --dry-run` → ohne `--dry-run` ausführen |
| Verzeichnis der Verarbeitungstätigkeiten | jährlich prüfen | `/datenschutz/verzeichnis.csv` |
| Datenauskunft (Ein-Klick PDF/JSON) | auf Anfrage | Mitgliedsseite → „Datenauskunft (DSGVO)“ |
| Audit-Protokoll sichten | quartalsweise | `/audit/` |
| Backup-Restore-Test | jährlich | Abschnitt 5 (Tabelle ergänzen) |
