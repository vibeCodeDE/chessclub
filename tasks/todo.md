# Fortschrittsprotokoll: Schachvereins-Software

**Statusquelle ist `tasks/plan.md`** — dort stehen die Checkboxen. Diese Datei protokolliert nur *abgeschlossene* Tasks mit Verifikationsbelegen und nennt die nächsten Schritte. Vollständige Akzeptanzkriterien: `tasks/plan.md` · Spezifikation: `docs/prd.md`

**Release-Schnitt:** v1 = alle M-Tasks · v1.1 = alle S-Tasks erst nach v1-Abnahme

---

## Erledigt

### Phase 1: Fundament

- **T1: Projekt-Scaffold + Docker** — Django-Projekt, `core`-App, Postgres, Compose, Basis-Template mobile-first ab 360 px. *Beleg:* `docker compose up` + `pytest` + Screenshot-Check 360/768/1280 px, 3 Tests grün.
- **T2: Auth, Rollen, Navigation** — Gruppen `admin/kapitaen/mitglied`, rollenbasierte Menüs, Passwort-Reset. *Beleg:* `pytest core/` → 20+ Tests grün; Login/Logout/Reset + Menüs per DOM verifiziert, Abweisung über 403/Redirect-Tests (`core/tests/test_access.py`).
- **T3: Mitgliederstammdaten + Admin + Liste/Filter** — Modell `Member` mit Statushistorie, Admin-Liste/Suche, Detailseite, CSV-Export, kein Hard-Delete. *Beleg:* `pytest members/` → 33 Tests grün; Anlegen/Suchen/Filtern durchgespielt, Statuswechsel historisiert, Layout 360/1280 px geprüft.
- **T4: Selbstbedienung + Änderungswunsch-Workflow** — Mitglied reicht Wunsch ein, Admin gibt frei/lehnt ab; Freigabe schreibt den Wert plus Audit-Eintrag. *Beleg:* 27 neue Tests (`members/tests/test_selfservice.py`), 85 grün gesamt; Workflow im Browser durchklickt (Einreichung → Freigabe/Ablehnung → Audit-Eintrag), 360/1280 px ohne Overflow.
  - *Hinweise an Folge-Tasks:* `core/models.py` mit `AuditLog` existierte bereits (Freigabe/Ablehnung schrieben Einträge) — T5 ergänzte Signale für Stammdaten + Logins sowie die read-only Admin-Ansicht. Profil liegt in `members` unter `/profil/`, nicht in `core`.
- **T5: Audit-Log + Login-Protokoll** — Signale für Stammdaten-Änderungen (Wer/Was/Wann + Alt/Neu in `feld`/`alt_wert`/`neu_wert`) sowie Login/Logout/Abweisung mit IP; `_changed_by` setzt Admin und Freigabe-View. *Beleg:* `pytest` → 105 Tests grün (`core/tests/test_audit.py`).
- **Checkpoint 1** — 2026-09-28, 105 Tests grün im Docker-Stack; Rollen-Flow im Browser durchklickt: Menüs je Rolle, 403-Negativtest, Mitglied anlegen + Statushistorie, Wunsch → Freigabe → Audit-Eintrag mit Alt/Neu, Ablehnung mit Kommentar, Login-/Logout-Protokoll mit IP.

### Phase 2: Beiträge + Dashboard

- **T6: Dashboard-Gerüst** — Route `/dashboard/` (nur Admin, Nav-Eintrag `core:dashboard`); Wunsch-Kachel zählt offene Wünsche live (0 → kein Crash), Beitrags-/Termin-/Anmeldungs-Kacheln als Platzhalter bis T11/T16/T19. *Beleg:* `pytest core/` → 45 Tests grün (neue `core/tests/test_dashboard.py`), 114 gesamt; Browser-Check 360/1280 px ohne Overflow, Kacheln einspaltig (360) / zweispaltig (1280).
  - Committet in `de9226d`. Davor gab es zusätzlich `256abcc` (Tailwind-CLI-Build statt CDN, `.container` → `.site-container`).
