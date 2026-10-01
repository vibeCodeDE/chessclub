#!/bin/sh
set -eu

# Schachverein - Verschlüsseltes Datenbank-Backup (PRD N2.1 / ADR-009)
#
# Erzeugt einen pg_dump, komprimiert per gzip und verschlüsselt symmetrisch
# per OpenSSL AES-256-CBC (PBKDF2). Der Schlüssel darf niemals im Repository
# liegen und muss getrennt vom DB-Host gesichert werden.

POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-schachverein}"
POSTGRES_DB="${POSTGRES_DB:-schachverein}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# 1. Pflichtprüfung: Schlüssel vorhanden? (PRD N2.1)
if [ -z "${BACKUP_ENCRYPTION_KEY:-}" ]; then
    echo "FEHLER: BACKUP_ENCRYPTION_KEY ist nicht gesetzt. Backup wird abgebrochen (PRD N2.1 verlangt verschlüsselte Backups)." >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

# 2. Sicherstellen, dass openssl verfügbar ist
if ! command -v openssl >/dev/null 2>&1; then
    if command -v apk >/dev/null 2>&1; then
        apk add --no-cache openssl >/dev/null 2>&1
    else
        echo "FEHLER: openssl ist nicht installiert." >&2
        exit 1
    fi
fi

TIMESTAMP=$(date +%Y-%m-%d_%H%M)
BACKUP_FILE="${BACKUP_DIR}/schachverein_${TIMESTAMP}.sql.gz.enc"
TMP_FILE="${BACKUP_FILE}.tmp"

echo "Starte verschlüsseltes Backup für ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}..."

# 3. Dump -> Gzip -> OpenSSL AES-256-CBC (PBKDF2)
export PGPASSWORD="${POSTGRES_PASSWORD:-}"
if pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    | gzip -c \
    | openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -salt -pass "pass:${BACKUP_ENCRYPTION_KEY}" -out "$TMP_FILE"; then
    mv "$TMP_FILE" "$BACKUP_FILE"
    echo "Backup erfolgreich erstellt: ${BACKUP_FILE}"
else
    rm -f "$TMP_FILE"
    echo "FEHLER: Backup-Erstellung fehlgeschlagen." >&2
    exit 1
fi

# 4. Bereinigung alter Backups (Retention)
echo "Bereinige Backups älter als ${BACKUP_RETENTION_DAYS} Tage in ${BACKUP_DIR}..."
find "$BACKUP_DIR" -name 'schachverein_*.sql.gz.enc' -type f -mtime "+$BACKUP_RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name 'schachverein_*.sql.gz' -type f -mtime "+$BACKUP_RETENTION_DAYS" -delete

echo "Backup-Lauf abgeschlossen."
