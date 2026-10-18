# Contract: Mannschaftsmeldelisten-Import (Team Roster)

**Feature**: `001-mannschaftskampf-autopilot` | **Date**: 2026-10-17 | **Spec**: [spec.md](../spec.md)

---

## 1. Übersicht

Der Roster-Import ermöglicht dem Verein oder Mannschaftsführer zu Saisonbeginn das einmalige Hochladen der offiziellen Rang- und Meldelisten für alle Mannschaften (FR-001, US 2).

- URL (Admin / Kapitän): `POST /spielbetrieb/meldeliste/import/`
- Unterstützte Formate: CSV (UTF-8, Trennzeichen Komma oder Semikolon) und XLSX.

---

## 2. Spaltenformat (CSV / Excel)

| Spaltenname | Pflicht | Typ | Beispiel | Beschreibung |
|---|---|---|---|---|
| `mannschaft` | Ja | String | `1. Mannschaft` oder `1` | Name oder Ziffer der Mannschaft |
| `rang` | Ja | Integer | `1` | Fortlaufende Rangnummer (1..30) |
| `brett` | Nein | Integer (1..8) | `4` | Stammbrettnummer (leer/0 für Ersatzspieler) |
| `mitgliedsnummer` | Optional* | Integer | `1042` | Vereins-Mitgliedsnummer zur exakten Zuordnung |
| `nachname` | Optional* | String | `Mustermann` | Nachname zur Zuordnung falls keine Nummer |
| `vorname` | Optional* | String | `Erika` | Vorname zur Zuordnung falls keine Nummer |
| `pkz` | Nein | String | `12345` | DSB-Personenkennziffer (optionaler Abgleich) |

*\*Entweder `mitgliedsnummer` ODER (`nachname` und `vorname`) muss angegeben sein.*

---

## 3. Validierungsregeln & Dry-Run

### Ablauf
1. **Schritt 1: Upload mit `dry_run=true`**:
   - Die Datei wird eingelesen und zeilenweise geprüft.
   - Mitglieder werden im System gesucht (exakter Match nach `mitgliedsnummer`, Fallback `nachname` + `vorname` case-insensitive).
   - Eindeutigkeit der Rangnummer je Mannschaft wird geprüft.
   - Eindeutigkeit des Stammbretts je Mannschaft wird geprüft (maximal 1 Spieler pro Stammbrett 1..8).
2. **Schritt 2: Ergebnisbericht (JSON oder HTML-Vorschau)**:
   - Zeigt gefundene Mannschaften, zugeordnete Stammspieler, Ersatzspieler und erkannte Konflikte.
3. **Schritt 3: Bestätigung mit `dry_run=false`**:
   - Bei fehlerfreier Prüfung oder manueller Freigabe werden `TeamRoster` und `RosterEntry` in einer Datenbanktransaktion persistiert.
   - Bestehende aktive Roster der Saison werden archiviert (`ist_aktiv = False`).
   - Audit-Log-Eintrag wird geschrieben.

---

## 4. API-Schemas

### Request (`multipart/form-data`)
```text
datei: [Upload-Datei]
saison: "2026/2027"
dry_run: true | false
```

### Response (JSON bei Dry-Run)
```json
{
  "dry_run": true,
  "gueltig": true,
  "teams_erkannt": [
    {
      "team_name": "1. Mannschaft",
      "stammspieler_anzahl": 8,
      "ersatzspieler_anzahl": 6
    },
    {
      "team_name": "2. Mannschaft",
      "stammspieler_anzahl": 8,
      "ersatzspieler_anzahl": 4
    }
  ],
  "warnungen": [
    {
      "zeile": 14,
      "nachricht": "Spieler 'Müller, Anton' wurde anhand von Vor- und Nachname zugeordnet (Mitgliedsnummer fehlte)."
    }
  ],
  "fehler": []
}
```

### Fehlerfälle (`gueltig: false`)
- `DOPPELTE_RANGNUMMER`: Mehrere Spieler mit identischer Rangnummer in derselben Mannschaft.
- `MITGLIED_NICHT_GEFUNDEN`: Ein Spieler konnte keinem aktiven Vereinsmitglied zugeordnet werden.
- `DOPPELTES_STAMMBRETT`: Zwei Spieler wurden auf das gleiche Stammbrett gesetzt.
- `BRETT_AUSSERHALB_LIMIT`: Stammbrett ist größer als die für die Mannschaft konfigurierte Brettanzahl.
