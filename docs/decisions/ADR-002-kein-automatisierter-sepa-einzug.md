# ADR-002: Kein automatisierter SEPA-Einzug, keine IBAN in der Software

## Status
Accepted

## Date
2026-09-28

## Context
PRD M2.3/M2.4: Der Verein zieht Beiträge per SEPA-Lastschrift ein. Ein automatisierter Einzug über eine Banking-API würde Zugangsdaten zur Vereinsbank und IBANs aller Mitglieder in der Software erfordern.

## Decision
Die Software verwaltet nur das **SEPA-Mandat** (Referenz, Datum, Status `aktiv`/`widerrufen`/`beendet`) und den **Zahlungsstatus**. Der Einzug erfolgt **bankseitig manuell** durch den Verein. Die Zahlungsart (SEPA-Einzug, Überweisung, Bar) wird je Buchung erfasst; eine SEPA-Buchung verlangt ein aktives Mandat.

- Keine IBAN, kein Bank-API-Zugang im Code.
- Abgesichert durch `dues/tests/test_keine_bank_api.py` (verbietet Netzwerk-Imports in `dues` und Bank-Endpunkte in den Settings).

## Alternatives Considered

### Banking-API / SEPA-XML-Erzeugung
- Pros: weniger manuelle Arbeit.
- Cons: Bankzugangsdaten und IBANs im System, höheres DSGVO- und Sicherheitsrisiko, deutlich mehr Umfang.
- Rejected: Für < 200 Mitglieder und einen jährlichen Lauf steht der Nutzen nicht im Verhältnis.

## Consequences
- Weniger personenbezogene Finanzdaten im System (DSGVO-freundlich).
- Der Vorstand bucht Zahlungen nach dem Bankeinzug manuell nach.
- Ein SEPA-XML-Export bleibt später nachrüstbar, ist aber nicht v1.
