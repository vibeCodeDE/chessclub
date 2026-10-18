# Quickstart & Validierungsleitfaden: Schmerzpunkte, Lösungen & Interaktive Vorschau

**Feature**: `003-produkt-schmerzpunkte-vorschau`  
**Date**: 2026-10-17  
**Status**: Ready for Implementation  

---

## Voraussetzungen & Setup

1. **Entwicklungsumgebung**:
   - Docker Compose Umgebung läuft: `docker compose up -d`
   - ODER lokales Python-Environment aktiv (Django 5, PostgreSQL)

2. **Relevante Dateien**:
   - Datenmodell: [`core/produkt.py`](file:///C:/Users/xyxyx/Desktop/development/core/produkt.py) (`ROLLEN_SCHMERZPUNKTE`)
   - View: [`core/views.py`](file:///C:/Users/xyxyx/Desktop/development/core/views.py) (`produkt_seite`)
   - Template: [`core/templates/core/produkt.html`](file:///C:/Users/xyxyx/Desktop/development/core/templates/core/produkt.html)
   - Styles: [`static/css/landing.css`](file:///C:/Users/xyxyx/Desktop/development/static/css/landing.css)
   - Tests: [`core/tests/test_produkt.py`](file:///C:/Users/xyxyx/Desktop/development/core/tests/test_produkt.py)

---

## Validierungsszenarien

### Szenario 1: Automatisierte Test-Suite ausführen

Prüft Datenvollständigkeit, Routing, Null-Script-Konformität und fehlerfreies Rendering.

```bash
docker compose exec app pytest core/tests/test_produkt.py
```

**Erwartetes Ergebnis**:
- Alle Tests grün (`5 passed` oder mehr).
- Keine Regressionen bei bestehenden Tests.

---

### Szenario 2: Sichtprüfung & Rollenwechsel (Desktop 1280 px)

1. Entwicklungs-Server starten / aufrufen:
   `http://localhost:8000/` (oder mit gesetztem `IS_MARKETING_SITE=1`).
2. Zum Abschnitt **„Schmerzpunkte & Lösungen“** scrollen.
3. Nacheinander auf die Rollen-Tabs klicken:
   - *1. Vorsitzender / Vorstand*
   - *Kassenwart / Finanzen*
   - *Turnierleiter / Spielleiter*
   - *Mannschaftsführer*
   - *Mitglieder & Eltern*

**Erwartetes Ergebnis**:
- Der Wechsel erfolgt augenblicklich (< 50 ms) ohne Seiten-Reload.
- Schmerzpunkte („Vorher“) und Software-Lösungen („Mit Schachverwaltung“) passen zur gewählten Rolle.
- Die rechte Vorschau-Box aktualisiert sich auf das jeweilige Modul (z. B. Beitrags-SEPA-Lauf bei Kassenwart, Schweizer System bei Spielleiter).
- Innerhalb der Vorschau-Box lassen sich Schalter umschalten (z. B. Mahnstufen, Rundenpaarungen).

---

### Szenario 3: Mobile Ansicht & Overflow-Prüfung (360 px)

1. Entwicklertools im Browser öffnen (`F12`).
2. Bildschirmbreite auf **360 px** einstellen (z. B. Mobile Device Emulation).
3. Die Schmerzpunkte-Sektion und die Vorschau-Box prüfen.
4. In der Browser-Konsole prüfen:
   ```javascript
   console.assert(document.documentElement.scrollWidth <= window.innerWidth, "Horizontaler Overflow erkannt!");
   ```

**Erwartetes Ergebnis**:
- Kein horizontaler Scrollbalken auf der Seite.
- Die Rollen-Tabs lassen sich horizontal wischen/scrollen oder brechen sauber um.
- Die Vorschau-Karten passen sich proportional an die Displaybreite an.

---

### Szenario 4: Progressive Enhancement (JavaScript deaktiviert)

1. In den Browsereinstellungen oder via DevTools JavaScript vollständig deaktivieren.
2. Seite neu laden.

**Erwartetes Ergebnis**:
- Alle Texte, Schmerzpunkte und Lösungen sind weiterhin vollständig sichtbar und lesbar.
- Das Layout bricht nicht zusammen, es gibt keine leeren weißen Kästen.
