# Betrieb & Wiederherstellung (T21)

Anleitung für den Vereinsserver. Alles setzt **Docker Compose** voraus; die Daten
liegen ausschließlich auf vereinseigener Infrastruktur in DE/EU (PRD N1.1).

## 1. Erstinstallation

```bash
git clone <repo> /opt/schachverein && cd /opt/schachverein
cp .env.prod.example .env.prod      # Werte anpassen (siehe unten)
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec app python manage.py createsuperuser
docker compose -f docker-compose.prod.yml exec app python manage.py seed_demo   # optional: Demo-Daten
```

`.env.prod` (niemals ins Git):

| Variable | Bedeutung | Beispiel |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Langer Zufallswert | 64 Zeichen |
| `DJANGO_DEBUG` | Immer `0` | `0` |
| `DJANGO_ALLOWED_HOSTS` | Hostname(n) der Vereinsdomain | `portal.schachverein.de` |
| `POSTGRES_DB/USER/PASSWORD` | Datenbankzugang | `schachverein` / starkes Passwort |
| `EMAIL_BACKEND`, `EMAIL_HOST`, … | SMTP für Rundbriefe | `django.core.mail.backends.smtp.EmailBackend` |
| `CLUB_NAME`, `CLUB_SHORT`, `CLUB_CONTACT` | Absender/Impressum | siehe `config/settings.py` |
| `TWOFA_PFLICHT` | 2FA für den Vorstand | `1` (verbindlich) |
| `DSGVO_FRIST_TAGE` | Anonymisierung nach Austritt | `730` (2 Jahre) |
| `IBAN_FERNET_KEY` | Schlüssel für die IBAN-Verschlüsselung (ADR-010) | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

> **Der IBAN-Schlüssel ist Pflicht.** Ohne `IBAN_FERNET_KEY` startet der
> Produktivbetrieb nicht (der Container bricht mit einer Fehlermeldung ab).
> Den Schlüssel **einmal** erzeugen, in `.env.prod` eintragen und getrennt vom
> DB-Host sichern (z. B. Passwortmanager des Vorstands). Wird er verloren,
> sind die gespeicherten IBAN nicht mehr lesbar; wird er versehentlich
> geändert, meldet die App das mit einem klaren Hinweis, statt still leere
> Mandate zu zeigen. Niemals ins Repository einchecken.

## 2. TLS-reverse-Proxy

Die App lauscht nur auf `127.0.0.1:8000`. Davor läuft z. B. Caddy oder nginx mit
Let's-Encrypt-Zertifikat. Sobald TLS läuft, in `.env.prod` setzen:

```
SECURE_SSL_REDIRECT=1
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=1
CSRF_COOKIE_SECURE=1
CSRF_TRUSTED_ORIGINS=https://portal.schachverein.de
```

Danach `docker compose -f docker-compose.prod.yml up -d` neu starten.

## 3. Backup

Der Service `backup` schreibt täglich `backups/schachverein_JJJJ-MM-TT_HHMM.sql.gz`
und löscht Dateien, die älter als 30 Tage sind. Zusätzlich **monatlich eine Kopie
auf ein zweites Medium** legen (PRD N2.1: „3-2-1-Regel“):

```bash
rsync -av backups/ backup-nas:/verein-backups/schachverein/
```

## 4. Wiederherstellung (Restore)

```bash
# 1. Wartungsfenster: App anhalten (DB bleibt erreichbar)
docker compose -f docker-compose.prod.yml stop app

# 2. Leere Datenbank erzeugen
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U schachverein -c "DROP DATABASE IF EXISTS schachverein;" \
                          -c "CREATE DATABASE schachverein;"

# 3. Backup einspielen
gunzip -c backups/schachverein_2026-09-01_0300.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db \
  psql -U schachverein -d schachverein

# 4. App starten und prüfen
docker compose -f docker-compose.prod.yml start app
curl -fsS http://127.0.0.1:8000/health/     # {"status": "ok"}
```

### Restore-Test-Protokoll

| Datum | Version/Backup | Dauer | Ergebnis | Getestet von |
| --- | --- | --- | --- | --- |
| _ausfüllen_ | _z. B. 2026-09-01_0300_ | _z. B. 25 min_ | _Daten vollständig, Login ok_ | _Vorstand_ |

> Der Restore muss **einmal dokumentiert** durchgeführt werden (< 4 h, PRD N2.1).
> Jährlich wiederholen und die Zeile ergänzen.

## 5. Updates

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build     # migriert automatisch
docker compose -f docker-compose.prod.yml exec app python manage.py migrate --check
```

Vor jedem Update ein manuelles Backup anstoßen:

```bash
docker compose -f docker-compose.prod.yml exec backup sh -c \
  'pg_dump -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > /backups/manuell_$(date +%F_%H%M).sql.gz'
```

## 6. Monitoring & Fehlerbenachrichtigung

* `GET /health/` liefert `{"status": "ok"}` – für Uptime-Checks nutzen.
* Fehler ab Stufe `ERROR` gehen per E-Mail an `DJANGO_ADMINS` (siehe `LOGGING` in `config/settings.py`).
* Logs: `docker compose -f docker-compose.prod.yml logs -f app`.

## 7. Datenschutz-Aufgaben im Betrieb

| Aufgabe | Rhythmus | Befehl/Stelle |
| --- | --- | --- |
| Anonymisierung nach Austritt | jährlich | `manage.py anonymize_former_members --dry-run` → ohne `--dry-run` ausführen |
| Verzeichnis der Verarbeitungstätigkeiten | jährlich prüfen | `/datenschutz/verzeichnis.csv` |
| Datenauskunft | auf Anfrage | Mitgliedsseite → „Datenauskunft (DSGVO)“ |
| Audit-Protokoll sichten | quartalsweise | `/audit/` |
| Backup-Restore-Test | jährlich | Abschnitt 4 |