- **T7: Beitragssätze + Beitragsjahre** — App `dues` mit `FeeCategory` (jahresunabhängig) und `FeeAmount` (Kategorie × Jahr × Betrag, `unique_together`); `Member.beitragskategorie` FK `null=True` = „keine Kategorie" (T8-Vorbedingung). Seed-Migration `0002_seed_beitragssaetze` legt 4 Kategorien × 2026/2027 mit **Platzhalterbeträgen** an (Erw. 90/95, Jugend 45/47, Familie 150/155, Erm. 55/57) — echte Vereinssätze sind weiterhin offen und per Admin überschreibbar. *Beleg:* `pytest` → **140 Tests grün** (24 neu in `dues/tests/test_models.py` + `dues/tests/test_admin.py`, 2 Audit-Tests in `core/tests/test_audit.py`); Negativtests: negativer Betrag (`ValidationError` + DB-Constraint), ausgetretenes Mitglied mit Kategorie, doppeltes (Kategorie, Jahr), Löschen einer vergebenen Kategorie (`ProtectedError`). Browser-Check am laufenden Stack: Kategorie-Änderungsseite zeigt 2026/2027 nebeneinander, 2027-Pflege lässt 2026 unberührt, Mitgliederliste filtert nach Kategorie.
  - *Nebenwirkung:* `AUDIT_FELDER` in `core/signals.py` ist dynamisch, deshalb protokolliert ein Kategoriewechsel jetzt automatisch mit. Damit die ID im Log lesbar wird, löst `AuditLog.anzeige_wert()` FK-Werte auf (im Admin: „Jugendliche" statt „2").
  - *Hinweise an Folge-Tasks:* T8 bucht `FeeAmount`-Posten je Jahr; ein Satz fehlt je (Kategorie, Jahr) → klarer Fehler statt 0-€-Posten. Beitragsposten/Zahlungen leben noch nicht — dafür sind T8/T9 zuständig.

---

## Nächste Schritte

Reihenfolge und Akzeptanzkriterien stehen in `tasks/plan.md`:

1. [T8](plan.md) Beitragslauf (idempotent)
2. [T9](plan.md) SEPA-Mandate + manuelle Zahlungserfassung
3. [T10](plan.md) Mahnwesen + Beitrags-Export
4. [T11](plan.md) Dashboard-Erweiterung offene Beiträge
5. [T11b](plan.md) Kassenbuch-Sicht Beiträge (Jahresübersicht) — *neu, schließt M2.6*
6. [T12](plan.md) Zugriffsprotokoll Detailansicht — hängt nur an T5, kann vor T8 gemacht werden
7. **Checkpoint 2** — Beitragslauf-Jahr komplett (Lauf → Zahlung → Mahnung → Export), Dashboard zeigt echte Zahlen, Review mit Mensch

**Danach:** Phase 3 (T13/T14) · Phase 4 (T16/T17) · Phase 4b (T19/T20) · Phase 5 (T23/T24/T25/T25b/T27)

---

## Noch offen (Blocker, keine Designfragen)

- **Beitragssätze und Kategorien des Vereins** — vor T8. Die Struktur steht (Platzhalterbeträge in der Seed-Migration); vor dem ersten echten Beitragslauf müssen die Sätze im Django-Admin unter *Dues → Beitragskategorien* eingetragen werden. Ab dann braucht **jede** Kategorie einen Satz für das Laufjahr, sonst bricht T8 mit einer klaren Meldung ab.
- SMTP-Zugangsdaten — vor T14 (dev: Django-Console-Backend)
- Domain/Hostname — vor T24
- Aufbewahrungsfristen mit Steuerberater bestätigen — vor T23 (Default 36 Monate bis Anonymisierung, 8 Jahre anonymisierte Finanzhistorie nach § 147 AO)
