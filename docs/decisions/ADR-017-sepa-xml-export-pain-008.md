# ADR-017: SEPA-XML-Export (pain.008) für Beitragsläufe

## Status
Accepted (ergänzt ADR-002 und ADR-010; die Bank-API-Sperre aus ADR-002 bleibt unverändert in Kraft)

## Date
2026-10-07

## Context
In ADR-002 wurde entschieden, keinen automatisierten Bank-API-Zugriff (wie FinTS oder EBICS) zu implementieren, um keine Vereinsbank-Zugangsdaten in der Software vorhalten zu müssen. Der Beitragseinzug erfolgt bankseitig manuell durch den Kassenwart. In ADR-010 wurde geregelt, dass die IBAN der Mitglieder verschlüsselt in der Datenbank gespeichert wird (Fernet AES-CBC + HMAC, Schlüssel aus Umgebung).

Das manuelle Abtippen von Dutzenden oder Hunderten Lastschriften im Online-Banking ist für den Kassenwart jedoch fehleranfällig und zeitintensiv. Der Kassenwart benötigt eine Möglichkeit, eine standardisierte Lastschriftdatei herunterzuladen, um sie mit zwei Klicks im Online-Banking des Vereins (z. B. Sparkasse, Volksbank, Deutsche Bank) als Sammelauftrag hochzuladen.

## Decision
- **Standardisierter SEPA-XML-Download nach ISO 20022 `pain.008.001.02` (EPC SEPA Core Direct Debit / B2C-Basislastschrift, Sequenztyp `RCUR`).**
- **Keine Fremdbibliotheken, keine Netzwerk-Imports:** Die XML-Generierung erfolgt ausschließlich über die Python-Standardbibliothek (`xml.etree.ElementTree`). Es werden weder `pysepa` noch HTTP- oder Socket-Bibliotheken importiert. Die Bank-API-Sperre aus ADR-002 und `dues/tests/test_keine_bank_api.py` bleibt zu 100 % erhalten.
- **In-Memory-Entschlüsselung:** Die nach ADR-010 verschlüsselt gespeicherten IBANs werden ausschließlich während der XML-Generierung im Prozessspeicher entschlüsselt und in den XML-Download geschrieben. Es erfolgt keine Speicherung der Klartext-IBANs auf der Festplatte, im Cache oder in temporären Dateien.
- **DSGVO & Audit-Protokollierung:** Das Erzeugen/Herunterladen der SEPA-XML gilt als Zugriff auf sensible Bankdaten (DSGVO N1.5). Jeder Export erzeugt einen Eintrag im `AuditLog` mit Benutzer, Zeitstempel, Beitragsjahr, Anzahl der Posten und Gesamtsumme – jedoch **ohne Klartext-IBANs** im Protokolltext.
- **Berechtigung:** Zugriff nur für die Vorstandsgruppe (`role_required(ADMIN_GROUP)`). Kapitäne, Mitglieder und Gäste erhalten HTTP 403 bzw. werden abgewiesen.
- **SEPA-Zeichensatzbereinigung:** Automatische Konvertierung von Umlauten (`ä`→`ae`, `ö`→`oe`, `ü`→`ue`, `ß`→`ss`) und Sonderzeichen gemäß dem offiziellen EPC-Zeichensatz, um Abweisungen durch Bankportale sicher zu verhindern.
- **Konfiguration des Gläubigers:** Gläubiger-Identifikationsnummer (`SEPA_CREDITOR_ID`), Vereins-IBAN (`SEPA_CREDITOR_IBAN`), Gläubigername (`SEPA_CREDITOR_NAME`, Fallback `CLUB_NAME`) und optional BIC (`SEPA_CREDITOR_BIC`) werden über Umgebungsvariablen gesteuert.

## Consequences
- Der Kassenwart spart stundenlange manuelle Tipparbeit und kann Beitragsläufe mit wenigen Klicks bei seiner Hausbank einreichen.
- Keine Sicherheitsrisiken durch gespeicherte Bank-PINs oder HBCI-/EBICS-Schlüssel im Webserver.
- 100 % DSGVO-konform durch verschlüsselte Persistenz, In-Memory-Verarbeitung und lückenlose Audit-Protokollierung.
- Wartungsfrei und zukunftssicher durch Verzicht auf externe Bibliotheken.
