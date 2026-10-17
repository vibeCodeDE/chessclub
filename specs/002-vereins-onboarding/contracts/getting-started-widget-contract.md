# Interface Contract: Dashboard Getting-Started Widget

**Bereich**: Vorstandsdashboard (`core/views.py:_dashboard_vorstand`)  
**Template**: `templates/core/includes/onboarding_widget.html`  
**Berechtigung**: Nur sichtbar für Rolle `admin` (`ADMIN_GROUP`)  

---

## 1. Datenstruktur im Template-Kontext (`onboarding_widget`)

```python
{
    "sichtbar": bool,  # False, wenn checklist_ausgeblendet=True
    "gesamt_schritte": int,  # 5
    "erledigte_schritte": int,  # z. B. 4
    "fortschritt_prozent": int,  # z. B. 80
    "aufgaben": [
        {
            "id": "profil",
            "titel": "Vereinsprofil & Spiellokal hinterlegen",
            "erledigt": bool,
            "url": str,  # /verein/setup/profil/
        },
        {
            "id": "beitraege",
            "titel": "Beitragskategorien einrichten",
            "erledigt": bool,
            "url": str,  # /verein/setup/beitraege/
        },
        {
            "id": "mitglieder",
            "titel": "Mitglieder importieren oder anlegen",
            "erledigt": bool,
            "url": str,  # /mitglieder/neu/ bzw. /verein/setup/mitglieder-import/
        },
        {
            "id": "mannschaften",
            "titel": "Erste Mannschaft anlegen",
            "erledigt": bool,
            "url": str,  # /mannschaften/neu/
        },
        {
            "id": "funktionaere",
            "titel": "Vorstandskollegen oder Kapitäne einladen",
            "erledigt": bool,
            "url": str,  # /onboarding/schritt/5/
        },
    ],
}
```

---

## 2. Ausblend-Aktion (`/onboarding/checklist/ausblenden/`)

- **HTTP-Methode**: POST
- **Berechtigung**: `@role_required(ADMIN_GROUP)`
- **Verhalten**:
  - Setzt `OnboardingProgress.get_solo().checklist_ausgeblendet = True`.
  - Schreibt `AuditLog`-Eintrag.
  - Antwortet mit Redirect auf das Dashboard (`core:dashboard`).
  - Bei AJAX-Aufruf (`X-Requested-With: XMLHttpRequest`): Antwortet mit `{ "erfolg": true }`.
