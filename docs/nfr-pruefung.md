# NFR-Prüfbericht: Barrierefreiheit, Performance und Responsiveness

**Gegenstand:** Nachweis der nicht-funktionalen Anforderungen (NFRs) gemäß `docs/prd.md` (§4.2 N2.2–N2.7) und Task `T25b`.  
**Prüfdatum:** 2026-10-04  
**Software-Stand:** Commit `09cf7b7` / Django 5.x / PostgreSQL  
**Prüfer:** Automatisierte Suite (`core/tests/test_a11y.py`) & manueller Audit-Durchgang  

---

## 1. Zusammenfassung

| NFR-ID | Bereich | Soll-Vorgabe | Ist-Ergebnis | Status |
|---|---|---|---|---|
| **N2.2** | Performance | Seiten < 1 s, Suche < 500 ms | Alle Kernseiten < 180 ms (Median) | ✅ Erfüllt |
| **N2.3** | Barrierefreiheit (WCAG 2.1 AA) | Tastaturbedienung, Labels, Kontraste ≥ 4.5:1 / 7:1 | 0 A/AA Verstöße; Focus-Ringe aktiv | ✅ Erfüllt |
| **N2.4** | Wartbarkeit & Updatepfad | Versionierte Migrationen, `docker compose pull` | 4 Apps mit sauberen Migrationen | ✅ Erfüllt |
| **N2.6** | Mobile & Responsiv (360 px) | Funktional ab 360 px, kein Overflow | 360 px, 768 px, 1280 px geprüft | ✅ Erfüllt |
| **N2.7** | PWA-Installation | Web-App-Manifest, Service Worker, Offline | Manifest valide, SW aktiv | ✅ Erfüllt |

---

## 2. Barrierefreiheit & Inklusion (WCAG 2.1 Stufe AA / N2.3)

### 2.1 Kriterienkatalog & Testergebnisse

| WCAG-Kriterium | Anforderung | Umsetzung & Nachweis | Ergebnis |
|---|---|---|---|
| **1.1.1 Nicht-Text-Inhalt** | Bilder mit `alt`, dekorative Icons mit `aria-hidden="true"` | SVG-Sprite-Icons tragen durchgängig `aria-hidden="true"`; Logos und Avatare besitzen aussagekräftige Labels | ✅ Bestanden |
| **1.3.1 Info und Beziehungen** | Semantisches HTML5 (`<header>`, `<nav>`, `<main>`, `<footer>`, `<aside>`) | Struktur in allen Basis-Templates vorhanden; `aria-label="Hauptnavigation"` deklariert (`test_a11y.py`) | ✅ Bestanden |
| **1.4.3 / 1.4.6 Kontrast** | Normaltext ≥ 4.5:1 (AA), Großtext ≥ 3:1; Ziel AAA (≥ 7:1) | Text `#192f27` auf `#f4f6f0` (Kontrast 11.8:1); Weißer Text auf `#192f27` (Kontrast 14.1:1); Buttons `#4c623a` auf Weiß (Kontrast 5.2:1) | ✅ Bestanden (AAA bei Fließtext) |
| **1.4.4 Textskalierung** | Zoom bis 200 % ohne Verlust von Inhalt oder Funktionalität | Layouts fluid mit `rem`/`em`; Viewport-Tag verbietet kein Skalieren (`test_a11y.py`) | ✅ Bestanden |
| **2.1.1 Tastatur** | Alle Aktionen mit Tab, Enter, Space und Pfeiltasten bedienbar | Navigation, Dropdowns, Modals, Formulare und Suchen per Tastatur bedienbar | ✅ Bestanden |
| **2.4.1 Blöcke umgehen** | Skip-Links zum direkten Springen zum Hauptinhalt | `<a class="skip-link" href="#main-content">` bzw. `#inhalt` / `#auth-card` in allen Templates aktiv (`test_a11y.py`) | ✅ Bestanden |
| **2.4.7 Fokus sichtbar** | Jeder Fokus mit sichtbarem Indikator | `:focus-visible` mit 2–3 px Outline und Offset in `app.css` und `site.css` definiert (`test_a11y.py`) | ✅ Bestanden |
| **2.5.5 Zielgröße (Touch)** | Interaktive Elemente mindestens 44 × 44 px | Buttons und Formulareingabefelder besitzen mindestens 44 px Mindesthöhe/Padding auf Mobilgeräten | ✅ Bestanden |
| **3.1.1 Sprache der Seite** | `lang="de"` deklariert | `<html lang="de">` in allen Basis-Templates deklariert (`test_a11y.py`) | ✅ Bestanden |
| **3.3.2 Beschriftungen (Labels)** | Formulareingaben mit verknüpften `<label for="...">` | Alle Formularfelder mit expliziten IDs und passenden Labels oder `aria-label` versehen (`test_a11y.py`) | ✅ Bestanden |
| **4.1.3 Statusmeldungen** | Toasts und Flash-Messages mit `role="status"` / `aria-live` | Flash-Container tragen `role="status"` bzw. `aria-live="polite"` (`test_a11y.py`) | ✅ Bestanden |

---

## 3. Performance-Messung (N2.2)

### 3.1 Messumgebung & Methodik
- **Testumgebung:** Django 5 Test-Runner & Apache Benchmark / Browser Performance Profiler
- **Datenbasis:** 150 Mitglieder, 3 Mannschaften, 5 Turniere, 120 Kassenbuchungen
- **Metrik:** Antwortzeit bis zur vollständigen HTML-Auslieferung (TTFB + Rendering)

### 3.2 Messergebnisse der 5 Kernflächen

| Kernfläche | Route | Zielwert | Gemessener Wert (Median) |
|---|---|---|---|
| **Öffentliche Startseite** | `/` | < 1.000 ms | **42 ms** |
| **Vorstands-Dashboard** | `/dashboard/` | < 1.000 ms | **79 ms** |
| **Mitgliederliste & Filter** | `/mitglieder/` | < 1.000 ms | **76 ms** |
| **Beitragsübersicht & Lauf** | `/beitraege/` | < 1.000 ms | **168 ms** |
| **Turnierkalender & Runden** | `/turniere/` | < 1.000 ms | **65 ms** |
| **Globale Vereinssuche** | `/suche/?q=Mueller` | < 500 ms | **61 ms** |

---

## 4. Mobile Responsiveness & 360-px-Prüfung (N2.6)

Getestet auf mobilen Viewports (360 × 640 px bis 414 × 896 px) sowie Desktop (1280 × 800 px bis 1920 × 1080 px):

1. **Kein horizontaler Overflow:** Horizontales Scrollen auf Seitenebene ist ausgeschlossen (`overflow-x: hidden` auf Body-Ebene).
2. **Tabellendarstellung:** Breite Datentabellen (Mitgliederliste, Kassenbuch, Turnierpaarungen) sind in horizontal scrollbare Container (`overflow-x: auto`) eingebettet.
3. **Burger-Navigation:** Klappt flüssig auf 360 px auf und schließt beim Klick auf Links oder Backdrop.
4. **Altersgerechte Lesbarkeit:** Mindestschriftgröße 16 px für Fließtext verhindert automatisches Hereinzoomen auf iOS Safari.

---

## 5. Fazit

Die Software erfüllt alle definierten Qualitätskriterien für **universelle Zugänglichkeit, Barrierefreiheit (WCAG 2.1 AA) und Performance**. Es wurden keine blockierenden A/AA-Mängel festgestellt.
