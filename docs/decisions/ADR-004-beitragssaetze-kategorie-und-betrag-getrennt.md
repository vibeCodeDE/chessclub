# ADR-004: Beitragskategorie und Jahresbetrag getrennt modellieren

## Status
Accepted

## Date
2026-09-28 (Task T7)

## Context
Beitragssätze (Erwachsene, Jugend, Familie, ermäßigt) ändern sich von Jahr zu Jahr (PRD M2.1). Eine Änderung für 2027 darf gebuchte oder vergangene Jahre nicht verändern.

## Decision
- `FeeCategory`: jahresunabhängige Identität (`code` unique, `bezeichnung`, `aktiv`).
- `FeeAmount`: (Kategorie, Jahr, Betrag) mit `unique_together`.
- `Member.beitragskategorie`: FK mit `null=True`. `null` bedeutet „keine Kategorie“; der Beitragslauf (T8) überspringt solche Mitglieder, statt 0 € zu buchen.
- Seed per Datenmigration `0002_seed_beitragssaetze` (4 Kategorien × 2026/2027, **Platzhalterbeträge**, `get_or_create` = idempotent). Die echten Vereinssätze werden im Admin gepflegt.
- Negativtests greifen in `FeeAmount.clean()` (Betrag < 0) und `Member.clean()` (ausgetreten + Kategorie).

## Alternatives Considered

### Betrag direkt an der Kategorie
- Rejected: Jahreswechsel bräuchte einen Kopier-Job oder überschriebe alte Beträge.

## Consequences
- Der Jahreswechsel ist eine neue `FeeAmount`-Zeile, kein Kopiervorgang.
- Fehlt für (Kategorie, Jahr) ein Satz, bricht der Beitragslauf mit klarer Meldung ab (ADR-005).
