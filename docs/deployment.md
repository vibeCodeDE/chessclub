# Betrieb & Wiederherstellung (T21)

Anleitung für den Vereinsserver. Die Abschnitte 1–7 setzen **Docker Compose** voraus;
die Daten liegen ausschließlich auf vereinseigener Infrastruktur in DE/EU (PRD N1.1).
Für Demos und Vorschauen gibt es in Abschnitt 8 eine Variante für **Vercel**.

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

## 8. Vercel (Demo & Vorschau)

Für Vorführungen und Vorschauen läuft die App auch auf Vercel. Der Echtbetrieb mit
Mitgliederdaten bleibt bei den Abschnitten 1–7 (PRD N1.1: Daten nur auf vereinseigener
Infrastruktur in DE/EU). Wer trotzdem echte Daten auf Vercel hält, braucht
Auftragsverarbeitungsverträge mit Vercel und dem Datenbankanbieter und legt Funktion
und Datenbank in die EU: `vercel.json` setzt die Funktion auf `fra1` (Frankfurt), die
Region der Datenbank wählst du beim Anlegen.

**So funktioniert es:** Vercel erkennt Django an `manage.py` und startet
`config.wsgi.application` als serverlose Funktion. `collectstatic` läuft im Build, die
statischen Dateien kommen vom Vercel-CDN. Die Funktion ist kurzlebig und hat kein
beschreibbares Dateisystem – die App braucht deshalb eine externe **PostgreSQL**-Datenbank
(SQLite funktioniert dort nicht). Migrationen laufen im Build: `vercel.json` ruft
`tools/vercel_build.py` auf.

### Einrichtung (einmalig im Vercel-Dashboard)

1. **Datenbank anlegen:** Projekt → *Storage* → PostgreSQL-Anbieter wählen (z. B. Neon),
   Region Frankfurt/EU, dem Projekt zuweisen und die Umgebungen *Production* und – für
   Vorschau-Deployments – *Preview* auswählen. Vercel setzt `DATABASE_URL` (über Pooler)
   und `DATABASE_URL_UNPOOLED` (direkt) selbst. Die App liest `DATABASE_URL` bzw.
   `POSTGRES_URL`; Migrationen laufen über die direkte Verbindung.
2. **Geheimen Schlüssel setzen:** *Settings → Environment Variables* →
   `DJANGO_SECRET_KEY` = langer Zufallswert, erzeugt mit
   `python -c "import secrets; print(secrets.token_urlsafe(64))"`. Ohne ihn gilt der
   öffentlich bekannte Entwicklungsschlüssel (das Build-Log warnt davor).
3. **System-Variablen freigeben:** Im selben Bereich muss die Option *Automatically expose
   System Environment Variables* aktiv sein (normalerweise ist sie es). Daran erkennt die
   App, dass sie auf Vercel läuft (`VERCEL=1`), und lässt die Vercel-Domains zu.
4. **Neu deployen:** *Deployments → Redeploy* oder ein neuer Commit. Der Build legt die
   Tabellen an.
5. **Prüfen:** `https://<projekt>.vercel.app/health/` muss `{"status": "ok"}` liefern,
   danach Startseite und Anmeldung.

### Optionale Variablen

| Variable | Wirkung |
| --- | --- |
| `SEED_DEMO=1` | Der Build legt Demo-Daten an, solange noch keine Mitglieder existieren (Logins: README). Nur für Demos – die Passwörter sind öffentlich bekannt. |
| `TWOFA_PFLICHT=0` | Zwei-Faktor-Pflicht für den Vorstand aus (nur Demo) |
| `DJANGO_ALLOWED_HOSTS` | eigene Domain(s), kommagetrennt, z. B. `portal.schachverein.de` |
| `MIGRATE_ON_BUILD=1` | migriert auch Preview-Builds. Ohne die Option migriert nur Production, denn Previews teilen sich die Datenbank oft mit Production. Hat jede Vorschau dank *Preview Branching* (Neon) eine eigene Datenbank-Kopie, ist die Option sinnvoll. |
| `EMAIL_BACKEND`, `EMAIL_HOST`, … | SMTP wie in Abschnitt 1; ohne SMTP landen Mails nur in den Funktions-Logs |
| `DJANGO_SETTINGS_MODULE=config.production` | strengere Settings; verlangt zusätzlich `DJANGO_EMAIL_BACKEND` (SMTP) |

Session- und CSRF-Cookies sind auf Vercel standardmäßig `Secure`. HTTPS-Erkennung und die
Weiterleitung von HTTP auf HTTPS übernimmt Vercel.

### Erstes Vorstandskonto

Ohne `SEED_DEMO` gibt es noch keine Benutzer. Das Konto entsteht lokal gegen die
Vercel-Datenbank:

```bash
vercel env pull .env.local          # Variablen des Projekts holen (nicht ins Git)
set -a; . ./.env.local; set +a
python manage.py createsuperuser
```

Danach im Django-Admin (`/admin/`) dem Konto die Gruppe `admin` geben – die Rollen folgen
den Gruppen, ohne sie fehlt die Vorstands-Navigation.

### Fehlersuche

| Symptom | Ursache und Abhilfe |
| --- | --- |
| `Bad Request (400)` auf jeder Seite | Die Domain ist in `ALLOWED_HOSTS` nicht erlaubt. Schritt 3 prüfen; eigene Domain in `DJANGO_ALLOWED_HOSTS` eintragen. Falls die System-Variablen nicht freigegeben werden sollen: `DJANGO_ALLOWED_HOSTS=.vercel.app` setzen. Danach neu deployen. |
| `Server Error (500)` auf `/`, aber `/health/` antwortet | Keine Datenbank oder keine Tabellen. Build-Log nach „Keine Datenbank-URL gefunden“ durchsuchen: dann fehlt `DATABASE_URL` in der Umgebung dieses Deployments (Schritt 1, Umgebungen prüfen). Preview-Builds migrieren nur mit `MIGRATE_ON_BUILD=1`. Ursache steht unter *Deployments → Logs*. |
| Build bricht bei `migrate` ab | Zugangsdaten und Erreichbarkeit der Datenbank prüfen. Die bisherige Version bleibt online. |
