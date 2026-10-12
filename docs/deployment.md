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

## 7. Monitoring & Fehlerbenachrichtigung (PRD N2.5, N2.8 / ADR-009 / T24b)

In `docker-compose.prod.yml` ist **Uptime Kuma** (`louislam/uptime-kuma:1-alpine`) als leichtgewichtiger Monitoring-Dienst integriert.

### 7.1 Zugriff & Sicherheit (PRD N2.8)
* **Port-Bindung:** Uptime Kuma lauscht auf `127.0.0.1:3001:3001` und ist damit von außen **nicht** ohne Weiteres erreichbar.
* **Admin-Zugriff:** Der Zugriff erfolgt über einen sicheren SSH-Port-Forwarding-Tunnel:
  ```bash
  ssh -L 3001:127.0.0.1:3001 user@vereinsserver
  ```
  Im Browser `http://localhost:3001` aufrufen. Beim ersten Start erzwingt Uptime Kuma die Erstellung eines Admin-Benutzers mit starkem Passwort.
* **Datenschutz (DSGVO):** Uptime Kuma speichert keine personenbezogenen Mitglieder- oder Vereinsdaten. Sämtliche Alarm-Mails enthalten ausschließlich technische Dienstnamen, Status und Zeitstempel.

### 7.2 Konfiguration der Monitore
1. **HTTP-Monitor für die Web-App:**
   * **Typ:** `HTTP(s)`
   * **Name:** `Schachverein Portal`
   * **URL:** `http://app:8000/health/`
   * **Intervall:** 60 Sekunden (Timeout: 10 Sekunden)
   * **Erwarteter Status:** HTTP 200 (Payload: `{"status": "ok"}`)

2. **Push-Monitor für das nächtliche Backup:**
   * **Typ:** `Push`
   * **Name:** `Schachverein DB-Backup`
   * **Intervall:** 86400 Sekunden (24 Stunden)
   * **Wiederholungen / Grace Period:** 7200 Sekunden (2 Stunden Pufferzeit)
   * **Push-URL:** Die von Uptime Kuma erzeugte URL (z. B. `http://uptime-kuma:3001/api/push/<TOKEN>?status=up&msg=OK`) in `.env.prod` als `KUMA_PUSH_URL` hinterlegen.
   * `tools/backup.sh` sendet nach jedem fehlerfreien, verschlüsselten Dump automatisch einen Ping an diesen Endpunkt. Bleibt das Backup aus, löst Uptime Kuma Alarm aus.

### 7.3 Benachrichtigungen & Fehler
* **SMTP-Alarmierung:** In Uptime Kuma unter *Einstellungen → Benachrichtigungen* SMTP mit den Vereins-Mail-Zugangsdaten (aus `.env.prod`) einrichten.
* **Django Error-Mailing:** Unbehandelte Serverfehler ab Stufe `ERROR` werden unabhängig von Uptime Kuma über das Django-Logging (`config/settings.py`) direkt per E-Mail an `DJANGO_ADMINS` gesendet.
* **Logs im laufenden Betrieb:**
  ```bash
  docker compose -f docker-compose.prod.yml logs -f app caddy backup uptime-kuma
  ```

### 7.4 Manueller Ausfalltest (Acceptance Test)
1. **App-Ausfall simulieren:**
   ```bash
   docker compose -f docker-compose.prod.yml stop app
   ```
   Innerhalb von ~60–90 Sekunden geht eine Alarm-Mail mit dem Betreff `[Down] Schachverein Portal` ein.
2. **Wiederanlauf prüfen:**
   ```bash
   docker compose -f docker-compose.prod.yml start app
   ```
   Innerhalb von 60 Sekunden trifft die Entwarnung `[Up] Schachverein Portal` ein.
3. **Backup-Monitor testen:** Bei Ausbleiben des täglichen Dumps alarmiert Uptime Kuma nach Ablauf der Karenzzeit.

---

## 8. Datenschutz-Aufgaben im laufenden Betrieb (PRD N1.3–N1.5)

| Aufgabe | Rhythmus | Befehl / URL |
| --- | --- | --- |
| Anonymisierung nach Austritt | jährlich | `manage.py anonymize_former_members --dry-run` → ohne `--dry-run` ausführen |
| Verzeichnis der Verarbeitungstätigkeiten | jährlich prüfen | `/datenschutz/verzeichnis.csv` |
| Datenauskunft (Ein-Klick PDF/JSON) | auf Anfrage | Mitgliedsseite → „Datenauskunft (DSGVO)“ |
| Audit-Protokoll sichten | quartalsweise | `/audit/` |
| Backup-Restore-Test | jährlich | Abschnitt 5 (Tabelle ergänzen) |

---

## 9. Alternative: Managed Deployment auf Scalingo (PaaS, EU)

Für den Betrieb **ohne Linux-Server-Administration** ist das Projekt für die europäische Plattform **Scalingo** vorbereitet (Rechenzentrum in der EU, 100 % DSGVO-konform, kein US Cloud Act):

### Bereitgestellte Dateien:
* `Procfile`: Definiert den Webprozess (`gunicorn`) und führt bei jedem Release automatisch `python manage.py migrate --noinput` aus.
* `runtime.txt`: Erzwingt Python 3.12.
* `scalingo.json`: Ermöglicht 1-Klick-Bereitstellung mit automatischem `postgresql:postgresql-sandbox` Addon und Standard-Umgebungsvariablen.
* `requirements.txt`: Beinhaltet `whitenoise` für effizientes Ausliefern statischer Dateien ohne separaten Webserver.

### Inbetriebnahme in 3 Schritten:
1. **App erstellen:** Auf [scalingo.com](https://scalingo.com) neue App mit Region *Europe (Paris / osc-fr1)* anlegen.
2. **PostgreSQL Addon hinzufügen:** Unter *Addons* das Addon **Scalingo PostgreSQL** buchen (setzt automatisch `SCALINGO_POSTGRESQL_URL`).
3. **Umgebungsvariablen setzen:**
   * `DJANGO_SETTINGS_MODULE=config.production`
   * `DJANGO_SECRET_KEY` (Zufallswert, mind. 50 Zeichen)
   * `IBAN_FERNET_KEY` (mit `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
   * `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` (+ SMTP-Zugangsdaten)
4. **Git Push:** Repository mit Scalingo verknüpfen (`scalingo git-setup` oder GitHub-Integration) und `git push scalingo main` ausführen.

