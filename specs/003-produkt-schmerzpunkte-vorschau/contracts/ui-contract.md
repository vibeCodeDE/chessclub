# UI & Schnittstellen-Vertrag: Schmerzpunkte, Lösungen & Vorschau

**Feature**: `003-produkt-schmerzpunkte-vorschau`  
**Date**: 2026-10-17  
**Status**: Specified  

---

## 1. Template-Kontext-Vertrag

Die View `core/views.py:produkt_seite` stellt dem Template `core/templates/core/produkt.html` folgende Variable im Rendering-Kontext bereit:

```python
kontext = {
    # Bestehende Variablen
    "product_name": settings.PRODUCT_NAME,
    "product_contact": settings.PRODUCT_CONTACT,
    "preisstufen": produkt.PREISSTUFEN,
    "preishinweis": produkt.PREISHINWEIS,
    "funktionen": produkt.FUNKTIONEN,
    "datenschutz_punkte": produkt.DATENSCHUTZ_PUNKTE,
    "schritte": produkt.SCHRITTE,
    "faq": produkt.FAQ,
    
    # NEU: Strukturierte Rollen, Schmerzpunkte und Vorschau-Daten
    "rollen_schmerzpunkte": produkt.ROLLEN_SCHMERZPUNKTE,
}
```

---

## 2. DOM-Struktur & CSS-Klassenvertrag

### 2.1 Sektions-Container

```html
<section class="lp-section lp-pains-showcase" id="loesungen" aria-labelledby="pains-heading">
  <div class="lp-wrap">
    <div class="lp-head">
      <span class="lp-eyebrow dark">Schmerzpunkte &amp; Lösungen</span>
      <h2 class="lp-h2" id="pains-heading">Vereinsarbeit ohne Zettelwirtschaft und Frust</h2>
      <p class="lp-muted">Wählen Sie Ihre Rolle im Verein und sehen Sie, wie Schachverwaltung Ihren Alltag erleichtert.</p>
    </div>

    <!-- Interaktiver Rollen-Umschalter -->
    <div class="lp-role-selector" role="tablist" aria-label="Vereinsrollen">
      <!-- Generiert pro Rolle: Hidden Radio + Label -->
      <input type="radio" name="lp_role" id="role-vorstand" class="lp-role-radio" checked>
      <label for="role-vorstand" class="lp-role-tab" role="tab" aria-controls="panel-vorstand" tabindex="0">
        <!-- SVG Icon + Kurztitel -->
      </label>
      ...
    </div>

    <!-- Rollen-Panels -->
    <div class="lp-role-panels">
      <!-- Pro Rolle: Panel mit Schmerzpunkten und interaktiver Vorschau -->
      <div id="panel-vorstand" class="lp-role-panel" role="tabpanel" aria-labelledby="role-vorstand">
        <div class="lp-panel-grid">
          <!-- Linke Spalte: Schmerzpunkte & Lösungen -->
          <div class="lp-panel-text">...</div>
          <!-- Rechte Spalte: Interaktives Mockup -->
          <div class="lp-panel-preview">...</div>
        </div>
      </div>
      ...
    </div>
  </div>
</section>
```

---

## 3. Interaktions- & Zustandskontrakt

### 3.1 Rollenwechsel via CSS-Selektor
```css
/* Radio-Inputs bleiben unsichtbar, steuern aber den Zustand */
.lp-role-radio {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

/* Panel-Sichtbarkeit über den :checked-Zustand */
#role-vorstand:checked ~ .lp-role-panels #panel-vorstand,
#role-kassenwart:checked ~ .lp-role-panels #panel-kassenwart,
#role-spielleiter:checked ~ .lp-role-panels #panel-spielleiter,
#role-kapitaen:checked ~ .lp-role-panels #panel-kapitaen,
#role-mitglieder:checked ~ .lp-role-panels #panel-mitglieder {
  display: block;
}

/* Aktiver Tab-Zustand */
#role-vorstand:checked ~ .lp-role-selector label[for="role-vorstand"],
#role-kassenwart:checked ~ .lp-role-selector label[for="role-kassenwart"],
#role-spielleiter:checked ~ .lp-role-selector label[for="role-spielleiter"],
#role-kapitaen:checked ~ .lp-role-selector label[for="role-kapitaen"],
#role-mitglieder:checked ~ .lp-role-selector label[for="role-mitglieder"] {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
```

### 3.2 Interaktives Mockup (Sub-Interaktion)
Innerhalb jedes Panels gibt es Radio- oder Schaltelemente, um typische Arbeitsabläufe direkt zu demonstrieren:
- **Kassenwart**: Umschalten zwischen *Offene Posten (1.240 €)*, *SEPA-XML (Vorschau)* und *Mahnstufe 1*.
- **Spielleiter**: Umschalten zwischen *Runde 1 (Paarungen)* und *Runde 2 (Schweizer System)*.
- **Mannschaftsführer**: Umschalten zwischen *Standardaufstellung* und *Ersatzspielerprüfung*.
- **Vorstand**: Umschalten zwischen *Audit-Log* und *1-Klick DSGVO-Auskunft*.

---

## 4. Barrierefreiheit (WCAG 2.1 AA)

- Jeder Tab hat `tabindex="0"`, sodass er mit der Tastatur erreichbar ist.
- `role="tab"` und `role="tabpanel"` definieren die semantische Verknüpfung.
- Bei Tastaturfokus wird ein sichtbarer Fokusring (`outline: 2px solid var(--primary); outline-offset: 2px`) angezeigt.
- Textkontrast für alle Informationselemente liegt über 4,5:1.
- Wenn CSS oder Skripte deaktiviert sind, bleiben alle Texte im DOM sequenziell lesbar (Progressive Enhancement).

---

## 5. Viewport- & Overflow-Garantie

- **360 px**: Die `.lp-role-selector` Leiste nutzt `overflow-x: auto` mit `scrollbar-width: none` und Flexbox (`display: flex; gap: 0.5rem; flex-wrap: nowrap`). Kein horizontaler Overflow der Gesamtseite (`document.body.scrollWidth <= window.innerWidth`).
- **1280 px**: 2-spaltiges Grid (`grid-template-columns: 1.1fr 0.9fr; gap: 2.5rem;`).
