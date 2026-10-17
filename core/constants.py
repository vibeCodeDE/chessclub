"""Zentrale Konstanten für das Vereins-Setup und Onboarding."""

DEFAULT_FEE_CATEGORIES = [
    {
        "name": "Erwachsene (Vollzahler)",
        "beschreibung": "Regulärer Jahresbeitrag für aktive erwachsene Mitglieder",
        "betrag": 72.00,
    },
    {
        "name": "Jugendliche / Schüler / Studenten",
        "beschreibung": "Ermäßigter Beitrag für Kinder, Jugendliche unter 18 Jahren und Auszubildende",
        "betrag": 36.00,
    },
    {
        "name": "Senioren (ab 65 Jahre)",
        "beschreibung": "Ermäßigter Beitrag für Seniorinnen und Senioren",
        "betrag": 50.00,
    },
    {
        "name": "Passive Mitglieder / Förderer",
        "beschreibung": "Unterstützende Mitgliedschaft ohne aktive Spielberechtigung",
        "betrag": 30.00,
    },
]
