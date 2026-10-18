# Research & Architecture Decisions: Saisonverwaltung für den Vereinsvorstand

**Feature**: `004-saison-verwaltung` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

---

## 1. Modul- und Domain-Platzierung des `Season`-Modells

### Kontext & Anforderung
Die Saisonverwaltung dient dem Vorstand zur Festlegung von Spielzeiten (z. B. „2026/2027“). Saisons steuern primär den Spielbetrieb (`teams`: Mannschaften, Ligaspiele, Aufstellungen), aber auch Vereinsturniere (`tournaments`: Vereinsmeisterschaften, Pokale).

### Entscheidung
Das Modell `Season` wird in `teams.models` implementiert und über `teams.services` gesteuert.
- **Begründung**:
  - `teams` ist die primäre Fachdomäne für den sportlichen Spielbetrieb und Wettkampfzyklen des Vereins.
  - Mannschaften (`Team`) und Ligaspiele (`LeagueMatch`) sind zwingend saisongebunden.
  - Die Verknüpfung in `tournaments.models.Tournament` erfolgt über einen optionalen ForeignKey (`saison = models.ForeignKey("teams.Season", on_delete=models.SET_NULL, null=True, blank=True)`), der dank Djangos String-basierter Model-Referenzierung (`"teams.Season"`) zirkuläre Importe vollständig vermeidet.
  - Die zentrale Administration und das Saison-Umschalten werden über klare, rollengeschützte Function-Based Views (`teams/views.py`) und reine Fachfunktionen (`teams/services.py`) abgewickelt.

### Verworfene Alternativen
- *Platzierung in `core.models`*: Zwar enthält `core` bereits vereinsweite Singletons (`ClubProfile`, `ModuleSettings`), jedoch sind Saisons keine statischen Einstellungen, sondern dynamische sportliche Entitäten mit Spielplänen, Mannschaftsübernahmen und Turnieren. Eine Auslagerung in `core` würde den Fachbezug zu `teams` zersplittern.
- *Reines Textfeld `saison = CharField(...)` an jedem Modell*: Führt zu Tippfehlern (z. B. „2026/27“ vs. „2026/2027“), verunmöglicht zentrale Statussteuerung (Archivierung, aktive Saison) und verhindert relationale Konsistenzprüfungen.

---

## 2. Verwaltung der „Aktiven Saison“ & Globaler Template-Kontext

### Kontext & Anforderung
Genau eine Saison ist das aktuelle Hauptspieljahr (z. B. `2026/2027`). Sie steuert die Standardauswahl im Dashboard, in Mannschaftslisten und im Spielbetrieb. Benutzer müssen jedoch jederzeit vergangene oder künftige Saisons ansehen können, ohne die globale Hauptsaison zu verändern.

### Entscheidung
- **Datenbankebene (`ist_aktiv`)**:
  - `Season.ist_aktiv = models.BooleanField("Aktive Hauptsaison", default=False)`.
  - In `teams.services.set_active_season(season, user)` wird die Umschaltung transaktionssicher (`transaction.atomic`) durchgeführt:
    1. Alle Saisons werden auf `ist_aktiv=False` gesetzt.
    2. Die gewählte Saison wird auf `ist_aktiv=True` gesetzt und im `AuditLog` protokolliert.
  - Singleton-Zugriffsmethode `Season.get_aktive_saison()`: Liefert die aktive Saison oder (als Ausfallsicherung) die chronologisch jüngste Saison.
- **Template- & Request-Ebene**:
  - Ein leichtgewichtiger Django Context-Processor `teams.context_processors.season_context` stellt in allen HTML-Templates die Variablen `aktive_saison` und `alle_saisons` bereit.
  - Das Saison-Auswahlelement in Übersichten erlaubt die Parameterübergabe `?saison=<id>`. Ein View-Helper `get_current_season_from_request(request)` liest den Parameter aus oder fällt auf `Season.get_aktive_saison()` zurück.

### Verworfene Alternativen
- *Speichern der aktiven Saison ausschließlich in der Benutzersitzung (Session)*: Verhindert, dass Gäste oder neue Mitglieder ohne gesetzte Session eine definierte Ansicht der aktuellen Saison sehen.
- *Globale Umgebungsvariable (z. B. `CURRENT_SEASON=2026/2027`)*: Erfordert Server-Neustarts und nimmt dem ehrenamtlichen Vorstand die Möglichkeit, Spielzeiten selbstständig im Browser zu verwalten.

---

## 3. Mannschaftsbindung, Eindeutigkeit & Bestandsdaten-Migration

### Kontext & Anforderung
Bislang besaß `Team` ein Feld `name = models.CharField(max_length=100, unique=True)` ohne Saisonzugehörigkeit. In der Vereinspraxis heißt die Mannschaft jedoch in jedem Jahr „1. Mannschaft“ oder „Jugend U16“, spielt aber in wechselnden Saisons mit unterschiedlichen Ligen und Spielern.

### Entscheidung
- **Modellerweiterung**:
  - `Team` erhält das Feld `saison = models.ForeignKey(Season, on_delete=models.PROTECT, related_name="teams")`.
  - Der globale `unique=True`-Constraint auf `name` wird entfernt. Stattdessen sichert ein zusammengesetzter Constraint `UniqueConstraint(fields=["name", "saison"], name="unique_team_per_saison")` die Eindeutigkeit des Mannschaftsnamens innerhalb einer Spielzeit ab.
- **Migration bestehender Daten**:
  - Eine dreistufige Django-Migration sorgt für 100 %ige Datenintegrität:
    1. Schema-Migration: Anlegen der Tabelle `Season` und Hinzufügen von `Team.saison` mit `null=True`.
    2. Daten-Migration: Ermitteln des aktuellen Datums, Erstellen einer initialen Saison (z. B. `2025/2026` oder `2026/2027`) und Zuweisen dieser Saison zu allen bestehenden `Team`-Einträgen.
    3. Schema-Migration: Ändern von `Team.saison` auf `null=False` und Aktivieren des `UniqueConstraint`.

