# ADR-009: Betrieb mit Caddy, restic und Uptime Kuma

## Status
Proposed (Umsetzung mit T24 bzw. T24b)

## Date
2026-09-29

## Context
T24 verlangt TLS-Vorbereitung per Reverse Proxy, nächtliche verschlüsselte Backups mit getrennt gelagertem Schlüssel und einen dokumentierten Restore. PRD N2.1 nennt dafür „pg_dump, komprimiert + verschlüsselt, z. B. GPG/age“. Der Betreiber hat keine Admin-Erfahrung mit nginx/certbot und soll möglichst wenig konfigurieren.

## Decision
- **Reverse Proxy: Caddy** als Container vor der App. Automatisches Let’s Encrypt, Konfiguration in wenigen Zeilen (`Caddyfile`), HSTS und Weiterleitung HTTP→HTTPS ohne Zusatzwerkzeuge.
- **Backup: pg_dump + restic.** Ein Backup-Container erzeugt den Dump und übergibt ihn per Pipe an restic (Verschlüsselung, Deduplizierung, Aufbewahrungsregeln). Ziel: S3-kompatibler Speicher oder SFTP-Speicher in der EU/DE (z. B. Hetzner Storage Box). Das Repository-Passwort liegt nicht im Repo und nicht auf dem DB-Host. restic erfüllt „verschlüsselt“ aus N2.1 anstelle von GPG/age; der PRD-Wortlaut („z. B.“) bleibt gültig.
- **Monitoring: Uptime Kuma** (eigener Container, nur intern erreichbar oder hinter Caddy mit Login). Prüft die Health-Check-Route und meldet ein ausbleibendes Backup per Push-Monitor. Eigener Task T24b, weil es nicht für den v1-Betrieb nötig ist.

## Alternatives Considered

### nginx + certbot
- Cons: zwei Bausteine, Erneuerung per Cron/Timer, mehr Konfiguration.
- Rejected: Caddy leistet dasselbe mit weniger Wartung.

### Nur pg_dump + GPG/age (Status quo von T24)
- Pros: keine neue Software.
- Cons: Aufbewahrung, Rotation und Integritätsprüfung müssen selbst gebaut werden.
- Rejected: restic liefert das fertig und hat einen `check`-Befehl für den Restore-Test.

### Coolify / Dokploy
- Rejected: eigene Plattform mit eigener Datenbank und Oberfläche, für eine App mit zwei Containern überdimensioniert.

### Litestream
- Rejected: setzt SQLite voraus; das Projekt nutzt PostgreSQL (ADR-001).

## Consequences
- T24 wird um Caddy und restic erweitert (Restore-Test, korruptes Backup und fehlender Schlüssel bleiben Pflicht-Negativtests).
- Neue Container: `caddy`, `backup` (T24), `uptime-kuma` (T24b). `docker-compose.prod.yml` bleibt die einzige Prod-Datei.
- Neue Anforderung N2.8 (Monitoring, Sollte) wird im PRD geführt und T24b zugeordnet.
- `docs/deployment.md` nennt Speicherort und Standort des restic-Ziels (Nachweis EU/DE, N1.1).
- Uptime Kuma speichert keine Personendaten der Mitglieder; Alarm-E-Mails enthalten nur Dienstnamen und Zeitstempel.
