# ADR-003: Änderungswunsch-Workflow statt direktem Editieren durch Mitglieder

## Status
Accepted

## Date
2026-09-28

## Context
Mitglieder sollen ihre Daten einsehen und Korrekturen anstoßen können (PRD M1.4). Stammdaten sind Grundlage für Beitragsläufe, Mahnungen und DSGVO-Auskunft und müssen nachvollziehbar bleiben (M7.3).

## Decision
Ein Mitglied sieht seine Daten unter `/profil/` und reicht einen **Änderungswunsch** ein (Feld + Wunschwert). Der Admin prüft und gibt frei oder lehnt ab. Erst die Freigabe schreibt den Wert und einen Audit-Eintrag (Alt/Neu). Ohne Freigabe ändert sich das Stammdatum nicht.

## Alternatives Considered

### Direktes Editieren durch das Mitglied
- Pros: weniger Aufwand für den Vorstand.
- Cons: ungeprüfte Änderungen an Anschrift/Bankbezug-relevanten Daten, schwerer nachvollziehbar.
- Rejected: Der Vorstand will die Kontrolle behalten.

## Consequences
- Zusätzlicher Freigabe-Schritt für den Vorstand.
- Vollständige Nachvollziehbarkeit im `AuditLog`.
- Mitglieder erhalten keinen Zugriff auf die Admin-Detailseite (PRD §3.8).
