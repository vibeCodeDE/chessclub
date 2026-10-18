# Contract: Saison-Verwaltungs-Endpunkte (HTTP API & Views)

**Feature**: `004-saison-verwaltung` | **Date**: 2026-10-17 | **Spec**: [spec.md](../spec.md)

---

## 1. Übersicht der Endpunkte

Alle nachfolgenden Verwaltungs-Endpunkte sind rollengeschützt und verlangen die Mitgliedschaft in der Administrator-/Vorstandsgruppe (`@role_required(ADMIN_GROUP)`). Jeder Zugriff durch nicht autorisierte Benutzer (Gäste, Mitglieder, Mannschaftsführer) antwortet mit HTTP 403 Forbidden.

| URL-Pfad | HTTP-Methode | View-Funktion | Beschreibung |
|---|---|---|---|
| `/saison/` | `GET` | `season_list` | Tabellarische Übersicht aller Saisons, Anzeige der aktiven Saison, Team- und Spieleanzahl |
| `/saison/neu/` | `GET`, `POST` | `season_create` | Neuanlage einer Saison mit Vorauswahl des nächsten logischen Zeitfensters |
| `/saison/<int:pk>/bearbeiten/` | `GET`, `POST` | `season_edit` | Bearbeiten von Name, Notizen und Datumsbereich einer bestehenden Saison |
| `/saison/<int:pk>/aktivieren/` | `POST` | `season_activate` | Setzt die angegebene Saison atomar als aktive Hauptsaison |
| `/saison/<int:pk>/abschliessen/` | `POST` | `season_archive` | Archiviert eine Saison (Schreibschutz); prüft vorab offene Spielbegegnungen |
| `/saison/<int:pk>/loeschen/` | `POST` | `season_delete` | Löscht eine leere Saison; blockiert bei vorhandenen Teams/Spielen |
| `/saison/<int:pk>/uebernahme/` | `GET`, `POST` | `season_rollover` | Assistent zur Übernahme von Mannschaften aus der Vorsaison |

---

## 2. Endpunkt-Spezifikationen

### 2.1 GET `/saison/` (Übersicht)
- **Rolle**: Vorstand / Admin (`ADMIN_GROUP`)
- **Query-Parameter**: Keine.
- **Template**: `teams/season_list.html`
- **Kontext**:
  - `saisons`: QuerySet aller Saisons, geordnet nach `-startdatum`.
  - `aktive_saison`: Die aktuell gesetzte Hauptsaison.
- **HTTP Status**: `200 OK` (Admin), `403 Forbidden` (Andere).

### 2.2 GET & POST `/saison/neu/` (Neuanlage)
- **Rolle**: Vorstand / Admin
- **GET Request**: Rendert Formular mit Standard-Vorbelegungen:
  - `name`: z. B. `2026/2027`
  - `startdatum`: `01.08.2026`
  - `enddatum`: `31.07.2027`
- **POST Payload**:
  - `name` (String, Pflicht, max. 50 Zeichen)
  - `startdatum` (Datum `YYYY-MM-DD`, Pflicht)
  - `enddatum` (Datum `YYYY-MM-DD`, Pflicht, > startdatum)
  - `notizen` (String, optional)
  - `als_aktiv_setzen` (Checkbox, optional)
- **Response**:
  - Bei Erfolg: HTTP 302 Redirect auf `/saison/` mit Erfolgsmeldung.
  - Bei Validierungsfehler: HTTP 200 mit Fehlermeldungen am Formularfeld.

### 2.3 POST `/saison/<int:pk>/aktivieren/` (Hauptsaison wechseln)
- **Rolle**: Vorstand / Admin
- **Header**: CSRF-Token erforderlich.
- **Ablauf**: Ruft `teams.services.set_active_season(season, request.user)` auf.
- **Response**: HTTP 302 Redirect auf `/saison/` mit Success-Message.
- **Audit-Log**: Erzeugt Eintrag mit `aktion="Saison aktiviert"`, `neu_wert=season.name`.

### 2.4 POST `/saison/<int:pk>/abschliessen/` (Saison archivieren)
- **Rolle**: Vorstand / Admin
- **POST Payload**:
  - `bestaetigen` (Checkbox/Flag, Pflicht falls noch ungespielte Partien existieren)
- **Response**:
  - HTTP 302 Redirect auf `/saison/` mit Erfolgsmeldung.
  - Falls offene Spiele existieren und nicht bestätigt wurde: HTTP 400 mit Liste ungespielter Begegnungen.
- **Audit-Log**: Erzeugt Eintrag `aktion="Saison archiviert"`.

### 2.5 GET & POST `/saison/<int:pk>/uebernahme/` (Rollover-Assistent)
- **Rolle**: Vorstand / Admin
- **Ziel**: Ziel-Saison (angegeben über `<pk>`).
- **GET Request**:
  - Listet alle Mannschaften der chronologischen Vorgänger-Saison auf.
  - Vorbelegte Eingabefelder je Team: Checkbox `uebernehmen`, Textfeld `liga`, Select `kapitaen`, SmallInt `brettanzahl`.
- **POST Payload**:
  ```json
  {
    "teams": [
      {
        "source_team_id": 1,
        "uebernehmen": true,
        "liga": "Verbandsliga Nord",
        "brettanzahl": 8,
        "kapitaen_id": 42
      }
    ]
  }
  ```
- **Response**: HTTP 302 Redirect auf `/spielbetrieb/?saison=<pk>` mit Meldung „X Mannschaften erfolgreich in Saison 2026/2027 übernommen.“
