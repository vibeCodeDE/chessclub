# Spec: SEPA-XML-Export (pain.008) für Beitragsläufe (T9c)

## Ziel
Kassenwarte können für jeden Beitragslauf eine standardkonforme SEPA-Lastschriftdatei (`pain.008.001.02`) herunterladen, um sie direkt im Online-Banking ihrer Bank (Sparkasse, Volksbank etc.) als Sammellastschrift einzureichen.

## Anforderungen & Richtlinien
- **Standard:** ISO 20022 `pain.008.001.02` (EPC SEPA Core Direct Debit, B2C, Sequence Type `RCUR`).
- **Keine Bank-API:** Keine FinTS/EBICS-Verbindungen, keine Netzwerkbibliotheken in `dues`, keine Bank-Endpunkte in den Settings (ADR-002, abgesichert durch `test_keine_bank_api.py`).
- **Kryptografie & DSGVO:** IBANs liegen nach ADR-010 verschlüsselt in der Datenbank (`VerschluesseltesIbanField`, Fernet). Die Entschlüsselung erfolgt rein flüchtig im Arbeitsspeicher bei der XML-Erzeugung.
- **Audit-Protokollierung:** Jeder SEPA-XML-Export wird im `AuditLog` protokolliert (Aktion: `SEPA-XML-Export`), ohne dass Klartext-IBANs im Logtext erscheinen.
- **Berechtigung:** Ausschließlich die Rolle `admin` (Vorstand/Kassenwart) hat Zugriff (PRD §3.8). Negativtests für alle anderen Rollen (Mitglied, Kapitän -> 403).
- **Abfrage-Effizienz:** O(1) Datenbankabfragen (`select_related("member", "member__sepa_mandat")`, `prefetch_related("zahlungen")`).

## Datenmodell & Filterung
Einzuziehende Posten für das gewählte Beitragsjahr `jahr`:
- `fee.jahr == jahr`
- `fee.ist_offen == True` (Posten nicht voll bezahlt und nicht erlassen, `offener_betrag > 0`)
- `fee.member.sepa_mandat.status == SepaMandate.Status.AKTIV`
- Mandat besitzt gültige IBAN und `erteilt_am`

Nicht eingezogene Posten:
- Bereits bezahlte Posten (`status == BEZAHLT` oder `offener_betrag == 0`)
- Posten ohne SEPA-Mandat oder mit Status `widerrufen`
- Erlassene Posten (`status == ERLASSEN`)

Einzugsbetrag je Lastschrift:
- `fee.offener_betrag` (ermöglicht auch den Einzug von Restbeträgen bei Teilzahlungen)

## SEPA-XML-Struktur (pain.008.001.02)
- Root: `<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02">`
- `<CstmrDrctDbtInitn>`
  - `<GrpHdr>`:
    - `<MsgId>`: `MSG-{jahr}-{timestamp}` (max 35 Zeichen)
    - `<CreDtTm>`: ISO 8601 `YYYY-MM-DDThh:mm:ss`
    - `<NbOfTxs>`: Anzahl der Lastschriften
    - `<CtrlSum>`: Kontrollsumme aller Beträge (2 Dezimalstellen)
    - `<InitgPty><Nm>`: Name des Gläubigers (max 70 Zeichen)
  - `<PmtInf>`:
    - `<PmtInfId>`: `PMT-{jahr}-{timestamp}` (max 35 Zeichen)
    - `<PmtMtd>DD</PmtMtd>`
    - `<NbOfTxs>`, `<CtrlSum>`
    - `<PmtTpInf>`:
      - `<SvcLvl><Cd>SEPA</Cd></SvcLvl>`
      - `<LclInstrm><Cd>CORE</Cd></LclInstrm>`
      - `<SeqTp>RCUR</SeqTp>`
    - `<ReqdColltnDt>`: Gewünschtes Ausführungsdatum `YYYY-MM-DD`
    - `<Cdtr><Nm>`: Gläubigername
    - `<CdtrAcct><Id><IBAN>`: Gläubiger-IBAN
    - `<CdtrAgt><FinInstnId>`: BIC oder `<Othr><Id>NOTPROVIDED</Id></Othr>`
    - `<ChrgBr>SLEV</ChrgBr>`
    - `<CdtrSchmeId><Id><OrgId><Othr><Id>{CI}</Id><SchmeNm><Prtry>SEPA</Prtry></SchmeNm></Othr></OrgId></Id>`
    - `<DrctDbtTxInf>` je Posten:
      - `<PmtId><EndToEndId>`: `BEITRAG-{jahr}-{member_id}`
      - `<InstdAmt Ccy="EUR">`: Betrag `0.00`
      - `<DrctDbtTx><MndtRltdInf>`:
        - `<MndtId>`: Mandatsreferenz (max 35 Zeichen)
        - `<DtOfSgntr>`: Erteilt am `YYYY-MM-DD`
        - `<AmdmntInd>false</AmdmntInd>`
      - `<DbtrAgt><FinInstnId><Othr><Id>NOTPROVIDED</Id></Othr></FinInstnId></DbtrAgt>`
      - `<Dbtr><Nm>`: Kontoinhaber (oder Vorname Nachname, max 70 Zeichen)
      - `<DbtrAcct><Id><IBAN>`: Debitor-IBAN
      - `<RmtInf><Ustrd>`: Verwendungszweck (max 140 Zeichen)

## Zeichensatz-Bereinigung (`sepa_sanitize`)
Nur erlaubte SEPA-Zeichen gemäß EPC (`[a-zA-Z0-9/-?:().,'+ ]`). Deutsche Umlaute und Sonderzeichen werden ersetzt (`ä`->`ae`, `ö`->`oe`, `ü`->`ue`, `ß`->`ss`, `&`->`+`).