### Verworfene Alternativen
- *Löschen alter Teams bei neuem Saisonstart*: Verletzt die PRD-Grundregel des Datenschutzes und der Historisierung (§3.1/§3.4). Frühere Spielergebnisse und Bilanzen müssen dauerhaft erhalten bleiben.
- *`on_delete=models.CASCADE` für `Team.saison`*: Würde beim versehentlichen Löschen einer Saison alle Mannschaften, Spielberichte und Aufstellungen unwiederbringlich vernichten. Daher ist zwingend `models.PROTECT` vorgeschrieben.

---

## 4. Geführter Saisonwechsel & Mannschaftsübernahme (Rollover)

### Kontext & Anforderung
Zu Beginn einer neuen Spielzeit (z. B. `2026/2027`) soll der Vorstand nicht alle Mannschaften neu eintippen müssen, sondern bestehende Teams mit 1 Klick übernehmen und für die neue Spielklasse konfigurieren können (FR-008, US 3).

### Entscheidung
- **Reine Servicefunktion `rollover_teams(source_season, target_season, selected_teams_data, user)` in `teams/services.py`**:
  - Arbeitet atomar in einer Transaktion (`with transaction.atomic():`).
  - Für jedes ausgewählte Team der Quell-Saison wird ein neues `Team`-Objekt für die Ziel-Saison instanziiert:
    - Name wird übernommen.
    - Liga/Staffel kann übergeben/angepasst werden (z. B. Aufstieg in die Verbandsliga).
    - Altersklasse, Brettanzahl und Mannschaftsführer werden übernommen oder aktualisiert.
    - Neues, eindeutiges `ical_token` wird generiert.
    - Spiele (`LeagueMatch`) der Vorsaison werden **nicht** kopiert; der neue Spielplan startet leer.
  - Erfolgreiche Übernahme wird im `AuditLog` mit Anzahl und Namen der übernommenen Mannschaften protokolliert.
- **UI-Maske**:
  - Tabellarische Vorschau aller Mannschaften der Vorsaison mit Checkboxen, vorbelegten Liga-Eingabefeldern und Kapitänswähler.
  - Barrierefreie Darstellung mit Kontrasten ≥ 4.5:1 und mobiler Eignung ab 360 px.

### Verworfene Alternativen
- *Automatisches blindes Kopieren aller Teams ohne Bestätigung*: Führt zu Karteileichen, wenn Teams abgemeldet werden oder neue Spielgemeinschaften entstehen.
- *Manuelle Neueingabe jedes einzelnen Teams*: Zeitaufwendig, fehleranfällig und unkomfortabel für ehrenamtliche Vorstände.

---

## 5. Revisionssicherheit, Archivierungs-Schreibschutz & Löschsperre

### Kontext & Anforderung
Ist eine Saison abgeschlossen, muss verhindert werden, dass alte Spielergebnisse oder Aufstellungen versehentlich verändert werden (FR-010, FR-011, US 5). Saisons mit bestehenden Daten dürfen nicht gelöscht werden.

### Entscheidung
- **Statusmodell**:
  - `Season.Status.choices`:
    - `VORBEREITUNG = "vorbereitung"` (Planungsphase vor Saisonstart)
    - `AKTIV = "aktiv"` (Laufender Spielbetrieb)
    - `ARCHIVIERT = "archiviert"` (Abgeschlossen, schreibgeschützt)
- **Schreibschutz-Validierung**:
  - Service-Methode `can_edit_match(match)` bzw. Check in `teams/services.py`: Liegt das Spiel in einer archivierten Saison, wird jede schreibende Operation (Ergebniseingabe, Aufstellung, Absage) mit `PermissionDenied` bzw. Validierungsfehler abgewiesen.
  - In den Templates werden bei `saison.ist_archiviert` Formulareingaben gesperrt und ein Archiv-Hinweisbanner eingeblendet.
- **Löschsperre**:
  - In `Season.delete()` und in `teams.services.delete_season(season)` wird geprüft, ob verknüpfte Mannschaften (`teams.exists()`) oder Turniere vorhanden sind. Falls ja, wird eine `ProtectedError`- bzw. `ValidationError`-Meldung ausgelöst.
- **Audit-Trail**:
  - Sämtliche Statuswechsel (`set_active_season`, `archive_season`, `reopen_season`) und Rollover-Aktionen werden im zentralen `AuditLog` erfasst.

---

## 6. Abgrenzung zur Beitrags- und Finanzverwaltung

### Kontext & Anforderung
Im deutschen Vereinsrecht und Steuerrecht orientieren sich Kassenberichte, Beitragsjahre und die GoBD-Finanzbuchhaltung am bürgerlichen Kalenderjahr (01.01. bis 31.12., PRD §3.2/§3.6). Schachsaisons erstrecken sich hingegen von Spätsommer bis Frühsommer (z. B. 01.08. bis 31.07.).

### Entscheidung
- Die Saisonverwaltung steuert **ausschließlich** den sportlichen Spielbetrieb (Mannschaften, Ligen, Ligaspiele) und Vereinsturniere.
- Das Beitragsmodul (`dues`) und das Kassenbuch (`cashbook`) bleiben strikt an das Kalender- bzw. Geschäftsjahr gekoppelt und werden von der sportlichen Saison nicht verändert.
- Dies verhindert steuerliche Fehlbuchungen, unvollständige Jahresabschlüsse und Verwirrung bei Kassenprüfungen.
