# ADR-010: IBAN verschlüsselt in der Datenbank (löst die IBAN-Sperre aus ADR-002 teilweise ab)

## Status
Accepted (ersetzt die Regel „keine IBAN in der Software" aus ADR-002; die Bank-API-Sperre aus ADR-002 bleibt unverändert in Kraft)

## Date
2026-09-29

## Context
ADR-002 hat festgelegt: kein Bank-API-Zugriff und **keine IBAN im System**, weil der Verein Einzüge bankseitig manuell auslöst. Beim Zusammenführen der beiden Zweige (2026-09-29) kam eine Implementierung herein, die die IBAN am SEPA-Mandat speichert, im Admin maskiert anzeigt, im PDF-Auskunftsbericht im Klartext ausgibt und im Demo-Datensatz befüllt.

Die Frage ist nicht „IBAN ja oder nein", sondern „wenn ja, wie". Ein Klartextfeld in der Datenbank schützt nichts: ein gestohlener Dump, ein SQL-Injection-Leser oder ein unverschlüsseltes Backup genügt, um die Kontoverbindung aller Mitglieder zu lesen. Ohne IBAN wäre die Maske („DE89 •••• 1300") im Grunde Informationskosmetik.

## Decision
- **Die IBAN wird verschlüsselt gespeichert**, nicht im Klartext. Verfahren: **Fernet** aus `cryptography` (AES-CBC mit HMAC, authentifizierte Verschlüsselung, getestete Implementierung). Neues Pragma `v1:` im Chiffretext, damit später eine Schlüsselrotation ohne Datenverlust möglich ist.
- **Der Schlüssel kommt aus der Umgebung** (`IBAN_FERNET_KEY`), nie aus der Datenbank, nie ins Repo, nie in ein eingechecktes Compose-File. Fehlt der Schlüssel, startet die App nicht — ein fehlender Schlüssel darf nicht stillschweigend zu „Klartext um einschalten" führen.
- **Keine Verschlüsselung der Datenbank als Ersatz:** die App muss zum Anzeigen entschlüsseln, der Klartext liegt also im Prozessspeicher. Verschlüsselung auf Spaltenebene schützt gegen gestohlene Dumps, Backups und Datenträger — **nicht** gegen jemanden mit Shell- oder Code-Zugriff auf den Container.
- **Ein nicht umkehrbares Feld `iban_kurz` (letzte vier Stellen) wird zusätzlich im Klartext geführt.** Dadurch müssen Listen, Badges und Auswertungen nicht entschlüsseln, und der Admin muss pro Zeile keine Entwchlüsselung und keine zusätzliche Abfrage machen.
- **Klartext-IBAN nur an zwei bewussten Stellen:** in der Mandats-Detailansicht und im DSGVO-Auskunftsbericht der betroffenen Person. Beides wird im `AuditLog` protokolliert. Der Mahnbrief zeigt Maske und Kontoinhaber, nicht die IBAN.
- **Kein Logging der IBAN.** Der `AdminEmailHandler` verschickt Tracebacks; ein SQL-Backend mit Debug-Logging schreibt Feldwerte mit. Deshalb: `DEBUG=False` im Betrieb (`config/production.py` erzwingt das) und kein Statement-Logging auf `django.db.backends` in Produktion.
- **Die Bank-API-Sperre aus ADR-002 bleibt.** Es gibt weiterhin keinen Netzwerkzugriff aus `dues`; `dues/tests/test_keine_bank_api.py` sichert das maschinell ab.
- **Nicht Bestandteil dieser Entscheidung** und bewusst offen gelassen: Suche/Sortierung nach IBAN und die Erkennung doppelter Mandate. Beides ginge nur über einen Blind-Index (HMAC über die normalisierte IBAN mit einem zweiten Schlüssel) und wird erst gebaut, wenn ein Anwendungsfall existiert.

## Alternatives Considered

### IBAN gar nicht speichern (ADR-002 unverändert)
- Pros: einfachster Weg, keine neue Abhängigkeit, kleinste Angriffsfläche.
- Cons: die Maske im Admin wäre wertlos, der Vorstand müsste die Kontoverbindung je Mandat von Hand nachtragen, und der DSGVO-Auskunftsbericht wäre unvollständig.
- Rejected: die Funktion ist für den Vorstand sinnvoll, sobald die Datenhaltung es aushält.

### Klartext in der Datenbank
- Rejected: schützt keinen der Fälle, die tatsächlich auftreten (Dump, Backup, SQL-Leser).

### Verschlüsselung auf Datenbankebene (pgcrypto, TDE)
- Pros: für alle Felder automatisch, keine App-Änderung.
- Cons: `pg_dump` enthält die Daten weiterhin im Klartext, solange man für den Restore entschlüsseln muss; die Sicherheit hängt am Dump-Workflow, nicht am Feld. Zusätzlich ist die Dev-/Test-Umgebung (SQLite) damit nicht abgedeckt.
- Rejected: löst das Problem nicht an der Wurzel und erzeugt eine zweite Abhängigkeit vom DB-Betrieb.

### `django-fernet-fields`
- Pros: fertiges Django-Feld.
- Cons: eine weitere Abhängigkeit, undurchsichtiger Umgang mit Schlüsselrotation und Backfill.
- Rejected: für ein einzelnes Feld ist eine eigene Feldklasse mit rund 30 Zeilen die kleinere und durchsichtigere Lösung.

## Consequences
- `cryptography` kommt als neue Abhängigkeit in `requirements.txt`; `IBAN_FERNET_KEY` in `.env.prod.example` und `config/settings.py`.
- Suchen, Sortieren und Eindeutigkeitsprüfungen auf der IBAN sind mit dem Chiffretext nicht möglich (siehe oben).
- Die Datenmigration vom Klartext auf den Chiffretext ist eine eigene, einmalige Migration; bestehende Installationen müssen den Schlüssel **vor** dem ersten Start mit der neuen Version setzen, sonst bricht der Start ab.
- `dues` bekommt Tests: Chiffretext in der Datenbank, Entschlüsselung nur über das Feld, Maske in Listen, kein Klartext im Audit-Log, Startabbruch ohne Schlüssel.
- Der Aufwand für den Vorstand bleibt klein: Die IBAN wird wie bisher im Mandatsformular gepflegt.
