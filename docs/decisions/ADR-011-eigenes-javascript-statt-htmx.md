# ADR-011: Eigenes JavaScript statt HTMX und Alpine.js (löst ADR-008 ab)

## Status
Accepted (setzt ADR-008 außer Kraft; ADR-008 wird nicht gelöscht)

## Date
2026-09-29

## Context
ADR-008 sah HTMX und Alpine.js als feste, versionierte Dateien in `static/vendor/` vor, um einzelne Abläufe ohne vollständigen Seitenaufbau zu erledigen. Der Vorteil sollte sein: weniger eigener Code, keine eigene Zustandsverwaltung.

Beim Zusammenführen der beiden Zweige (2026-09-29) lag bereits eine Umsetzung vor, die genau die Interaktionen ohne fremde Bibliothek umsetzt: `static/js/app.js` (Vanilla JS) und `core/ui.py` (Fragment-Antworten derselben Views, Erkennung über `X-Requested-With`). Es gibt kein `static/vendor/`, keinen `hx-`-Attribut und keine `x-data`-Bindung im Baum.

## Decision
- **Kleine Interaktionen werden mit eigenem JavaScript umgesetzt** (`static/js/app.js`), ohne Framework. Erkennungsmerkmale: AJAX-Fragment statt Vollseiten-Response, optimistische UI mit Rollback bei Fehler, Toasts, Bestätigungsdialoge, Quick-Filter, Service-Worker-Registrierung.
- **Jede Aktion funktioniert ohne JavaScript als normaler POST.** Das ist die eigentliche Regel: JavaScript verbessert, es ersetzt nichts. Die Fragment-Antwort wird nur bei `X-Requested-With` geliefert, sonst kommt die vollständige Seite.
- **Kein CDN, keine Drittanbieter-Assets, kein npm im Betrieb** (PRD N1.1). Es gibt keinen Build-Schritt für CSS oder JavaScript.
- **Serverseitig bleibt die Wahrheit.** Views sind Function-Based Views; die JSON-/Fragment-Antwort ist eine zweite Ausprägung derselben View, keine separate API.
- CSRF-Token wird bei jeder asynchronen Anfrage als Header mitgeschickt; ohne gültigen Token bleibt der POST abgewiesen.

## Alternatives Considered

### HTMX + Alpine.js umsetzen (ADR-008 unverändert)
- Pros: weniger eigener Code, deklarativ.
- Cons: zwei weitere Dateien, die manuell aktualisiert werden müssen, zwei Fremdbibliotheken mit eigenen Versionen und Fehlermodi, und ein Verständnis der Framework-Semantik, das der Betreiber nicht hat. Für die vorhandenen vier Interaktionen ist der eigene Code kleiner als die Einrichtung.
- Rejected: der Nutzen rechtfertigt die Abhängigkeit nicht; die Entscheidung wird ausdrücklich zurückgenommen, nicht verschoben.

### SPA (React/Vue)
- Rejected: siehe ADR-001.

### Unveränderte Vollseiten-Aktionen ohne jede Asynchronie
- Pros: am einfachsten zu verstehen.
- Cons: jede Mahnung, Zahlung und Kategorie-Abschaltung lädt die ganze Seite neu; bei der Beitragsübersicht mit bis zu 200 Zeilen ist das spürbar.
- Rejected: der Aufwand bleibt, die Wirkung ist dieselbe wie bei der Lösung mit Fragmenten.

## Consequences
- `static/js/app.js` ist Handverantwortung: Änderungen brauchen einen Test (`dues/tests/test_beitraege.py` prüft die Fragment-Antworten und den Fehlerfall) und einen Blick auf den Fallback ohne JavaScript.
- Zwei Stellen in der Doku sind zu aktualisieren, weil sie HTMX/Alpine nennen: `docs/prd.md` §3.8-Verweis auf T10b und der Planabschnitt zu T10b.
- T10b gilt als erledigt, weil das Ziel („Interaktion ohne Neuladen, ohne CDN, ohne Build") erreicht ist — die technische Lösung weicht bewusst ab.
