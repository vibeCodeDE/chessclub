#!/bin/sh
set -eu

# Schachverein - Wiederherstellung aus verschlüsseltem Backup (PRD N2.1 / ADR-009)
#
# Entschlüsselt ein mit tools/backup.sh erstelltes Backup per OpenSSL AES-256-CBC,
# prüft die Integrität und spielt den Dump in die Datenbank ein.

POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-schachverein}"
POSTGRES_DB="${POSTGRES_DB:-schachverein}"

USAGE="Verwendung: $0 <pfad-zu-schachverein_*.sql.gz.enc> [--check-only]"

if [ $# -lt 1 ]; then
    echo "$USAGE" >&2
    exit 1
fi

BACKUP_FILE="$1"
CHECK_ONLY="${2:-}"

# 1. Pflichtprüfung: Schlüssel vorhanden?
if [ -z "${BACKUP_ENCRYPTION_KEY:-}" ]; then
    echo "FEHLER: BACKUP_ENCRYPTION_KEY ist nicht gesetzt." >&2
    exit 1
fi

# 2. Prüfen, ob Datei existiert
if [ ! -f "$BACKUP_FILE" ]; then
    echo "FEHLER: Backup-Datei '${BACKUP_FILE}' existiert nicht." >&2
    exit 1
fi

# 3. Sicherstellen, dass openssl verfügbar ist
if ! command -v openssl >/dev/null 2>&1; then
    if command -v apk >/dev/null 2>&1; then
        apk add --no-cache openssl >/dev/null 2>&1
    else
        echo "FEHLER: openssl ist nicht installiert." >&2
        exit 1
    fi
fi

export BACKUP_ENCRYPTION_KEY

# 4. Vorprüfung / Entschlüsselungstest & Gzip-Integrität (ohne DB-Änderung)
echo "Prüfe Schlüssel und Integrität von ${BACKUP_FILE}..."
if ! openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -pass env:BACKUP_ENCRYPTION_KEY -in "$BACKUP_FILE" 2>/dev/null | gzip -t 2>/dev/null; then
    echo "FEHLER: Entschlüsselung oder Integritätsprüfung fehlgeschlagen. Falscher Schlüssel oder korrupte Datei. Datenbank wurde NICHT verändert." >&2
    exit 2
fi

if [ "$CHECK_ONLY" = "--check-only" ] || [ "$CHECK_ONLY" = "--dry-run" ]; then
    echo "Integritätsprüfung erfolgreich: Backup kann mit diesem Schlüssel entschlüsselt werden."
    exit 0
fi

echo "Entschlüsselung verifiziert. Starte Einspielen in ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}..."

# 5. Einspielen in die Datenbank
export PGPASSWORD="${POSTGRES_PASSWORD:-}"
if openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -pass env:BACKUP_ENCRYPTION_KEY -in "$BACKUP_FILE" \
    | gunzip -c \
    | psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB"; then
    echo "Wiederherstellung von ${BACKUP_FILE} erfolgreich abgeschlossen."
else
    echo "FEHLER: Fehler beim Einspielen der SQL-Befehle in die Datenbank." >&2
    exit 1
fi
