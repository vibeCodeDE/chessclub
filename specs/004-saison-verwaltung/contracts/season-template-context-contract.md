# Contract: Template-Kontext & Saison-Auswahl (UI Integration)

**Feature**: `004-saison-verwaltung` | **Date**: 2026-10-17 | **Spec**: [spec.md](../spec.md)

---

## 1. Django Context-Processor: `season_context`

### Registrierung
In `config/settings.py` unter `TEMPLATES[0]["OPTIONS"]["context_processors"]`:
`"teams.context_processors.season_context"`

### Signatur & Bereitgestellte Variablen
```python
def season_context(request) -> dict:
    """Stellt Saisondaten für Kopfzeile, Navigation und Filter bereit."""
    return {
        "aktive_saison": aktive_saison,       # Season-Objekt mit ist_aktiv=True
        "alle_saisons": alle_saisons,         # QuerySet aller Saisons (-startdatum)
        "gewaehlte_saison": gewaehlte_saison, # Aus request.GET.get('saison') oder aktive_saison
    }
```

---

## 2. UI-Filterkomponente: `includes/season_filter.html`

Integrierbar in Spielbetrieb- und Turnier-Übersichtsseiten:

```html
<form method="get" class="season-filter-form" role="search" aria-label="Saison auswählen">
  <label for="saison-select" class="sr-only">Saison filtern:</label>
  <div class="relative inline-flex items-center">
    <select id="saison-select" name="saison" onchange="this.form.submit()" class="form-select ...">
      {% for s in alle_saisons %}
        <option value="{{ s.id }}" {% if s.id == gewaehlte_saison.id %}selected{% endif %}>
          Saison {{ s.name }}{% if s.ist_aktiv %} (Aktuell){% elif s.ist_archiviert %} (Archiv){% endif %}
        </option>
      {% endfor %}
    </select>
  </div>
</form>
```

### Barrierefreiheit (WCAG 2.1 AA)
- Explizites Formular-Label (oder `<label class="sr-only">`).
- Sichtbarer Tastaturfokus (`:focus-visible`).
- Klare Textbeschriftung inkl. Statusindikator `(Aktuell)` / `(Archiv)`.
- Responsive Anpassung ab 360 px Breite ohne Ausbrechen aus dem Viewport.
