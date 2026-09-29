# ADR-007: Mahnbrief als druckbares HTML statt serverseitigem PDF

## Status
Accepted

## Date
2026-09-29 (Task T10)

## Context
PRD M2.5 nennt „Mahnbrief als PDF“. `tasks/plan.md` T10 nennt „druckbares HTML/PDF“. Der Vorstand druckt und versendet Mahnungen selbst. Vollständiges Design: `docs/superpowers/specs/2026-09-29-t10-mahnwesen-export-design.md`.

## Decision
Der Mahnbrief ist ein eigenständiges, druckoptimiertes HTML-Dokument. Der Browser erzeugt das PDF über „Drucken / Als PDF speichern“. Das PRD-Ziel „PDF“ ist damit auf diesem Weg erfüllt.

## Alternatives Considered

### Serverseitiges PDF (z. B. WeasyPrint)
- Pros: direkter Download.
- Cons: neue Abhängigkeit und Systembibliotheken im Docker-Image, Inhaltstests wären PDF-basiert.
- Rejected für v1: Aufwand ohne Mehrwert für einen manuellen Druckprozess.

## Consequences
- Keine neue Abhängigkeit, Tests bleiben HTML-basiert.
- Serverseitige PDFs sind später nachrüstbar, falls der Vorstand sie braucht (dann neue ADR).
- Der DSGVO-Auskunfts-Export (T23, PRD N1.2 „PDF“) muss dieselbe Frage separat entscheiden.
