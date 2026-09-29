# ADR-008: HTMX und Alpine.js (lokal) für kleine Interaktionen

## Status
Proposed (Umsetzung nach T10, Task T10b)

## Date
2026-09-29

## Context
ADR-001 setzt auf serverseitige Templates ohne SPA. Einzelne Abläufe (z. B. „Mahnung setzen“ in der Mahnliste, Filter in Listen) laden bei jeder Aktion die ganze Seite neu. Der Betrieb soll ohne Node-Build und ohne Drittanbieter-Assets auskommen (PRD N1.1). Der Betreiber pflegt die Software allein.

## Decision
- **HTMX** für Teilaktualisierungen und **Alpine.js** für kleine Client-Zustände (Dropdown, Modal, Burger-Menü).
- Beide werden als **feste, versionierte Dateien** in `static/vendor/` eingecheckt und von der App selbst ausgeliefert. Kein CDN, kein npm-Zwang im Betrieb.
- Views bleiben Function-Based Views. HTMX-Antworten sind Template-Fragmente derselben Views (Erkennung über den `HX-Request`-Header), keine zweite API.
- CSRF: Der Token wird bei jeder HTMX-Anfrage als Header mitgeschickt (`hx-headers` am `<body>`). Ohne gültigen Token bleibt der POST abgewiesen.
- Jede Aktion muss ohne JavaScript weiter funktionieren (normales Formular als Fallback), sonst zählt sie als nicht umgesetzt.

## Alternatives Considered

### SPA (React/Vue) + API
- Rejected: siehe ADR-001.

### django-tables2 + django-filter für Listen
- Pros: weniger eigener Listencode.
- Cons: T3 hat Liste und Filter bereits gebaut; die Bibliotheken würden Bestehendes ersetzen und der Zusatzpaket-Sparsamkeit aus ADR-001 widersprechen.
- Deferred: erneut bewerten, wenn bei T16–T20 (Teams, Turniere) mehrere ähnliche Listen entstehen.

### Serverseitiges PDF (WeasyPrint)
- Rejected: siehe ADR-007. Der DSGVO-Auskunfts-Export (T23) entscheidet die PDF-Frage separat.

### python-chess / PGN-Anzeige
- Rejected: keine PRD-Anforderung; wäre ein neues Feature, keine Ergänzung.

## Consequences
- Zwei kleine statische Dateien mehr im Repo, die bei Updates manuell ersetzt werden (Versionsnummer im Dateinamen, Hinweis in `docs/wartung.md`).
- Tests prüfen HTML-Fragmente und den Fallback ohne `HX-Request`-Header.
- Kein Einfluss auf N1.1: keine externen Anfragen.
