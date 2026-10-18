# Contract: Saison-Fachlogik (`teams/services.py`)

**Feature**: `004-saison-verwaltung` | **Date**: 2026-10-17 | **Spec**: [spec.md](../spec.md)

---

## 1. Übersicht & Prinzipien

Alle geschäftsrelevanten Operationen werden als reine Python-Funktionen in `teams/services.py` ohne Abhängigkeit vom Django HTTP-Request ausgeführt. Sie sind unabhängig testbar, garantieren atomare Datenbanktransaktionen und erzeugen revisionssichere Einträge im `AuditLog`.

---

## 2. Funktionsdefinitionen

### 2.1 `create_season`
```python
def create_season(
    *,
    name: str,
    startdatum: datetime.date,
    enddatum: datetime.date,
    notizen: str = "",
    als_aktiv_setzen: bool = False,
    user: Optional[AbstractBaseUser] = None,
) -> Season:
    """Erstellt eine neue Saison und setzt sie optional als aktive Hauptsaison.
    
    Validiert:
    - startdatum < enddatum
    - Eindeutigkeit des Namens
    
    Protokolliert:
    - AuditLog-Eintrag "Saison angelegt" mit Name und Zeitspanne.
    """
```

### 2.2 `set_active_season`
```python
def set_active_season(
    season: Season,
    user: Optional[AbstractBaseUser] = None,
) -> Season:
    """Setzt die übergebene Saison atomar als einzige aktive Hauptsaison.
    
    Ablauf:
    with transaction.atomic():
        Season.objects.exclude(pk=season.pk).filter(ist_aktiv=True).update(ist_aktiv=False)
        season.ist_aktiv = True
        if season.status == Season.Status.VORBEREITUNG:
            season.status = Season.Status.AKTIV
        season.save(update_fields=["ist_aktiv", "status", "aktualisiert_am"])
        
    Protokolliert:
    - AuditLog "Saison aktiviert" (alter Wert -> neuer Wert).
    """
```

### 2.3 `archive_season`
```python
def archive_season(
    season: Season,
    *,
    force: bool = False,
    user: Optional[AbstractBaseUser] = None,
) -> tuple[bool, list[str]]:
    """Versetzt eine Saison in den Status ARCHIVIERT und aktiviert den Schreibschutz.
    
    Prüfungen:
    - Ermittelt alle LeagueMatch-Einträge der Saison, die noch nicht im Status GESPIELT oder ABGESAGT sind.
    - Wenn ungespielte Matches existieren und force=False ist: Rückgabe (False, [Warnhinweise]).
    - Wenn force=True oder keine offenen Spiele:
        season.status = Season.Status.ARCHIVIERT
        season.save()
        AuditLog "Saison archiviert"
        Rückgabe (True, []).
    """
```

### 2.4 `rollover_teams`
```python
def rollover_teams(
    *,
    source_season: Season,
    target_season: Season,
    teams_payload: list[dict],
    user: Optional[AbstractBaseUser] = None,
) -> list[Team]:
    """Übernimmt ausgewählte Mannschaften aus source_season in target_season.
    
    teams_payload enthält pro Mannschaft:
    {
        "source_team_id": int,
        "uebernehmen": bool,
        "name": str (optional, Default: Quellname),
        "liga": str,
        "altersklasse": str,
        "brettanzahl": int,
        "kapitaen_id": Optional[int],
    }
    
    Ablauf:
    with transaction.atomic():
        - Für jedes aktivierte Team wird ein neues Team(saison=target_season, ...) erzeugt.
        - Neues ical_token wird generiert.
        - Vorhandene Spiele der Vorsaison werden NICHT kopiert.
        - AuditLog "Mannschaftsübernahme durchgeführt" mit Liste der neuen Teams.
    """
```

### 2.5 `validate_match_season_bounds`
```python
def validate_match_season_bounds(match: LeagueMatch) -> None:
    """Validiert, dass match.datum innerhalb von match.team.saison liegt.
    
    Hebt ValidationError("Das Spieldatum liegt außerhalb der Saison ...") aus,
    falls match.datum < saison.startdatum oder match.datum > saison.enddatum.
    """
```

### 2.6 `check_match_edit_allowed`
```python
def check_match_edit_allowed(match: LeagueMatch) -> None:
    """Prüft Schreibberechtigung auf ein Ligaspiel.
    
    Hebt PermissionDenied aus, wenn match.team.saison.ist_archiviert ist.
    """
```
