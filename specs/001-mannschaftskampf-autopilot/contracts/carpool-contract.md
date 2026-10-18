# Contract: Fahrgemeinschaften-Koordination (Carpool Logistics)

**Feature**: `001-mannschaftskampf-autopilot` | **Date**: 2026-10-17 | **Spec**: [spec.md](../spec.md)

---

## 1. Übersicht

Bei Auswärtsspielen erfasst das System automatisch, welche Spieler selbst fahren und wie viele Plätze sie anbieten, wer eine Mitfahrgelegenheit sucht und wer eigenständig anreist. Der Mannschaftsführer sieht die Auslastung in einem kompakten Dashboard-Widget (FR-009, US 5).

---

## 2. Service-Funktion: `get_carpool_summary` (`teams/services.py`)

Reine Funktion ohne HTTP-Kontext.

### Signatur
```python
def get_carpool_summary(match: LeagueMatch) -> dict:
    """Aggregiert Fahrgemeinschafts-Status und Platzkapazitäten für ein Ligaspiel."""
```

### Rückgabeformat (Dictionary)
```python
{
    "auswaertsspiel": True,
    "gesamt_zusagen": 8,
    "benoetigte_plaetze": 3,
    "angebotene_plaetze": 6,
    "differenz_plaetze": 3,  # positiv = Puffer, negativ = Plätzmangel!
    "status_ampel": "gruen", # "gruen" (Puffer >= 0) | "rot" (Mangel) | "grau" (Heimspiel)
    "fahrer": [
        {
            "name": "Dr. Michael Weber",
            "telefon": "+491701122334",
            "freie_plaetze": 3,
            "treffpunkt_notiz": "Treffpunkt 08:30 Uhr P+R West",
        },
        {
            "name": "Thomas Wagner",
            "telefon": "+491715566778",
            "freie_plaetze": 3,
            "treffpunkt_notiz": "Fahre direkt ab Südstadt",
        }
    ],
    "mitfahrer_gesuche": [
        {"name": "Julian Meier", "telefon": "+491799988771"},
        {"name": "Lisa Becker", "telefon": "+491763322110"},
        {"name": "Maximilian Graf", "telefon": "+491512233445"}
    ],
    "selbst_anreise": [
        {"name": "Klaus Sommer", "telefon": "+491709876543"}
    ],
    "offene_angaben": 2
}
```

---

## 3. UI-Komponente & Ansicht

- Eingebettet in `teams/templates/teams/match_detail.html`:
  - Erscheint automatisch bei Spielen mit `heimspiel=False`.
  - Zeigt Status-Badge: `[Fahrgemeinschaften: 6 Plätze für 3 Suchende bereit]` (Grün) bzw. `[Achtung: Es fehlen 2 Plätze!]` (Rot).
  - Akkordeon-Ansicht mit Fahrern, Telefonnummern und Treffpunkten für schnelle Abstimmung.
