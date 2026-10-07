# ADR-016: DSB-Schnittstellen-Architektur (Mitgliedermeldung, DWZ-Sync, Meldeformate)

## Status
Accepted

## Date
2026-10-07

## Context
Der Deutsche Schachbund (DSB) und seine Landesverbände wickeln die Mitglieder- und Spielberechtigungsverwaltung zentral über das DSB-Mitgliederportal (auf Basis von *nuLiga / nu Datenautomaten GmbH*, ehemals MIVIS) ab. 

Für Vereine und externe Vereinssoftware existiert verbandseitig **keine offene Schreib-Schnittstelle (REST- oder GraphQL-API)**, über die Neuaufnahmen, Austritte oder Stammdatenmutationen direkt in das Verbandssystem eingespielt werden können. Gleichzeitig benötigen Schachvereine:
1. Aktuelle Wertungszahlen (DWZ, DWZ-Index) und Verbands-Identifikatoren (ZPS-Code, PKZ, FIDE-ID) ihrer Mitglieder für den Ligaspielbetrieb und Turniere.
2. Einen effizienten Weg, um turnusmäßige Meldungen (Bestandserhebung für Landessportbund/Landesverband zum 1. Januar sowie laufende Mutationen) ohne fehleranfälliges manuelles Abtippen im Verbandsportal durchzuführen.
3. Den standardisierten Export von Vereins-Turnierergebnissen zur DWZ-Auswertung (DeWIS / TRF).

## Decision
Wir etablieren ein **Drei-Säulen-Schnittstellenkonzept**, das die verbandlichen Realitäten abbildet, manuelle Doppelerfassung minimiert und strikt den DSGVO-Leitplanken des Projekts folgt:

### 1. Datenmodell & Identifikatoren (`members`)
Das `Member`-Modell wird um bundesweit einheitliche Verbandskennungen erweitert:
- `zps_nummer`: Vereins- und Spielernummer nach ZPS (Zentrale Pass-Stelle des DSB, z. B. `C0101-042`).
- `pkz`: Bundesweit eindeutige Personenkennziffer im DSB-System.
- `dwz` & `dwz_index`: Aktuelle Deutsche Wertungszahl und Berechnungskennziffer.
- `fide_id`: FIDE-Identifikationsnummer für international gewertete Spieler.
- `spielberechtigung`: Kennzeichnung von Erst- vs. Zweitmitgliedschaft (Gastspielrechte für Mannschaftskämpfe).

### 2. Lesender Verbandsabgleich (DWZ-Sync & Drift Detection)
- **Schnittstelle:** Nutzung der offiziellen **JSON-Schnittstelle des DSB-Wertungsportals** (Abruf der Vereinsmitgliederliste inkl. DWZ über den Vereinsschlüssel).
- **Service-Design:** Reiner Fachservice `members.services.dsb_sync` ohne HTTP-Abhängigkeit.
- **Ratenbegrenzung & Caching:** Abrufe werden maximal 1× täglich ausgeführt und serverseitig zwischengespeichert, um Verbandsserver zu schonen.
- **Drift Detection (Diskrepanzerkennung):** Visueller Abgleich für den Spielleiter/Vorstand:
  - Mitglieder, die im Verein aktiv sind, aber in der Verbandsliste fehlen (Meldung im Portal ausstehend).
  - Mitglieder mit abweichendem Status (beim Verband abgemeldet, im Verein noch geführt).
  - Automatische Übernahme aktualisierter DWZ-Werte.

### 3. Strukturierter Melde- & Mutationsexport (nuLiga / LSB-Bestandserhebung)
- **Mutations-Export:** Strukturierter CSV-Export für das DSB-/nuLiga-Portal mit Filterung auf Änderungen seit dem letzten Meldedatum:
  - Neuzugänge (Eintritte).
  - Abgänge (Austritte).
  - Adress- und Namenskorrekturen (aus genehmigten `ChangeRequest`-Vorgängen).
- **LSB-Jahresmeldung:** Vorgefertigter Export nach den Alters- und Geschlechtsrastern der Landessportbünde zum Stichtag 01.01.
- **Turnier-Auswertung (DeWIS / TRF):** Ergänzung des bestehenden ChessResults-Exports (S3.5 / Task T22) um das offizielle FIDE/DSB **TRF16-Format** bzw. DeWIS-XML, um Turniere direkt zur DWZ-Auswertung einreichen zu können.

### 4. Datenschutz- und Sicherheitsgrenzen (DSGVO N1.1, ADR-002, ADR-010)
- **Strikte Funktionstrennung:** Finanz- und Bankdaten (SEPA-Mandate, IBAN, Beitragsstatus, Mahnstufe) sind streng von sportlichen Verbandsdaten getrennt. Sie fließen unter keinen Umständen in Verbands-Exporte oder Schnittstellen.
- **Audit-Protokollierung:** Jeder DSB-Abruf und jeder Melde-Export wird im `AuditLog` mit Zeitstempel und ausführendem Vorstand protokolliert.

## Alternatives Considered

### Inoffizielles Browser-Scraping / Reverse Engineering des nuLiga-Portals
- *Verworfen:* Extrem fragil bei Änderungen an HTML/CSRF des Portals; Verstoß gegen Nutzungsbedingungen des Verbands; hohes Sicherheitsrisiko bei der Speicherung von Verbands-Zugangsdaten im Vereinsserver.

### Vollständig manuelle Pflege ohne Software-Unterstützung
- *Verworfen:* Führt zu Daten-Drift zwischen interner Mitgliederliste und Verbandsmeldeliste, erhöht Fehlerquote bei DWZ-Angaben und Mannschaftsmeldungen.

## Consequences
- Die Realität (keine Schreib-API beim DSB) ist architektonisch sauber gelöst, ohne unrealistische Annahmen über Verbands-APIs zu treffen.
- Die Software bietet maximale Arbeitserleichterung durch automatisierte DWZ-Aktualisierung und maßgeschneiderte Melde-Dateien.
- Die Anforderung K3.6 im PRD ist damit konkret spezifiziert.
