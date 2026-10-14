# ADR-021: django-import-export im Django Admin (Mitglieder & Kassenbuch)

## Status
Accepted

## Date
2026-10-13

## Context
In [ADR-001](ADR-001-django-stack.md) wurde festgelegt, dass der Django-Admin einen wesentlichen Teil der Verwaltungs-UI übernimmt, damit der Vorstand Daten ohne Programmierkenntnisse pflegen kann.
Während in [ADR-020](ADR-020-vereinsstammdaten-in-der-datenbank.md) (T31) ein geführter Web- & CLI-Setup-Assistent für das erstmalige Einspielen von Mitgliederlisten und Vereinsstammdaten geschaffen wurde, fehlte im regulären Django Admin (`/admin/members/member/` und `/admin/cashbook/cashentry/`) eine standardisierte Import- und Exportmöglichkeit für den laufenden Vereinsalltag (PRD M1.5, S1.7, S6.2).

Wichtige Randbedingungen:
- Finanzdaten dürfen niemals gelöscht werden (ADR-005, ADR-006; GoBD-Konformität).
- Personenbezogene Daten und Zugriffe müssen DSGVO-konform im AuditLog protokolliert werden (PRD N1.5, [AGENTS.md](../../AGENTS.md)).
- Alle Validierungsregeln (z. B. Austrittsdatum nur bei Status „ausgetreten“, positive Kassenbuchbeträge) müssen auch beim Import streng greifen.

## Decision
1. **Integration von `django-import-export` (>=4.0):**
   - Hinzufügen von `django-import-export>=4.0` in `requirements.txt`.
   - Registrierung von `"import_export"` in `INSTALLED_APPS` und Aktivierung atomarer Transaktionen via `IMPORT_EXPORT_USE_TRANSACTIONS = True`.

2. **Ressourcen mit Modell-Validierung:**
   - **`MemberResource` (`members/resources.py`):**
     - Bildet die zentralen Felder von `Member` ab.
     - `ForeignKeyWidget` für `FeeCategory` über den Namen der Kategorie für benutzerfreundliche CSV-Exporte und -Importe.
     - `clean_model_instances = True` erzwingt `full_clean()` für jede importierte Zeile (verhindert inkonsistente Status- oder Datumswerte).
     - Übergabe des ausführenden Benutzers (`_changed_by`), damit Statuswechsel in `MemberStatusChange` historisiert werden.
   - **`CashEntryResource` (`cashbook/resources.py`):**
     - Bildet Einnahmen und Ausgaben ab.
     - Verknüpfung von `storno_von` über die Buchungs-ID.
     - Automatisches Setzen von `erfasst_von` auf den importierenden Admin-Benutzer.
     - `clean_model_instances = True` sichert Vorzeichen- und Betragsregeln ab.

3. **Admin-Integration & Revisionssicherheit (`ImportExportModelAdmin`):**
   - `MemberAdmin` und `CashEntryAdmin` erben von `ImportExportModelAdmin`.
   - `has_delete_permission` bleibt bei beiden Models strikt auf `False` deaktiviert – ein Löschen über den Admin ist technisch ausgeschlossen.
   - Überladene Hooks `get_data_for_export()` und `process_result()` erzeugen bei jedem Export und Import automatisch einen `AuditLog`-Eintrag mit Benutzer, Zeilenanzahl und Aktion.
   - Unbefugte Rollen (`kapitaen`, `mitglied`, Gäste) werden über Djangos Admin-Berechtigungen abgewiesen (HTTP 302/403).

## Consequences
- Der Vorstand kann Mitgliederlisten und Kassenbuchungen im Django Admin in gängigen Formaten (CSV, TSV, JSON) exportieren, selektiv Spalten wählen und neue Datensätze importieren.
- Strikte DSGVO- und Revisionskonformität: Jeder Export und Import wird im AuditLog protokolliert; Löschschutz bleibt vollständig aktiv.
- 12 neue Tests in `members/tests/test_member_import_export.py` und `cashbook/tests/test_cashbook_import_export.py` sichern den Export, Import, Audit-Trail und Negativtests ab.
