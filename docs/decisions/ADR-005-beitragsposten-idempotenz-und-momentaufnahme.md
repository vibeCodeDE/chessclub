# ADR-005: Beitragsposten – Idempotenz über Constraint, Betrag als Momentaufnahme

## Status
Accepted

## Date
2026-09-28 (Task T8)

## Context
Der Jahresbeitragslauf (PRD M2.2) darf bei doppelter Ausführung nichts doppelt buchen. Spätere Änderungen an Beitragssätzen dürfen bereits gebuchte Finanzhistorie nicht überschreiben.

## Decision
- `FeePost` mit `unique_together` über **Mitglied × Jahr**. Diese Constraint *ist* die Idempotenz, es gibt kein Lauf-Flag. Ein zweiter Lauf ergänzt nur, was fehlt (z. B. im Jahresverlauf beigetretenes Mitglied).
- Kategorie und Betrag werden als **Momentaufnahme** im Posten gespeichert. `PROTECT` auf Mitglied und Kategorie.
- Regelbasis in `dues/services.py`: `plan_lauf` (Vorschau ohne Schreibzugriff) und `fuehre_lauf` (atomar). Damit nutzen Export (T10) und Kassenbericht (T11b) dieselben Zahlen.
- Kein eigenes Lauf-Modell: Nachvollziehbarkeit über `core.AuditLog` (eine Sammelzeile je Lauf; ein leerer Wiederholungslauf schreibt keine Zeile).
- `passiv` ist laut PRD nicht als beitragspflichtig definiert: Der Lauf-Dialog hat einen Schalter, Default „nicht buchen“ (Entscheidung mit dem Menschen, 2026-09-28).
- Fehlt der Satz einer Kategorie, bricht der Lauf ohne Teilbuchung ab, statt 0-€-Posten anzulegen.

## Alternatives Considered

### Pauschaler Abbruch bei bestehendem Lauf
- Rejected: Nachzügler bekämen nie einen Posten.

### Eigenes Lauf-Modell
- Rejected: Der Audit-Log reicht als Nachweis; ein zweites Modell wäre Duplikat.

## Consequences
- Satzänderungen wirken nur auf zukünftige Läufe, nie rückwirkend.
- Die Korrektur eines falschen Posten-Betrags läuft über das Admin mit Alt/Neu-Audit; ein Storno für Beitragsposten ist nicht Teil von v1.
