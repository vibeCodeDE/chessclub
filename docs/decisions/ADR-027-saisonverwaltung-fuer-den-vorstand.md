# ADR-027: Saisonverwaltung für den Vorstand

## Status

Accepted

## Date

2026-10-17

## Context

Ein Schachverein strukturiert seinen sportlichen Spielbetrieb und Vereinsturniere in jährlichen Spielzeiten (Saisons, z. B. von August bis Juli des Folgejahres wie `2026/2027`). Bisher fehlte im System eine explizite Domänenentität für Saisons: Mannschaften und Begegnungen existierten unstrukturiert nebeneinander, was zu Problemen bei der Vorbereitung neuer Spielzeiten im Sommer und bei der revisionssicheren Historisierung alter Ergebnisse führte.

Gleichzeitig verlangen die Architektur- und Governance-Regeln ([AGENTS.md](../../AGENTS.md)):
- Strikte Trennung zwischen sportlicher Spielzeit (z. B. 01.08. bis 31.07.) und dem steuerlichen Beitrags- und Geschäftsjahr (01.01. bis 31.12. gem. PRD §3.2 und §3.6).
- Rollenmodell nach PRD §3.8: Saisonverwaltung ist dem Vorstand (`admin`) vorbehalten; Mannschaftsführer und reguläre Mitglieder besitzen reine Leserechte auf die jeweiligen Saisondaten.
- Regelbasis als reine Funktionen in `teams/services.py`, Views bleiben dünne FBVs.
- Revisionssicherheit und Auditierung: Alle statusändernden Saison-Aktionen müssen im `AuditLog` protokolliert werden.
- Datenintegrität: Finanz- und historische Spieldaten dürfen nie verloren gehen; Löschen von Saisons mit zugeordneten Daten wird strikt unterbunden.

## Decision

1. **Datenmodell `Season` (`teams/models.py`):**
   - Felder: `name` (z. B. "2026/2027"), automatischer `slug` ("2026-2027"), `startdatum`, `enddatum`, `status` (`vorbereitung`, `aktiv`, `archiviert`), `ist_aktiv` (Boolean), `notizen`, Zeitstempel.
   - Validierung: `startdatum < enddatum` in `clean()`.
   - Modifikation `Team`: `saison = ForeignKey(Season, on_delete=PROTECT)`. Eindeutigkeit über `UniqueConstraint(name, saison)`.
   - Modifikation `Tournament`: `saison = ForeignKey(Season, on_delete=SET_NULL, null=True, blank=True)`.

2. **Atomare Hauptsaison & Kontextbereitstellung:**
   - Genau eine Saison kann als aktive Hauptsaison markiert werden (`ist_aktiv=True`).
   - Umschaltung erfolgt transaktionssicher per `transaction.atomic()` über `set_active_season`.
   - Globaler Context-Processor `season_context` (`teams/context_processors.py`) stellt `aktive_saison`, `alle_saisons` und `gewaehlte_saison` templateweit bereit.

3. **Spielbetrieb & Spieldatenvalidierung:**
   - Spielbetrieb (`team_list`, `match_list`) und Turniere (`manage_list`, `public_list`) filtern standardmäßig auf die aktive Hauptsaison und bieten über den wiederverwendbaren Filter `season_filter.html` eine Historienansicht.
   - Datumsvalidierung: `validate_match_season_bounds` in `LeagueMatch.clean()` verhindert, dass Ligaspiele außerhalb des Saisonzeitfensters angelegt werden.

4. **Geführter Rollover-Assistent (`rollover_teams`):**
   - 1-Klick-Übernahme ausgewählter Mannschaften aus der Vorsaison mit Anpassung von Liga, Brettanzahl und Mannschaftsleitung.
   - Jedes neue Team erhält ein frisches `ical_token` und einen leeren Spielplan; Vorsaisondaten bleiben unberührt.

5. **Schreibschutz & Löschsperre:**
   - Archivierung (`archive_season`): Setzt `status='archiviert'`, sperrt Bearbeitung (`check_match_edit_allowed`) und warnt vor offenen Begegnungen.
   - Löschsperre (`delete_season`): Verhindert das Löschen von Saisons, denen Mannschaften oder Turniere zugeordnet sind.

## Consequences

- Klare, zukunftssichere saisonale Trennung aller sportlichen Aktivitäten ohne Kollision mit dem Beitrags- und Kassenbuchwesen.
- Drastische Entlastung der Vereinsführung beim jährlichen Saisonwechsel im Sommer.
- Revisionssichere historische Archivierung aller Ligaspiele und Vereinsturniere.
- 100 % Testabdeckung mit 41 spezifischen Saison-Tests und Einhaltung aller Query-Budgets (`assertNumQueries`).
