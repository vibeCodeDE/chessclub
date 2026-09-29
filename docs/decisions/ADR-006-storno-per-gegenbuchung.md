# ADR-006: Falsche Zahlungen per Storno-Gegenbuchung aufheben, nie löschen

## Status
Accepted

## Date
2026-09-28 (Task T9)

## Context
Zahlungen werden manuell gebucht (PRD M2.4) und können falsch erfasst werden. Die Finanzhistorie unterliegt Aufbewahrungspflichten (PRD N1.3, § 147 AO). Vollständiges Design: `docs/superpowers/specs/2026-09-28-t9-zahlungserfassung-design.md`.

## Decision
- `Payment` hängt per `PROTECT`-FK am `FeePost`; es gibt keinen Lösch-Pfad.
- Eine Fehlbuchung wird durch eine **Gegenbuchung** (negativer Betrag, `storno_von`-FK) aufgehoben. Ein Storno eines Stornos ist nicht zulässig.
- Der offene Betrag ist `betrag − Summe der Zahlungen inkl. Stornos`, berechnet in `dues/services.py` über Annotationen (`Coalesce(Sum(...))`), ohne gespeichertes Summenfeld und ohne N+1.
- Überzahlung wird als **Gutschrift angezeigt** (negativer offener Betrag), nicht gekappt.
- `Payment` ist im Admin nur einsehbar; Anlegen nur über das Formular, Audit-Einträge „Zahlung gebucht/storniert“.

## Alternatives Considered

### Zahlungen editier-/löschbar
- Rejected: Historie ginge verloren, Widerspruch zur Aufbewahrungspflicht.

### Gespeichertes Summenfeld am Posten
- Rejected: kann von den Zahlungen abweichen; Annotation ist einfacher und konsistent.

## Consequences
- Lückenlose Buchungshistorie; T10 und T11b lesen dieselbe Regel aus `dues/services.py`.
- Korrekturen kosten eine zusätzliche Buchung.
