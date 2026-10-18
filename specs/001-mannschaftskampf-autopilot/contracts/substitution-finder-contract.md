# Contract: Ersatzspieler-Ermittlung & Anfrage (Substitution Finder)

**Feature**: `001-mannschaftskampf-autopilot` | **Date**: 2026-10-17 | **Spec**: [spec.md](../spec.md)

---

## 1. Übersicht

Ermöglicht dem Mannschaftsführer die sofortige, regelkonforme Ermittlung von Ersatzkandidaten aus nachrangigen Mannschaften nach Absage eines Stammspielers, inklusive Festspielprüfung und 1-Klick-Anfrage (FR-005, FR-006, FR-007).

---

## 2. Service-Funktion: `get_eligible_substitutes` (`teams/services.py`)

Reine Funktion ohne HTTP-Kontext.

### Signatur
```python
def get_eligible_substitutes(match: LeagueMatch, board_number: int) -> list[dict]:
    """Ermittelt berechtigte Ersatzspieler aus unteren Mannschaften für ein Brett.
    
    Returns:
        Liste von Dictionaries, sortiert nach Mannschaftsebene und Rangziffer.
    """
```

### Rückgabeformat (List of Dicts)
```python
[
    {
        "member_id": 42,
        "name": "Anton Müller",
        "email": "a.mueller@example.com",
        "telefon": "+491701234567",
        "heimat_team_id": 2,
        "heimat_team_name": "2. Mannschaft",
        "rangnummer": 3,
        "bisherige_einsaetze_hoeher": 2,
        "festspiel_schwelle": 2,
        "festspiel_status": "festgespielt",  # "gruen" | "warnung_letzter" | "festgespielt"
        "festspiel_warnung": "Achtung: Wenn Müller heute in der 1. spielt, ist er dort festgespielt!",
        "terminkollision": False,
        "kollision_text": None,
        "vorauswahl": True,  # Standardmäßig True, außer bei Terminkollision
    },
    {
        "member_id": 55,
        "name": "Bernd Schmidt",
        "email": "b.schmidt@example.com",
        "telefon": "+491719876543",
        "heimat_team_id": 2,
        "heimat_team_name": "2. Mannschaft",
        "rangnummer": 4,
        "bisherige_einsaetze_hoeher": 1,
        "festspiel_schwelle": 2,
        "festspiel_status": "warnung_letzter",
        "festspiel_warnung": "Vorsicht: Letzter freier Einsatz vor dem Festspielen!",
        "terminkollision": False,
        "kollision_text": None,
        "vorauswahl": True,
    },
    {
        "member_id": 78,
        "name": "Clara Schulz",
        "email": "c.schulz@example.com",
        "telefon": "+491724455667",
        "heimat_team_id": 3,
        "heimat_team_name": "3. Mannschaft",
        "rangnummer": 1,
        "bisherige_einsaetze_hoeher": 0,
        "festspiel_schwelle": 2,
        "festspiel_status": "gruen",
        "festspiel_warnung": None,
        "terminkollision": True,
        "kollision_text": "3. Mannschaft spielt zeitgleich gegen Schachfreunde Süd",
        "vorauswahl": False,  # Bei Terminkollision abgewählt
    }
]
```

---

## 3. UI-Workflow & Endpunkte

### `GET /spielbetrieb/spiele/<int:match_id>/ersatz/<int:brett>/`
Zeigt die Vorschlagsliste für das vakante Brett an.
- Rollenschutz: `@role_required(ADMIN_GROUP, KAPITAEN_GROUP)` (nur Kapitän des betroffenen Teams oder Admin).
- Rendert Ampel-Status (Grün / Gelb / Rot) und Vorauswahl-Checkboxen für alle Kandidaten.
- Zeigt Festspiel-Warnungen unübersehbar hervor.

### `POST /spielbetrieb/spiele/<int:match_id>/ersatz/<int:brett>/anfragen/`
Löst die Ersatzanfrage an die ausgewählten Kandidaten aus.

**Parameter**:
```text
candidate_ids: [42, 55]  (Liste der ausgewählten Member-IDs)
hinweis: "Spielbeginn 10:00 Uhr im Vereinsheim" (optional)
```

**Ablauf**:
1. Erstellt `SubRequest` für das Spiel und Brett.
2. Erzeugt für jeden gewählten Kandidaten ein `SubRequestCandidate` mit sicherem Token (`secrets.token_urlsafe(32)`).
3. Versendet automatisch E-Mails an alle Kandidaten mit E-Mail-Adresse.
4. Generiert für den Mannschaftsführer vorbereitete Click-to-Chat-Links (`wa.me`) für schnellen WhatsApp-Versand:
   ```text
   https://wa.me/?text=Hallo!%20F%C3%BCr%20unsere%201.%20Mannschaft%20wird%20ein%20Ersatzspieler%20an%20Brett%204%20gesucht.%20Wer%20zuerst%20klickt%2C%20hat%20den%20Platz%3A%20https%3A%2F%2Fverein.de%2Fspielbetrieb%2Fersatz%2F<token>%2F
   ```
5. Schreibt AuditLog-Eintrag.

**Antwort (JSON / UI)**:
```json
{
  "success": true,
  "sub_request_id": 12,
  "angefragte_spieler_anzahl": 2,
  "whatsapp_share_url": "https://wa.me/?text=...",
  "message": "Ersatzanfrage an 2 Spieler per E-Mail versendet. WhatsApp-Vorlage bereit."
}
```
