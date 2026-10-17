# Implementation Plan: Schachvereins-Software

## Overview

Selbst gehostete Django-Web-App für einen Schachverein (< 200 Mitglieder): Mitglieder, Beiträge (SEPA-Status), Spielbetrieb, Turniere, Kommunikation, Kassenbuch — DSGVO-konform, deutschsprachig, Deployment per Docker Compose auf Vereinsserver.

## Architecture Decisions

> Begründungen einzelner Entscheidungen stehen als ADRs in `docs/decisions/` ([ADR-001](../docs/decisions/ADR-001-django-stack.md) bis [ADR-016](../docs/decisions/ADR-016-dsb-schnittstellen-architektur.md)).

- **Django 5 + PostgreSQL + serverseitige Templates:** Nutzer kennt Django noch nicht — Djangos Admin-Oberfläche übernimmt einen großen Teil der Verwaltungs-UI; Views bleiben einfache Function-Based Views. Keine SPA.
- **Design-System handgeschrieben in `static/css/app.css`:** kein Tailwind, kein CSS-Buildschritt, kein Node im Betrieb. Das eingebaute Stylesheet ist selbst die Quelle; ein Build würde nur einen zusätzlichen Fehlerpfad in den Betrieb bringen. (Der frühere Tailwind-CLI-Build ist mit dem Zusammenführen der Zweige entfallen.)
- **Interaktionen als eigenes Vanilla-JS (`static/js/app.js`):** Formulare funktionieren ohne JavaScript als normale POSTs; dieAJAX-Schicht ist eine Ergänzung (optimistische UI mit Rollback, Toasts, Bestätigungen). Das löst [ADR-008](../docs/decisions/ADR-008-htmx-alpine-lokal.md) ab — siehe [ADR-011](../docs/decisions/ADR-011-eigenes-javascript-statt-htmx.md).
- **Rollenmodell über Django Groups:** `admin` (Vorstand), `kapitaen`, `mitglied` — keine eigene Permission-Engine; `@login_required` + Gruppen-Checks; **verbindliche Matrix in PRD §3.8**.
- **Single-Tenant, eine Organisation:** kein Tenant-Field, kein Multi-Club-Denkwerk.
- **Fachlogik in `services.py` bzw. Fachmodulen:** getrennte Apps `members`, `dues`, `teams`, `tournaments`, `comms`, `cashbook`, `core` (Dashboard, Audit, DSGVO-Tools).
- **Vereinsprofil (Absender, Kontakt) kommt aus den Settings** (`CLUB_NAME`, `CLUB_SHORT`, `CLUB_CONTACT`) statt aus einer eigenen App mit einem einzelnen Datensatz — siehe [ADR-012](../docs/decisions/ADR-012-vereinsprofil-in-den-settings.md).
- **E-Mails über SMTP des Vereins/Providers,** Versand nur aus Gruppenverteilung mit Opt-in-Status.
- **Schweizer Paarung:** kleine Eigenimplementierung in `tournaments/pairing.py` (Buchholz-Wertung, Bye-Behandlung, Vermeidung von Wiederholungen) statt exotischer Library — Risiko bewusst minimiert, Formate ≤ 64 Spieler reichen für den Verein.
- **Betrieb mit Caddy + restic (+ Uptime Kuma):** [ADR-009](../docs/decisions/ADR-009-betrieb-caddy-restic-uptime-kuma.md). Umsetzung als T24, T24b.
- **Mobile-First + PWA:** alle Templates responsive ab 360 px (Burger-Menü, scrollbare Tabellen); Web-App-Manifest + Service Worker, damit die App auf dem Homescreen installierbar ist (keine nativen Apps, kein Store).
- **DSB-Schnittstellen-Architektur:** [ADR-016](../docs/decisions/ADR-016-dsb-schnittstellen-architektur.md) regelt die Verbandsanbindung: Keine Schreib-API beim DSB, stattdessen Drei-Säulen-Modell aus DWZ-Read-Sync (JSON-API), strukturiertem nuLiga-/LSB-Mutationsexport und TRF16-/DeWIS-Turnierformat (K3.6).

## Konventionen

- **Größe:** Task-Größe einer Session: `S` klein, `M` mittel, `L` groß. *(Früher als „Scope" geführt — hat sich mit PRD-Priorität S vermischt.)*
- **PRD:** Verweis auf die Anforderung im PRD (`M2.2`, `S3.4`, `N1.5` …). Dort gilt M = Muss, S = Sollte, K = Kann.
- **Release:** `v1` = Kernrelease (alle M-Anforderungen) · `v1.1` = ergänzende S-Anforderungen, **erst nach v1-Abnahme**.
- Jeder Testblock enthält zwingend mindestens einen **Negativtest** (verweigerter Zugriff, Randfall, Dry-Run) und für Daten-/Wiederherstellungs-Tasks einen **Integrationstest** (End-to-End-Fluss).
- **Traceability-Regel:** Jede PRD-Anforderungs-ID (M/S/K/N) ist genau einer Task zugeordnet. Beim Anlegen oder Umnummerieren einer Anforderung wird die Zuordnung hier und in `docs/prd.md` im selben Commit nachgezogen. Unzugeordnete IDs sind ein Review-Blocker.
- **Nummernvergabe:** Aufgaben-IDs werden **nicht** wiederverwenden. Nachträge erhalten ein `b`-Suffix (T7b, T9b, T10b, T11b, T15b, T16b, T24b, T25b), damit bestehende Verweise in `tasks/todo.md`, in den ADRs und im Code gültig bleiben.
- **Status:** Checkboxen `[x]`/`[ ]` stehen **ausschließlich** in dieser Datei. `tasks/todo.md` führt nur das Fortschrittsprotokoll (erledigte Tasks mit Verifikationsbelegen) und verlinkt auf die Task hier.

## Task List

### Phase 1: Fundament

- [x] **T1: Projekt-Scaffold + Docker**
  Django-Projekt, `core`-App, Settings (DEBUG, Postgres), Docker Compose (app + db), Basis-Template **mobile-first (Responsive ab 360 px, Burger-Menü, scrollbare Tabellen)**, Styles, Health-Check-Route.
  *Acceptance:* `docker compose up` → Login-Seite erreichbar; Layout auf 360 px ohne horizontalen Overflow; `pytest` läuft leer grün.
  *Verify:* `docker compose up -d` + `pytest` + Browser-Check 360/768/1280 px · *Files:* `manage.py`, `docker-compose.yml`, `Dockerfile`, `config/`, `core/` · *Größe:* M · *PRD:* N2.6, M7.2 · *Release:* v1

- [x] **T2: Auth, Rollen, Navigation**
  Login/Logout, Gruppen `admin/kapitaen/mitglied`, rollenbasierte Menüs, Passwort-Reset für Admin-Versand.
  *Acceptance:* 3 Testnutzer (eine pro Rolle) sehen unterschiedliche Menüs; Nicht-Mitglied wird abgewiesen.
  *Verify:* `pytest core/` · *Files:* `core/views.py`, `core/auth_views.py`, `core/context_processors.py`, `core/templates/` · *Größe:* S · *PRD:* M1.2, M7.2, N1.5 · *Release:* v1 · *Deps:* T1

- [x] **T3: Mitgliederstammdaten + Admin**
  Model `Member` (Profilfelder, Status aktiv/passiv/ausgetritten, Ein-/Austrittsdatum), Djangos Admin mit Liste/Suche, Mitgliederliste mit Filter, Detailseite.
  *Acceptance:* Admin legt 3 Testmitglieder an; Liste zeigt alle 3, Filter nach Status "aktiv" liefert genau 2; Statuswechsel auf "ausgetritten" erzeugt einen Historieneintrag, das Mitglied selbst bleibt per Datensatz-ID auffindbar (kein Hard-Delete); CSV-Export enthält die 3 Testmitglieder.
  *Verify:* `pytest members/` — **Negativtest:** Rolle „mitglied" erhält 403 auf der Admin-Detailseite eines fremden Mitglieds; Lösch-Aktion ist im Admin nicht vorhanden. · *Files:* `members/models.py`, `members/admin.py`, `members/views.py` · *Größe:* M · *PRD:* M1.1, M1.3, M1.5, M1.6 · *Release:* v1 · *Deps:* T2

- [x] **T4: Selbstbedienung + Änderungswunsch**
  Mitglied sieht eigene Daten, reicht Änderungswunsch ein (Feld + Wunschwert); Admin-Übersicht mit Freigabe/Ablehnung; Freigabe schreibt Wert + Audit-Eintrag.
  *Acceptance:* Wunsch fließt von Einreichung bis zur Freigabe; ohne Freigabe ändert sich nichts am Stammdatum.
  *Verify:* `pytest members/` (Workflow-Test) · *Files:* `members/models.py`, `members/views.py`, `members/templates/` · *Größe:* M · *PRD:* M1.4 · *Release:* v1 · *Deps:* T3

- [x] **T5: Audit-Log + Login-Protokoll**
  Signale loggen Änderungen an personenbezogenen Feldern (Wer, Was, Wann, Alt/Neu) + Login-Ereignisse; Admin-Ansicht löst Fremdschlüssel-IDs in Namen auf (ohne N+1).
  *Acceptance:* Jede Mitgliederänderung und jeder Login ist mit Zeit + Benutzer sichtbar; die Changelist zeigt statt einer Datenbank-ID den Namen der Kategorie.
  *Verify:* `pytest core/` — **Negativtest:** Der Audit-Eintrag ist weder anleg- noch änder- noch löschbar (`core/tests/test_audit.py`). · *Files:* `core/models.py`, `core/signals.py`, `core/admin.py` · *Größe:* M · *PRD:* M7.3, N1.5 · *Release:* v1 · *Deps:* T4

**Checkpoint 1:** Alle Tests grün; Rollen-Flow manuell durchklicken (Admin anlegen → Wunsch → Freigabe → Audit-Eintrag). *Review mit Mensch.*

### Phase 2: Beiträge + Dashboard

- [x] **T6: Dashboard-Gerüst**
  Startseite für die Vorstandsgruppe mit Kachel-Gerüst (offene Beiträge, Mitglieder, Kasse, Zahlungen, Termine, Änderungswünsche); eigene Fassung für Mitglied und für den Kapitän. Rollentrennung nach PRD §3.8: der Kapitän sieht Spielbetrieb, **keinen** Finanzwert.
  *Acceptance:* Wunsch-Kachel zeigt die echte Anzahl offener Wünsche; Beitrags-Kachel zeigt Summe und Anzahl der offenen Posten; Kapitän-Dashboard enthält weder Finanzkachel noch Beitrags-CSV noch Audit-Protokoll.
  *Verify:* `pytest core/tests/test_dashboard.py` (inkl. `KapitaenDashboardTests` als Negativtest) · *Files:* `core/views.py`, `core/templates/core/dashboard*.html` · *Größe:* S · *PRD:* M7.1 · *Release:* v1 · *Deps:* T5

- [x] **T7: Beitragssätze**
  Model `FeeCategory` (Name, Beschreibung, Betrag, aktiv), Zuordnung zum Mitglied (`Member.beitragskategorie`, nullable). Der Betrag liegt am Kategorie-Datensatz; Momentaufnahme in den Beitragsposten (T8).
  *Abweichung von [ADR-004](../docs/decisions/ADR-004-beitragssaetze-kategorie-und-betrag-getrennt.md):* die Trennung Kategorie × Jahr × Betrag (`FeeAmount`) ist **nicht** umgesetzt — offene Nacharbeit in **T7b**.
  *Acceptance:* Kategorien lassen sich anlegen, deaktivieren und löschen; eine vergebene Kategorie lässt sich nicht löschen; Mitglied ohne Kategorie wird beim Beitragslauf übersprungen, nicht mit 0 € gebucht.
  *Verify:* `pytest dues/` — **Negativtest:** negativer Betrag wird abgelehnt; Mitglied mit Status „ausgetritten" kann keiner Kategorie zugeordnet werden; Löschen einer vergebenen Kategorie wird verhindert. · *Files:* `dues/models.py`, `dues/admin.py`, `dues/forms.py` · *Größe:* S · *PRD:* M2.1 · *Release:* v1 · *Deps:* T5

- [x] **T7b: Jahresbeträge je Kategorie** *(Nachtrag, schließt ADR-004)*
  `FeeAmount` (Kategorie × Jahr × Betrag) zurückführen; der Beitragslauf nimmt den Satz des Laufjahrs, fehlt er, bricht der Lauf mit klarer Meldung ab und legt **nichts** an. Kein Klartext-IBAN-Thema.
  *Acceptance:* 2026 und 2027 lassen sich getrennt pflegen; die Änderung von 2027 lässt 2026 unberührt; Beitragsposten behalten den Betrag als Momentaufnahme.
  *Verify:* `pytest dues/` — **Negativtest:** Lauf ohne Satz für das Jahr legt keinen Posten an (auch nicht teilweise); doppelter (Kategorie, Jahr) wird abgelehnt. · *Files:* `dues/models.py`, `dues/services.py`, Migration · *Größe:* S · *PRD:* M2.1, M2.2 · *Release:* v1 · *Deps:* T7, T8

- [x] **T8: Beitragslauf**
  Jahreslauf erzeugt für alle aktiven Mitglieder mit Kategorie einen Beitragsposten (`MembershipFee`); idempotent — ein zweiter Lauf für dasselbe Jahr legt nichts doppelt an. UI `/beitraege/lauf/` (POST), Beitragsposten im Admin nur einsehbar.
  *Design:* Betrag als Momentaufnahme, Regelbasis in `dues/services.py` (`beitragslauf`), Status je Posten aus den Zahlungen — [ADR-005](../docs/decisions/ADR-005-beitragsposten-idempotenz-und-momentaufnahme.md) gilt inhaltlich, das Modell heißt jetzt `MembershipFee`.
  *Acceptance:* Lauf mit 10 Testmitgliedern → 10 Posten, zweiter Lauf → weiterhin 10; ausgetretene Mitglieder werden nie gebucht; der Lauf berührt das Kassenbuch nicht.
  *Verify:* `pytest dues/tests/test_beitraege.py` — **Negativtest:** Rolle „mitglied"/„kapitaen" erhält 403 (auch ohne dass dabei Posten entstehen); Lauf nur per POST; Mitglied ohne Kategorie wird übersprungen statt mit 0 € gebucht. · *Files:* `dues/services.py`, `dues/views.py`, `dues/urls.py`, `dues/models.py`, `dues/templates/dues/overview.html` · *Größe:* M · *PRD:* M2.2 · *Release:* v1 · *Deps:* T7

- [x] **T9: SEPA-Mandate + Zahlungserfassung**
  `SepaMandate` je Mitglied (Referenz, Datum, Status, Kontoinhaber), Zahlungen buchen (SEPA-Einzug/Überweisung/Bar, manuell, Zahlungsart je Buchung), offener Betrag je Posten. Jede Zahlung erzeugt eine Kassenbuchung.
  *Design:* kein Bank-API-Zugriff ([ADR-002](../docs/decisions/ADR-002-kein-automatisierter-sepa-einzug.md)), IBAN verschlüsselt statt im Klartext ([ADR-010](../docs/decisions/ADR-010-iban-verschluesselt-in-der-datenbank.md)), Maskierung in Listen. **Storno per Gegenbuchung fehlt noch** — [ADR-006](../docs/decisions/ADR-006-storno-per-gegenbuchung.md) ist über **T9b** nachzuziehen.
  *Acceptance:* Zahlung markiert den Posten als bezahlt; Teilzahlung bleibt offen; Überzahlung wird als Gutschrift sichtbar, nicht gekappt; die Kassenbuchung entsteht in derselben Transaktion.
  *Verify:* `pytest dues/` + `dues/tests/test_rollen.py` — **Negativtest:** Zahlung für ein Mitglied ohne Mandat bei Zahlungsart „SEPA-Einzug" wird abgelehnt; 403 für „mitglied"/„kapitaen" ohne Seiteneffekt; Betrag 0 abgelehnt. · *Files:* `dues/models.py`, `dues/services.py`, `dues/views.py`, `dues/crypto.py` · *Größe:* M · *PRD:* M2.3, M2.4 · *Release:* v1 · *Deps:* T8

- [x] **T9b: Storno von Zahlungen per Gegenbuchung** *(Nachtrag, schließt ADR-006)*
  `Payment.storno_von` (Selbstbezug), Gegenbuchung mit negativem Betrag und Verweis, Status des Postens wird neu berechnet, Audit-Eintrag mit Actor. Kein Hard-Delete, keine Lösch-Aktion im Admin.
  *Acceptance:* Storno einer Zahlung setzt den Posten auf den vorherigen Status; Originalbuchung bleibt lesbar; Kassenbuch enthält Original und Gegenbuchung.
  *Verify:* `pytest dues/` — **Negativtest:** Storno eines Stornos wird abgelehnt; Storno einer Zahlung mit Audit-Eintrag ist nur mit Actor erlaubt; Buchung ist im Admin nicht löschbar. · *Files:* `dues/models.py`, `dues/services.py`, `dues/views.py`, `dues/admin.py`, Migration · *Größe:* M · *PRD:* M2.3 · *Release:* v1 · *Deps:* T9

- [x] **T9c: SEPA-XML-Export (pain.008)** *(v1.1)*
  Standardisierter SEPA-XML-Download (pain.008.001.02) für offene Beitragsposten mit aktivem SEPA-Mandat zur manuellen Abgabe im Online-Banking (Sparkasse, Volksbank etc.).
  *Design:* [ADR-017](../docs/decisions/ADR-017-sepa-xml-export-pain-008.md) und [Spec](../docs/superpowers/specs/2026-10-07-t9c-sepa-xml-export.md). Reines stdlib `xml.etree.ElementTree` ohne Netzwerk-Imports (ADR-002 bleibt intakt), flüchtige Entschlüsselung im RAM (ADR-010), EPC-Zeichensatzbereinigung, AuditLog-Protokollierung ohne Klartext-IBANs (DSGVO N1.5), O(1)-Query-Budget.
  *Acceptance:* Kassenwart klickt auf SEPA-XML-Export für das gewählte Beitragsjahr; XML-Datei entspricht pain.008.001.02 mit korrekter Kontrollsumme, Transaktionsanzahl, Gläubiger-ID und Mandatsdaten; Posten ohne Mandat oder bereits bezahlt werden übersprungen; AuditLog erfasst den Export; Nicht-Admins werden abgewiesen.
  *Verify:* `pytest dues/tests/test_sepa_export.py` + `pytest dues/tests/test_rollen.py` — **Negativtest:** Rollen „mitglied“ und „kapitaen“ erhalten 403; Beitragsjahr ohne offene Mandatsposten bricht mit klarer Meldung ab; widerrufene Mandate und bezahlte Posten werden nicht eingezogen; `assertNumQueries` prüft O(1)-Budget; `test_keine_bank_api.py` bleibt grün. · *Files:* `dues/services.py`, `dues/views.py`, `dues/urls.py`, `dues/templates/dues/overview.html`, `config/settings.py`, `.env.prod.example` · *Größe:* S · *PRD:* S2.7 · *Release:* v1.1 · *Deps:* T9

- [x] **T10: Mahnwesen + Beitrags-Export**
  Offene-Beitragsübersicht mit 1./2. Mahnung, Mahnbrief als druckbares HTML, CSV-Export der Jahresbeiträge. Stufe streng +1 (max. 2), kein Mahnen eines bezahlten Postens, Prüfungen im Service.
  *Design:* Mahnbrief als druckbares HTML ([ADR-007](../docs/decisions/ADR-007-mahnbrief-als-druckbares-html.md)); Vereinsdaten aus den Settings ([ADR-012](../docs/decisions/ADR-012-vereinsprofil-in-den-settings.md)). Regelbasis in `dues/services.py` (`mahnung_erstellen`, `mahntext`).
  *Acceptance:* Mahnbrief druckbar für ein Testmitglied; CSV enthält alle Posten des Jahres mit erlaubten Feldern; zwei Exporte sind identisch.
  *Verify:* `pytest dues/tests/test_beitraege.py` + `test_rollen.py` — **Negativtest:** Nicht-Admin erhält 403 auf Übersicht, Brief, Export **und** POST (jeweils ohne Seiteneffekt); bezahlter Posten ist nicht mahnbar; Stufe wird nicht übersprungen. · *Files:* `dues/templates/dues/mahnbrief.html`, `dues/services.py`, `dues/views.py` · *Größe:* M · *PRD:* M2.5 · *Release:* v1 · *Deps:* T9

- [x] **T10b: Interaktionen ohne Neuladen** *(Nachtrag — in anderer Form umgesetzt)*
  Umsetzung als eigenes Vanilla-JS in `static/js/app.js` (AJAX-Fragment für „Mahnung setzen", Kategorie-Toggle, Zahlung, optimistische UI mit Rollback, Toasts). Kein HTMX, kein Alpine, kein CDN — [ADR-011](../docs/decisions/ADR-011-eigenes-javascript-statt-htmx.md) löst [ADR-008](../docs/decisions/ADR-008-htmx-alpine-lokal.md) ab. Jedes Formular funktioniert ohne JavaScript als normaler POST.
  *Acceptance:* Mahnung und Zahlung lassen sich ohne Seiten-Reload auslösen; ohne JavaScript funktioniert dasselbe Formular als POST; es wird kein Skript von einem fremden Host geladen.
  *Verify:* `pytest dues/tests/test_beitraege.py` (AJAX-Antwort und Fehlerfall) — **Negativtest:** Aufruf ohne `X-Requested-With` liefert die volle Seite statt des Fragments; kein `http(s)://` in `<script src>`. · *Files:* `static/js/app.js`, `core/ui.py`, `dues/views.py` · *Größe:* S · *PRD:* — (Technik; unterstützt N2.3, N1.1) · *Release:* v1 · *Deps:* T10

- [x] **T11: Dashboard-Erweiterung offene Beiträge**
  Beitrags-Kacheln befüllen (offene Summe + Anzahl, Fortschrittsbalken) aus `jahres_uebersicht(jahr)`.
  *Acceptance:* Nach Seed + Lauf zeigt die Beitrags-Kachel die echte offene Summe; ohne Daten bleibt die Anzeige bei 0 € statt zu crashen.
  *Verify:* `pytest core/tests/test_dashboard.py` · *Größe:* S · *PRD:* M7.1 · *Release:* v1 · *Deps:* T10

- [x] **T11b: Kassenbericht Beiträge (Jahresübersicht)**
  Reine Lese-Sicht für den Kassenbericht: Zahlungen je Mitglied für ein gewähltes Jahr, Jahressumme der Einnahmen aus Beiträgen, offene Posten zum Stichtag. Kein eigenes Buchungssystem — das bleibt S6.1/S6.2 (v1.1, T15). Die Auswertung `jahres_uebersicht()` und der Kassen-Jahresabschluss sind bereits da; es fehlt die **Mitgliedsliste je Jahr mit Zahlungen** und der CSV-Export dieser Sicht.
  *Acceptance:* Für Jahr X mit 10 Mitgliedern und 8 Zahlungen zeigt die Übersicht 8 Zeilen; die Jahressumme entspricht der im Test berechneten Modellsumme; ein Jahr ohne Daten zeigt „keine Buchungen" statt 0-€-Zeilen; der CSV-Export summiert identisch zur Anzeige.
  *Verify:* `pytest dues/` — **Negativtest:** Rolle „kapitaen" und „mitglied" erhalten 403; **Referenztest:** Jahressumme wird gegen eine im Test berechnete Modellsumme verglichen, nicht gegen einen festen Wert. · *Files:* `dues/views.py`, `dues/templates/` · *Größe:* S · *PRD:* M2.6 · *Release:* v1 · *Deps:* T10

- [x] **T12: Zugriffsprotokoll Detailansicht**
  Protokolliert den Aufruf einer Mitglieder-Detailansicht (Wer, Wann, welche Person) als Lese-„Zugriff" im `AuditLog` — schließt die Lücke zwischen PRD N1.5 („Zugriffe") und T5 (nur Änderungen + Logins). Der **JSON**-Export der Datenauskunft wird heute noch nicht protokolliert (HTML und PDF werden es) — das gehört in dieselbe Task.
  *Acceptance:* Detailaufruf erzeugt einen AuditLog-Eintrag; jeder Auskunfts-Export (HTML/PDF/JSON) wird protokolliert; Einträge sind nach 12 Monaten Löschfrist markierbar.
  *Verify:* `pytest core/` + `pytest members/` — **Negativtest:** Listenansicht erzeugt **keinen** Lese-Eintrag; Rolle „mitglied" darf die Detailseite eines fremden Mitglieds nicht öffnen (403); der JSON-Export ohne Eintrag im Log schlägt fehl. · *Files:* `members/views.py`, `core/views.py`, `core/models.py` · *Größe:* S · *PRD:* N1.5 · *Release:* v1 · *Deps:* T5

**Checkpoint 2:** Beitragslauf für ein Testjahr komplett durchgespielt (Lauf → Zahlung → Mahnung → Export); Dashboard zeigt echte Zahlen; Rollenmatrix je Zeile durch negative Tests belegt. *Review mit Mensch.*

### Phase 3: Kommunikation (öffentliche Präsenz)

- [x] **T13: News/Ankündigungen + öffentliche Startseite**
  `NewsPost` (Titel, Text, Datum, Entwurf/veröffentlicht), öffentliche Startseite zeigt veröffentlichte Posts, Admin-CRUD, Archiv.
  *Acceptance:* 2 Beiträge (1 Entwurf, 1 veröffentlicht) angelegt; Startseite zeigt genau 1 Beitrag; Archiv listet beide nach Datum sortiert, Entwurf nur für Admin sichtbar.
  *Verify:* `pytest comms/` — **Negativtest:** Entwurf für Gast nicht sichtbar (nicht in Liste, 404 auf Detail); Nicht-Admin darf weder anlegen noch veröffentlichen (403). · *Files:* `comms/models.py`, `comms/views.py` · *Größe:* S · *PRD:* M5.1 · *Release:* v1 · *Deps:* T11

- [x] **T14: E-Mail-Versand an Gruppen**
  Opt-in-Flag je Mitglied, Formular „E-Mail an Gruppe" (Betreff, Text, Empfängergruppe), Versand via SMTP, Versandprotokoll (An, Wann, Status).
  *Acceptance:* Testversand an drei Empfänger im Nur-Test-Modus; Versandprotokoll enthält alle 3 mit Zeitpunkt und Status; ein opt-out-Mitglied in der Gruppe wird übersprungen.
  *Verify:* `pytest comms/` — **Negativtest:** Opt-out-Mitglied erhält keine Mail; Nicht-Admin darf nicht versenden (403); leere Empfängergruppe bricht mit klarer Meldung ab, statt 0 Mails still zu senden. · *Files:* `comms/views.py`, `comms/services.py` · *Größe:* M · *PRD:* M5.2 · *Release:* v1 · *Deps:* T13

**Checkpoint 3:** News veröffentlichen + Test-Mail. *Review mit Mensch.*

### Phase 4: Spielbetrieb

- [x] **T16: Mannschaften + Ligaspiele**
  Models `Team` (Kapitän, Liga, Brettanzahl), `LeagueMatch` (Datum, Uhrzeit, Gegner, Heim/Auswärts, Runde, Status, Ergebnis), CRUD für Admin.
  *Acceptance:* 2 Mannschaften und 1 Ligaspiel angelegt und in der Liste sichtbar; Spiel erscheint in der Liste der eigenen Mannschaft; abgeschlossene Spiele lassen sich nicht mehr ändern.
  *Verify:* `pytest teams/` — **Negativtest:** Rollen „mitglied" und „kapitaen" erhalten 403 auf Anlegen/Bearbeiten; Änderung eines Spiels im Status „abgeschlossen" wird abgelehnt. · *Files:* `teams/models.py`, `teams/views.py` · *Größe:* S · *PRD:* M4.1, M4.2 · *Release:* v1 · *Deps:* T14

- [x] **T16b: iCal-Feed der Ligaspiele** *(v1.1 — umgesetzt)*
  Abonnierbarer Kalender-Feed (`.ics`) der Ligaspiele je Mannschaft und gesamt, Zugriff über geheimen Token-Link; Token durch Admin erneuerbar (macht alte Links ungültig). Reine Funktion für die Feed-Erzeugung in `teams/services.py`, ohne Bibliothek (RFC 5545, wenige Felder).
  *Acceptance:* Feed enthält genau die Spiele der gewählten Mannschaft mit Datum, Gegner, Heim/Auswärts; Import in einen Kalenderclient zeigt die Termine; nach Token-Erneuerung liefert der alte Link 404.
  *Verify:* `pytest teams/` — **Negativtest:** ungültiger oder fehlender Token → 404 (kein Hinweis, ob die Mannschaft existiert); Feed enthält keine Aufstellungs- und keine Personendaten; abgesagte Spiele werden als `STATUS:CANCELLED` ausgegeben, nicht weggelassen; `assertNumQueries` für den Feed. · *Files:* `teams/services.py`, `teams/views.py` · *Größe:* S · *PRD:* S4.6 · *Release:* v1.1 · *Deps:* T16

- [x] **T17: Aufstellung + Einzelergebnisse**
  Kapitän trägt Aufstellung ein (Reihenfolge Mitglieder); Ergebnis je Brett (1/0/½) → Mannschaftsergebnis automatisch; Live-Brettpunkte im Browser.
  *Acceptance:* Nur Kapitän/Admin kann aufstellen; Summe der Bretter = Mannschaftsergebnis; die Aufstellung bleibt ohne JavaScript speicherbar.
  *Verify:* `pytest teams/` — **Negativtest (PRD §3.8):** Kapitän einer **anderen** Mannschaft erhält 403; Rolle „mitglied" darf nicht aufstellen. · *Files:* `teams/views.py`, `teams/models.py`, `teams/templates/` · *Größe:* M · *PRD:* M4.3, M4.4 · *Release:* v1 · *Deps:* T16


- [x] **T18: Tabellenberechnung inkl. Buchholz** *(v1.1)*
  Liga-Tabelle aus allen Ergebnissen (Satz 1/½/0, Buchholz als Tiebreak). `teams/services.py:tabelle()` summiert heute Mannschafts- und Brettpunkte und die Differenz, **eine Buchholz-Spalte fehlt** — die Tabelle ist damit unvollständig, nicht falsch.
  *Acceptance:* 4 Mannschaften × 3 Spiele → korrekte Reihenfolge inkl. Buchholz (Testdatensatz mit bekanntem Ergebnis); ungespielte Spiele zählen nicht.
  *Verify:* `pytest teams/` (Referenzrechnung; Umgang mit ungespielten/abgesagten Spielen als Negativfall) · *Files:* `teams/services.py`, `teams/templates/teams/tabelle_list.html` · *Größe:* S · *PRD:* S4.5 · *Release:* v1.1 · *Deps:* T17

**Checkpoint 3b:** Testspiel komplett (Aufstellung → Ergebnis). *Review mit Mensch.*

### Phase 4b: Turniere

- [x] **T19: Turnier-Modell + öffentliche Anmeldung**
  `Tournament` (Datum, Ort, Format, Anmeldeschluss, Startgeld-Status), öffentliche Detailseite + Anmeldeformulare (Mitglied/Gast mit Name + E-Mail), Teilnehmerliste.
  *Acceptance:* Öffentliche Seite ohne Login erreichbar; Mitgliedsanmeldung und Gastanmeldung landen in der Teilnehmerliste; die Gastanmeldung zeigt nur Name + E-Mail (N1.7).
  *Verify:* `pytest tournaments/` — **Negativtest:** Anmeldung nach Anmeldeschluss abgewiesen; doppelte Anmeldung derselben E-Mail unterbunden; Gastdaten erscheinen nur in der Turnierverwaltung, nicht in der Mitgliederliste und nicht in der Mitgliedersuche (N1.7). · *Files:* `tournaments/models.py`, `tournaments/views.py` · *Größe:* M · *PRD:* M3.1, M3.2, N1.7 · *Release:* v1 · *Deps:* T17

- [x] **T20: Runden + Ergebniserfassung + Zwischenwertung**
  Runden anlegen, Ergebnisse je Partie (1/0/½), Zwischenstand (Punkte, Buchholz) — handpaarierbarer Kern des Schweizer Systems.
  *Acceptance:* 8 Testspieler, 3 Runden → Zwischenstand korrekt (Referenzrechnung im Test).
  *Verify:* `pytest tournaments/` — **Negativtest:** Ergebnis ändern nur für Turnierverwalter; Doppelpartien in einer Runde abgewiesen; nur die letzte Runde ist löschbar. · *Files:* `tournaments/views.py`, `tournaments/models.py` · *Größe:* M · *PRD:* M3.3 · *Release:* v1 · *Deps:* T19

- [x] **T21: Schweizer Paarung** *(v1.1 — umgesetzt)*
  Paarungsservice in `tournaments/pairing.py` (Buchholz, Bye-Handling, Farbausgleich, Vermeidung von Wiederholungen), idempotent je Rundennummer.
  *Acceptance:* 8 Testspieler, 3 Runden: Paarungen ohne Doppel-Partien, Stand korrekt (Referenzrechnung).
  *Verify:* `pytest tournaments/` (Paarungs-Tests) — **Negativtest:** Spielerzahl ohne Bye-Regel → klare Fehlermeldung statt stummer Fehlpaarung. · *Files:* `tournaments/pairing.py`, `tournaments/views.py` · *Größe:* L · *PRD:* S3.4 · *Release:* v1.1 · *Deps:* T20

- [x] **T22: Turnierexport im ChessResults-Format** *(v1.1 — umgesetzt)*
  Druckansicht und CSV-Export nach ChessResults-/Swiss-Manager-Struktur mit den Abschnitten `[TRN]`, `[ARB]` und `[RAN]`, Semicolon-Trennzeichen und Kennungen `TRN`/`ARB`/`RAN`.
  *Acceptance:* CSV importiert ohne Nacharbeit in ChessResults (oder im dokumentierten Ersatzwerkzeug); Druckansicht A4-freundlich.
  *Verify:* `pytest tournaments/` + manueller Download — **Negativtest:** Nicht-Admin erhält 403 auf den CSV-Export; **Inhaltstest:** CSV enthält keine Privatanschriften/Telefonnummern, nur Turnierfelder. · *Files:* `tournaments/views.py`, Templates · *Größe:* S · *PRD:* S3.5 · *Release:* v1.1 · *Deps:* T20

**Checkpoint 4:** Testturnier über 3 Runden gespielt (Paarung → Ergebnisse → Zwischenstand). *Review mit Mensch.*

### Phase 5: DSGVO & Betrieb

- [x] **T23: DSGVO-Auskunfts-Export + Löschfristen**
  Ein-Klick-Auskunft je Mitglied als HTML, PDF und JSON, automatische Anonymisierung nach Austritt + konfigurierbarer Frist (Management-Command), maschinenlesbarer Export der Datenkategorien; HTML- und PDF-Export werden protokolliert.
  *Acceptance:* Auskunft enthält alle personenbezogenen Felder; Anonymisierung löscht Kontaktdaten, behält die Finanzhistorie anonymisiert; Frist konfigurierbar.
  *Verify:* `pytest core/` + `python manage.py anonymize_former_members --dry-run` — **Integrationstest:** Vollzyklus Austritt → Frist abgelaufen → Command → alle Felder geprüft; **Negativtest:** `--dry-run` ändert nichts; nach Anonymisierung ist die Suche nach Name/E-Mail **leer**, die Finanzhistorie aber intakt. · *Files:* `core/views.py`, `core/dsgvo.py`, `core/pdf.py`, `core/management/commands/` · *Größe:* M · *PRD:* N1.2, N1.3, N1.4 · *Release:* v1 · *Deps:* T12

- [x] **T24: Deployment + Backup + Restore-Doku**
  Produktions-Compose mit App und PostgreSQL, Caddy TLS-Reverse-Proxy, verschlüsseltes nächtliches `pg_dump`-Backup (OpenSSL AES-256-CBC PBKDF2), `docs/deployment.md` inkl. Restore-Anleitung, Restore-Testprotokoll (< 4 h) und Updatepfad; EU/DE-Standortnachweis.
  *Acceptance:* Backup ist komprimiert **und verschlüsselt**, Passwort/Schlüssel liegt getrennt vom DB-Host; Restore-Test einmal erfolgreich durchgespielt (< 4 h) inklusive Entschlüsselung und Zeilenanzahl-Abgleich; `docs/deployment.md` nennt Server/Provider mit EU/DE-Standort; Update auf eine neue Image-Version läuft per dokumentiertem Ablauf ohne Datenverlust.
  *Verify:* **Integrationstest:** Backup → leere DB → Restore → Daten da + Integritäts-Abgleich; **Negativtest:** korruptes Backup bzw. fehlender Schlüssel wird mit klarem Fehler abgewiesen, statt stillschweigend einen leeren Datenbestand zu schreiben. · *Files:* `docker-compose.prod.yml`, `Caddyfile`, `tools/backup.sh`, `tools/restore.sh`, `docs/deployment.md`, `config/tests/test_deployment.py` · *Größe:* M · *PRD:* N2.1, N2.4, N1.1 · *Release:* v1 · *Deps:* T23


- [x] **T24b: Monitoring mit Uptime Kuma** *(v1.1 — umgesetzt)*
  Monitoring-Container in `docker-compose.prod.yml`: Prüfung der Health-Check-Route, Push-Monitor für das nächtliche Backup, Alarm per E-Mail an die Admin-Adresse. Anleitung in `docs/deployment.md`, Abschnitt „Monitoring".
  *Acceptance:* Stoppt man den App-Container, kommt innerhalb des eingestellten Intervalls genau eine Alarm-Mail; bleibt die Backup-Meldung aus, kommt ebenfalls eine; nach Wiederanlauf folgt eine Entwarnung.
  *Verify:* Integrationstest per Compose-Config (`docker compose -f docker-compose.prod.yml config`) + dokumentierter manueller Ausfalltest — **Negativtest:** Der Monitor ist von außen nicht ohne Login erreichbar; Alarm-Mails enthalten keine Personendaten (nur Dienstname, Zeit). · *Files:* `docker-compose.prod.yml`, `docs/deployment.md` · *Größe:* S · *PRD:* N2.8 · *Release:* v1.1 · *Deps:* T24

- [x] **T25: Härtung: Header, Fehlalarme, Produktions-Settings, Wartungsdoku**
  Sicherheits-Header-Middleware (HSTS, X-Frame, X-Content-Type, Referrer-Policy, Permissions-Policy, CSP), Fehlerbenachlichtigung per E-Mail an Admin, `config/production.py` erzwingt Secret-Key und echtes Mail-Backend und wird vom Prod-Compose aktiviert, `docs/wartung.md` als Django-Primer.
  *Acceptance:* Jeder Header per Response-Check nachgewiesen; erzwungener Serverfehler erzeugt genau eine E-Mail an die Admin-Adresse mit Traceback im Log (nicht im Mail-Body); der Prod-Compose startet nicht ohne Secret-Key und ohne SMTP-Backend.
  *Verify:* `pytest core/tests/test_haertung.py` + `pytest config/` — **Negativtest:** `config.production` bricht mit `ImproperlyConfigured` ab, wenn `DJANGO_SECRET_KEY` fehlt oder das Console-Mail-Backend gesetzt ist. · *Files:* `core/middleware.py`, `config/production.py`, `config/settings.py`, `docker-compose.prod.yml`, `docs/wartung.md` · *Größe:* M · *PRD:* N2.5 · *Release:* v1 · *Deps:* T24

- [x] **T25b: NFR-Nachweis — Performance + Barrierefreiheit**
  Messung statt Behauptung. **Stand:** Die Latenzmessungen liegen in `docs/abnahme.md` (Dashboard 79 ms, Mitglieder 76 ms, Beiträge 168 ms, Turniere 65 ms, Suche 61 ms) — allerdings auf SQLite im Entwicklungsrechner mit dem Testclient, also ohne Netz und ohne PostgreSQL. **Offen:** WCAG-2.1-AA-Durchgang (Kontraste, Formular-Labels, Tastaturbedienung, Fokusreihenfolge), der 360-px-Durchgang für alle Kernflächen, der Updatepfad-Nachweis und `docs/nfr-pruefung.md` als Ort mit Messwert, Methodik, Datum und Uhrzeit/Netzwerk.
  *Acceptance:* Für jede der 5 Kernflächen liegt ein Messwert auf der Zielhardware vor; Kontraste, Labels, Tastaturbedienung und Fokus geprüft — schwere Verstöße (A/AA) sind 0 oder als dokumentierte Ausnahme im PRD-§7-Erfolgskriterium vermerkt.
  *Verify:* `pytest core/` (automatisierbare Teilprüfungen) + manueller Audit-Durchgang mit Tastatur — **Negativtest:** Auf 360 px darf kein horizontaler Overflow entstehen. · *Files:* `core/tests/test_a11y.py`, `docs/nfr-pruefung.md`, `docs/abnahme.md` · *Größe:* M · *PRD:* N2.2, N2.3, N2.4 · *Release:* v1 · *Deps:* T25

- [x] **T26: 2FA für die Vorstandsgruppe** *(v1.1 — umgesetzt)*
  TOTP als eigene schlanke Implementierung in `core/twofa.py` (kein Fremdpaket), Gerät je Vorstandskonto (`TwoFactorDevice`), erzwungen für die Admin-Gruppe im Produktivbetrieb (`TWOFA_PFLICHT`), in der Entwicklung abschaltbar.
  *Acceptance:* Admin-Login erfordert 2FA; Gerät kann im Profil eingerichtet und gewechselt werden; Rollen „mitglied"/„kapitaen" bleiben ohne 2FA.
  *Verify:* `pytest core/tests/test_haertung.py` — **Negativtest:** Admin-Login ohne gültiges Token wird abgewiesen; ein Token außerhalb des Zeitfensters wird nicht akzeptiert. · *Files:* `core/twofa.py`, `core/auth_views.py`, `core/models.py` · *Größe:* S · *PRD:* N1.6 · *Release:* v1.1 · *Deps:* T25

- [x] **T26b: Brute-Force-Schutz (django-axes) und Dev-Tooling (django-debug-toolbar, django-extensions)** *(v1.1 — umgesetzt)*
  Brute-Force-Schutz für Logins (`/anmelden/`, `/admin/`) nach 5 Fehlversuchen mit 1 Stunde Sperre und barrierefreier deutscher Sperrseite (`core/lockout.html`) gemäß [ADR-015](../docs/decisions/ADR-015-brute-force-schutz-und-dev-profiling.md). Entwicklungs-Profiling mit `django-debug-toolbar` (N+1-Query-Prüfung, SQL-Budgets) und Entwicklungs-Tools mit `django-extensions` (`shell_plus`, `show_urls`, `validate_templates`) aktiv bei `DEBUG=True`, vollkommen abgeschaltet in Produktion (`DEBUG=False`).
  *Acceptance:* 5 Fehlversuche sperren den Zugang mit HTTP 429 und Lockout-Template; erfolgreiche Anmeldung setzt den Zähler zurück; `/__debug__/` ist in Produktion 404 und nicht erreichbar; `validate_templates` meldet 0 Syntaxfehler; 2FA-Vervollständigung funktioniert mit mehreren Auth-Backends.
  *Verify:* `pytest core/tests/test_axes_and_toolbar.py` — **Negativtest:** 6. Versuch nach 5 Fehlern liefert 429; `/__debug__/` bei `DEBUG=False` liefert 404; Dev-Tools in Produktion nicht aktiv. · *Files:* `requirements.txt`, `config/settings.py`, `config/urls.py`, `config/settings_test.py`, `core/auth_views.py`, `core/templates/core/lockout.html`, `core/tests/test_axes_and_toolbar.py`, `docs/decisions/ADR-015-brute-force-schutz-und-dev-profiling.md` · *Größe:* S · *PRD:* N1.6, N2.2 · *Release:* v1.1 · *Deps:* T26

- [x] **T15: Kassenbuch** *(v1.1 — umgesetzt)*
  `CashEntry` (Einnahme/Ausgabe, Kategorie, Betrag, Datum, Notiz, Belegnummer), Liste + Jahresfilter, Jahresabschluss, CSV-Export für den Steuerberater.
  *Acceptance:* Buchungen anlegen/filtern; Jahres-CSV summiert korrekt; **keine** Löschfunktion für Buchungen.
  *Verify:* `pytest cashbook/` — **Negativtest:** Nicht-Admin erhält 403 auf Liste + Export; **Inhaltstest:** CSV-Summe stimmt für gefiltertes Jahr (Vergleich mit Model-Berechnung). · *Files:* `cashbook/models.py`, `cashbook/views.py` · *Größe:* S · *PRD:* S6.1, S6.2 · *Release:* v1.1 · *Deps:* T14

- [x] **T15b: Kassenbuch stornieren statt löschen** *(Nachtrag, schließt ADR-006)*
  Buchung wird nicht gelöscht, sondern mit einer Gegenbuchung (negativer Betrag, Verweis auf die Originalbuchung, Begründung, Actor) und Audit-Eintrag storniert; die Liste zeigt beide Zeilen. Die automatische Beitrags-Kassenbuchung aus T9 bleibt unangetastet.
  *Acceptance:* Der Jahresabschluss und der CSV-Export bleiben nachvollziehbar (Original + Gegenbuchung); ein Storno ist im Admin nicht rückgängig zu machen.
  *Verify:* `pytest cashbook/` — **Negativtest:** Es existiert keine Lösch-Route mehr (404/405); ein Storno ohne Begründung wird abgelehnt; der Saldo ist nach dem Storno wieder wie vor der Buchung. · *Files:* `cashbook/models.py`, `cashbook/views.py`, `cashbook/admin.py`, Migration · *Größe:* S · *PRD:* S6.1, S6.2 · *Release:* v1.1 · *Deps:* T15

- [x] **T27: PWA — installierbare App**
  `manifest.webmanifest` (Name, Icons, `display: standalone`, Farbschema), Service Worker (App-Shell + Statics aus Cache, Network-First für den Rest), iOS-Meta-Tags (apple-touch-icon, Statusbar), Registrierung im Basis-Template, Versions-/Cache-Invalidierung bei Deploy.
  *Acceptance:* „Zum Homescreen hinzufügen" auf Android + „Zum Bildschirm hinzufügen" auf iOS funktioniert; App öffnet sich ohne Browser-UI; Startseite lädt offline aus dem Cache; Update invalidiert den alten Cache.
  *Verify:* `pytest core/tests/test_pwa.py` + manuell Chrome DevTools → Application → Add to home screen — **Negativtest:** offline erscheint nur die Offline-Seite, **keine** angeforderten Seiten werden mit veralteten Daten aus dem Cache bedient. · *Files:* `core/views.py`, `static/manifest.webmanifest`, `static/sw.js`, `tools/generate_icons.py` · *Größe:* M · *PRD:* N2.7 · *Release:* v1 · *Deps:* T25

- [x] **T28: Öffentliche Designsprache (Referenz-ZIP)**
  Der öffentliche Teil der App folgt der Designsprache aus `schachclubmanager-modern-web-design (1).zip`:
  eigenes Stylesheet `static/css/site.css`, Hüllen `public_base.html`/`auth_base.html`, Startseite, Aktuelles
  (Liste mit Kategoriefilter + Detail), Turniere (Liste + Detail mit Anmeldung), Mitglied werden, neue Seite
  `/verein/` (Selbstverständnis, Zeiten, Ligaspielplan) sowie 404, Offline und der Anmeldeeinstieg.
  Alle Inhalte kommen aus den vorhandenen Modellen; das Vereinsprofil aus den Settings.
  Siehe [ADR-013](../docs/decisions/ADR-013-oeffentliche-designsprache.md) und
  [Spec](../docs/superpowers/specs/2026-09-30-oeffentliche-designsprache.md). Der interne Bereich bleibt unverändert.
  *Acceptance:* Alle öffentlichen Seiten laden ohne Templatfehler; jede im öffentlichen Bereich verwendete Klasse ist in
  `site.css` definiert; öffentliche Templates laden weder `app.css` noch `landing.css`; kein externes Asset
  (N1.1); Kategoriefilter und Turnieranmeldung funktionieren; Navigation markiert die aktive Seite.
  *Verify:* `pytest core/tests/test_oeffentliches_design.py` — **Negativtest:** eine unbekannte Kategorie im Filter
  zeigt weiterhin alle Beiträge (nichts wird versteckt), Entwürfe bleiben verborgen, ein nicht öffentliches Turnier
  bleibt 404, ein Storno der offenen Anmeldung zeigt kein Formular, und ohne gepflegte Vereinsdaten erscheinen
  keine erfundenen Angaben. · *Files:* `static/css/site.css`, `templates/public_base.html`, `templates/auth_base.html`,
  `templates/404.html`, `templates/includes/public_field.html`, `core/templates/core/*`,
  `tournaments/templates/tournaments/public_*`, `members/templates/members/join_info.html`, `core/views.py`,
  `core/urls.py`, `static/js/public.js`, `static/sw.js`, `static/img/` · *Größe:* L · *PRD:* S9.1, S9.2, S9.3, S9.4 · *Release:* v1.1 · *Deps:* T13, T19

- [x] **T29: DSB- / DWZ-Synchronisation & Drift Detection** *(v1.1 — umgesetzt)*
  Anbindung an die offizielle JSON-Schnittstelle des DSB-Wertungsportals (`https://www.schachbund.de/wertungsportal-api/vereinsliste`):
  Serverseitiges Caching (24 h), Drift Detection (fehlt im Verband, fehlt im Verein, Status- und DWZ-Abweichungen),
  Übernahme aktualisierter DWZ/DWZ-Indizes und Verbandskennungen (`zps_nummer`, `pkz`, `fide_id`, `spielberechtigung`),
  AuditLog-Protokollierung und UI-Übersicht `/mitglieder/dsb-sync/`.
  *Design:* [ADR-016](../docs/decisions/ADR-016-dsb-schnittstellen-architektur.md), reiner Fachservice `members.services.dsb_sync` ohne HTTP-Abhängigkeit.
  *Acceptance:* Verbandsdaten werden gecacht abgerufen; Drift-Erkennung identifiziert DWZ-Abweichungen, fehlende Verbands- und Vereinsmitglieder sowie Statusdiskrepanzen; DWZ-Werte lassen sich einzeln oder gesammelt übernehmen; AuditLog erfasst Abgleiche und Wertänderungen; Nicht-Admins werden abgewiesen.
- [x] **T30: Modul-Toggles im Admin-Panel (UI- und Feature-Schalter)** *(v1.1)*
  De-/Aktivierung optionaler Satellitenmodule (`teams`, `tournaments`, `cashbook`, `comms`) im Django Admin Panel über das Singleton-Modell `ModuleSettings` (ADR-019).
  *Design:* [ADR-019](../docs/decisions/ADR-019-modul-toggles-im-admin-panel.md). Reines Singleton-Modell in `core/models.py`, Fachlogik in `core/services.py:is_module_active`, URL-Schutz mit 404 über `ModulAktivMiddleware`, dynamische Filterung in `core/context_processors.py`, Kacheln im Dashboard dynamisch, Finanzbuchungs-Integrität in `dues` bleibt im Hintergrund unangetastet, AuditLog-Erfassung bei Einstellungsänderung.
  *Acceptance:* Superadmin/Vorstand kann Checkboxen im Admin (`/admin/core/modulesettings/`) ändern; inaktive Module verschwinden aus Navigation, Dashboard und Suche; direkte URL-Aufrufe inaktiver Module liefern 404; Reaktivierung stellt alle Daten sofort wieder her; Nicht-Admins werden im Admin abgewiesen (403); Änderung erzeugt AuditLog.
- [x] **T30b: Vereinshomepage als modulares Add-on (`homepage_aktiv`, ADR-023)** *(v1.1)*
  Klarstellung der Produktarchitektur: Hauptanwendung ist die Schachverwaltung, die Vereinshomepage ist ein de-/aktivierbares Satellitenmodul (`homepage_aktiv`).
  *Design:* [ADR-023](../docs/decisions/ADR-023-vereinshomepage-als-modul.md). Boolean-Feld `homepage_aktiv` in `ModuleSettings` (`core/models.py`), Fachservice-Routing in `core/services.py:is_module_active("homepage")`, URL-Schutz mit 404 für `/verein/` via `ModulAktivMiddleware`, intelligente Weiterleitung bei `/` (eingeloggte Nutzer -> Dashboard, Gäste -> Login), Ausblenden von *„Vereinsseite“* in `core/context_processors.py`, Entkopplung von Kacheln im Dashboard, Auswahlkarte im Onboarding-Wizard Schritt 2 (`step_2_modules.html`), AuditLog-Protokollierung.
  *Acceptance:* Vorstand kann `homepage_aktiv` im Admin und im Onboarding an-/abwählen; bei `homepage_aktiv=False` leitet `/` angemeldete Nutzer zum Dashboard und Gäste zum Login; `/verein/` antwortet mit 404; die Menüoption *„Vereinsseite“* verschwindet; bei `homepage_aktiv=True` ist die öffentliche Homepage regulär erreichbar; Reaktivierung stellt alle Views wieder her.
  *Verify:* `pytest core/tests/test_module_toggles.py` — **Negativtest:** `/verein/` liefert 404 bei deaktivierter Homepage; unbefugter Gast auf `/` wird zur Login-Seite weitergeleitet. · *Files:* `core/models.py`, `core/services.py`, `core/views.py`, `core/middleware.py`, `core/context_processors.py`, `core/forms_onboarding.py`, `core/templates/core/onboarding/step_2_modules.html`, `core/templates/core/dashboard*.html`, `core/tests/test_module_toggles.py` · *Größe:* S · *PRD:* S7.4 · *Release:* v1.1 · *Deps:* T30
- [x] **T30c: Marketing-Site-Routing auf schachverwaltung.de (`IS_MARKETING_SITE`, ADR-024)** *(v1.1)*
  Zwei-Welten-Routing für SaaS-Vertrieb vs. Vereinsbetrieb: Auf der Haupt-Marketingdomain (`schachverwaltung.de`) oder bei `IS_MARKETING_SITE=True` rendert `/` direkt die Produkt-Landingpage; auf Vereins-Subdomains oder Vereinsinstallationen verbleibt `/` auf der Vereinsinstanz. `/produkt/` leitet mit HTTP 301 permanent auf `/` um.
  *Design:* [ADR-024](../docs/decisions/ADR-024-marketing-site-routing-schachverwaltung-de.md). Reiner Fachservice `core.services.is_marketing_site`, Konfigurationsvariablen `IS_MARKETING_SITE` und `PRODUCT_HOSTS` in `config/settings.py` und `.env.prod.example`, Weiche in `core/views.py:home`, permanenter 301-Redirect in `core/views.py:produkt_redirect`.
  *Acceptance:* Zugriff auf `/` via `schachverwaltung.de` oder bei `IS_MARKETING_SITE=True` liefert die Produktseite (200); Zugriff via Vereins-Subdomain liefert die Vereinsseite (oder Login); `/produkt/` leitet mit HTTP 301 permanent auf `/` weiter.
  *Verify:* `pytest core/tests/test_produkt.py` — **Negativtest:** Vereins-Subdomain liefert keine Verkaufssätze auf der Startseite; Hostname-Erkennung greift isoliert; `/produkt/` leitet per 301 um. · *Files:* `config/settings.py`, `.env.prod.example`, `core/services.py`, `core/views.py`, `core/urls.py`, `core/tests/test_produkt.py` · *Größe:* S · *PRD:* S7.4 · *Release:* v1.1 · *Deps:* T30, T30b
- [x] **T31: Vereins-Setup & Onboarding-Tool (Web & CSV-Import)** *(v1.1)*
  Zentrales Onboarding- und Verwaltungstool für den Vorstand im Browser (`/verein/setup/`) und per CLI (`import_members`), um echte Vereinsdaten nach dem Deployment (z. B. auf Scalingo) in die Datenbank einzupflegen (ADR-020).
  *Design:* [ADR-020](../docs/decisions/ADR-020-vereinsstammdaten-in-der-datenbank.md). Singleton-Modell `ClubProfile` in `core/models.py` mit Fallback auf Django-Settings; reiner Fachservice `members.services.import_service` für Parsing, Encoding-Erkennung (UTF-8, Latin-1), Validierung und verschlüsselte SEPA-Mandatsanlage (Fernet); dünne Function-Based Views mit `@role_required(ADMIN_GROUP)` für Profil, Beitragskategorien, Mannschaften und CSV-Import inklusive Muster-Download und Dry-Run-Vorschau; AuditLog-Erfassung.
  *Acceptance:* Vorstand kann über `/verein/setup/` Stammdaten (Name, Spielabendzeiten, SEPA-Gläubiger) in der DB speichern; Templates und Kontextprozessoren spiegeln DB-Werte sofort wider; Mitglieder-CSV lässt sich prüfen (Vorschau mit Fehleranzeige) und fehlerfrei importieren; SEPA-Mandate werden mit verschlüsselter IBAN erzeugt; Nicht-Admins erhalten 403.
- [x] **T32: django-import-export im Django Admin (Mitglieder & Kassenbuch)** *(v1.1)*
  Standardisierter Import und Export für `Member` und `CashEntry` direkt im Django Admin Panel über `django-import-export` (ADR-021).
  *Design:* [ADR-021](../docs/decisions/ADR-021-django-import-export-im-admin.md). Ressourcen `MemberResource` (`members/resources.py`) und `CashEntryResource` (`cashbook/resources.py`), Foreign-Key-Widget für Beitragskategorien über den Namen, Vorbelegung von `erfasst_von` und `_changed_by`, `clean_model_instances = True` für strenge Modell-Validierung, Deaktivierung von Lösch-Rechten (`has_delete_permission = False`), automatische AuditLog-Protokollierung bei jedem Export und Import.
  *Acceptance:* Vorstand kann im Django-Admin Mitglieder und Kassenbuchungen als CSV/TSV/JSON exportieren und neue Datensätze importieren; Statusänderungen werden historisiert; unbefugte Rollen erhalten 302/403; ungültige Daten werden abgewiesen; Löschen bleibt unmöglich; AuditLog erfasst Aktionen.
  - [x] **T33: Operative Exzellenz, Spieltags-Workflows & Design-Hebel** *(v1.1)*
  Umsetzung der 8 strategischen Hebel für Vereinspraxis und Design:
  1. *F1 (Beiträge):* 1-Klick-SEPA-Sammelverbuchung nach Banklauf mit Kassenbucheintrag und AuditLog (`dues.services.sepa_sammelverbuchung`, `/beitraege/lauf/<jahr>/sepa-verbuchen/`).
  2. *F2 & D3 (Mannschaften):* Druckfertiger A4-Spielberichtsbogen (`/spiele/<pk>/drucken/`) mit Aufstellung, Einzelergebnissen und Unterschriftsfeldern sowie 1-Klick-WhatsApp-Ticker-Kopierer.
  3. *D1 (Ergebniserfassung):* Touch-Pills am Brett (≥ 44×44 px nach WCAG 2.5.5) mit Sofort-Autosave statt fummeliger Dropdowns.
  4. *F3 & D3 (Turniere):* A4-Rundenaushang für das Schwarze Brett am Spielabend (`/turniere/verwalten/<pk>/runden/<nr>/drucken/`).
  5. *F4 (Mitglieder):* Persönlicher iCal-Kalender-Abonnement-Feed (`/mitglieder/kalender/<token>.ics`) für individuelle Spielereinsätze mit manipulationssicherem Signatur-Token (`TimestampSigner`).
  6. *F5 (Mitglieder):* Smart-Filter & Schnellauswahl-Badges (U18, Senioren, ohne Kategorie, ohne SEPA-Mandat).
  7. *D2 & D4 (Design):* Klassisch-schachliche Serif-Typografie (`--display`), tabellarische Ziffern (`tabular-nums`) für Tabellen und DWZ, WCAG AAA-Kontraste.
  8. *D3 (Print-Engine):* Systemweite `@media print`-Optimierung für sauberen A4-Druck.
  *Verify:* `pytest dues/tests/test_sepa_sammelverbuchung.py teams/tests/test_match_print.py tournaments/tests/test_round_print.py members/tests/test_personal_calendar.py members/tests/test_member_filters.py` — **Negativtests:** 403-Checks für unberechtigte Rollen, Signatur-Manipulation im Token, Status-Validierung. · *Files:* `dues/`, `teams/`, `tournaments/`, `members/`, `static/css/app.css` · *Größe:* M · *Release:* v1.1 · *Deps:* T8, T9, T16, T17, T19, T20

- [x] **T34: Demo-Daten-Steuerung im Django Admin Panel (Ein/Aus, S7.6, ADR-022)** *(v1.1)*
  Webbasierte Steuerung für das Laden und sichere Entfernen von Beispieldaten direkt im Django Admin Panel (`/admin/core/demodata/`).
  *Design:* [ADR-022](../docs/decisions/ADR-022-demo-daten-steuerung-im-admin-panel.md). Reine Fachfunktionen in `core/services.py` (`get_demo_data_status`, `install_demo_data`, `remove_demo_data`), Proxy-Modell `DemoData` in `core/models.py`, `DemoDataAdmin` in `core/admin.py`, benutzerfreundliches Admin-Template mit Statuskarten, Bestätigungs-Checkbox, Revisionssicherheit via `AuditLog` und Schutz vor versehentlichem Löschen echter Produktivdaten.
  *Acceptance:* Vorstand/Superadmin kann Demo-Daten mit einem Klick erzeugen und sicher wieder entfernen; Versuch des Löschens bei Vorhandensein echter Daten wird verweigert; unbefugte Rollen (Mitglied, Kapitän) werden mit 302/403 abgewiesen; jede Aktion wird im AuditLog protokolliert; Dark/Light Mode barrierefrei nach WCAG 2.1 AA.
  *Verify:* `pytest core/tests/test_admin_demodata.py` — **Negativtests:** Nicht-Staff abgewiesen, Löschen ohne Checkbox abgewiesen, Löschen bei echten Daten verweigert. · *Files:* `core/services.py`, `core/models.py`, `core/admin.py`, `templates/admin/core/demodata/change_list.html`, `core/tests/test_admin_demodata.py` · *Größe:* S · *Release:* v1.1 · *Deps:* T2, T5, T30

**Checkpoint Final (v1):** Alle PRD-Erfolgskriterien durchgegangen, DSGVO-Checkliste abgehakt, NFR-Nachweis (T25b) abgelegt, Traceability-Tabelle abgeglichen, Berechtigungsmatrix (§3.8) gegen die Tests geprüft, Abnahme durch den Vorstand. Checkliste: `docs/abnahme.md`. **Danach erst v1.1-Tasks:** T7b, T9b, T9c, T15b, T16b, T18, T22, T24b, T29, T30, T31, T32, T33.

## Release-Schnitt

- **v1 (Kern — alle M-Anforderungen):** T1–T14 (inkl. T10b, T11b, T12), T16, T17, T19, T20, T23, T24, T25, T25b, T27
- **v1.1 (S-Anforderungen — erst nach v1-Abnahme):** T9c SEPA-XML-Export, T15 Kassenbuch, T15b Storno Kassenbuch, T16b iCal-Feed, T18 Tabellen/Buchholz, T21 Paarung, T22 Turnierexport, T24b Monitoring, T26 2FA, T26b Brute-Force/Dev-Toolbar, T28 öffentliche Designsprache, T29 DSB- / DWZ-Synchronisation (K3.6), T30 Modul-Toggles (S7.4), T31 Vereins-Setup (S7.5/S1.7), T32 Admin Import/Export (M1.5/S1.7/S6.2), T33 Operative Hebel & Print/Touch-Design, T34 Demo-Daten-Steuerung (S7.6)
- **Nacharbeit aus v1, die die Abnahme blockiert:** T7b (Jahresbeträge), T9b (Storno Zahlungen), T11b (Kassenbericht), T12 (Zugriffsprotokoll), T24 (verschlüsseltes Backup)
- **Out of scope (K):** nuLiga-Mutations-Export / TRF16 (ADR-016 Säule 3), SMS/Erinnerungen (K5.4), DATEV (K6.3)

**Traceability-Check (bei jedem Checkpoint):** Jede M- und N-ID aus `docs/prd.md` ist genau einer Task zugeordnet — v1-Task, außer N1.6 (2FA) und N2.8 (Monitoring), die im PRD als S geführt werden und daher T26 bzw. T24b (v1.1) zugeordnet sind. T10b ist reine Technik ohne PRD-ID.

| PRD-ID | Task |
|---|---|
| M1.1–M1.6 | T3 (Stammdaten/Liste/CSV), T2 (Rollen), T4 (Selbstbedienung) |
| M2.1 / M2.2 / M2.3 / M2.4 / M2.5 / M2.6 | T7 (+T7b) / T8 / T9 (+T9b) / T9 / T10 / T11b |
| S2.7 | T9c *(v1.1 / ADR-017)* |
| M3.1 / M3.2 / M3.3 | T19 / T19 / T20 |
| M4.1 / M4.2 / M4.3 / M4.4 | T16 / T16 / T17 / T17 |
| S4.6 | T16b *(v1.1)* |
| M5.1 / M5.2 | T13 / T14 |
| M7.1 / M7.2 / M7.3 | T6 + T11 / T1 + T2 / T5 |
| S7.4 | T30 *(v1.1 / ADR-019)* |
| S7.5 / S1.7 | T31 *(v1.1 / ADR-020)* |
| S7.6 | T34 *(v1.1 / ADR-022)* |
| N1.1 | T24 (Hoststandort + kein CDN/Tracker) |
| N1.2 / N1.3 / N1.4 | T23 |
| N1.5 | T5 (Logins/Änderungen) + T12 (Detail-Zugriffe) |
| N1.6 | T26 + T26b *(v1.1 — im PRD als S geführt)* |
| N1.7 | T19 |
| N2.1 / N2.4 | T24 |
| N2.2 / N2.3 | T25b + T26b |
| N2.8 | T24b *(v1.1 — im PRD als S geführt)* |
| N2.5 | T25 |
| N2.6 / N2.7 | T1 / T27 |
| S9.1–S9.4 | T28 *(v1.1)* |
| K3.6 | T29 *(v1.1 / ADR-016)* |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Django unbekannt beim Nutzer | Med | Admin-first-Ansatz, `docs/wartung.md`, keine exotischen Packages |
| Schweizer Paarung bei > 64 Spielern zu einfach | Med | `pairing.py` ist bewusst klein; Grenze dokumentieren, Referenz-Tests mit bekanntem Turnierdatensatz, Umstieg auf bbpPairings als möglicher Nachfolger (eigene ADR dann) |
| E-Mail-Zustellung selbst gehostet (SPF/DKIM) | Med | Versandprotokoll; Provider-/Zusteller-Doku (SPF, DKIM, DMARC) in `docs/deployment.md`; `config.production` verweigert den Start mit Console-Backend |
| Umfang zu groß für eine Session | Med | **v1/v1.1-Split:** v1 = alle M-Tasks, v1.1 = S-Tasks erst nach Abnahme; Checkpoints nach je 3–5 Tasks |
| Datenverlust auf Vereinsserver | Hoch | T24: verschlüsselte Backups (restic) + dokumentierter Restore-Test inkl. Entschlüsselung — **offen**, das aktuelle Backup ist nur komprimiert |
| DSGVO-Anforderung („Zugriffe") unvollständig umgesetzt | Med | T12 protokolliert Detailansichten; N1.5 definiert „Zugriff" konkret; Audit-Logs ≥ 12 Monate; Berechtigungsmatrix §3.8 mit Negativtests je Zeile |
| Finanzdaten werden doch gelöscht | Hoch | T9b (Zahlungen) und T15b (Kassenbuch) erzwingen Gegenbuchung statt Löschung; `test_rollen.py` und `test_audit.py` sichern die Verbote ab |
| NFRs (Performance, WCAG, Updatepfad) behauptet, aber nie gemessen | Med | T25b misst die 5 Kernflächen auf der Zielhardware und schreibt Messwert/Methodik/Datum in `docs/nfr-pruefung.md`; T24 testet den Updatepfad |
| Gastdaten (Name/E-Mail aus Turnieranmeldung) als Personendaten Dritter übersehen | Med | N1.7 definiert Zweck, Sichtbarkeit und Löschfrist; T19 prüft explizit, dass Gastdaten in Mitgliedersuche/-listen nicht auftauchen |
| Rollenleck im Dashboard (Kapitän sieht Finanzdaten) | Hoch | T6: Der Kapitän bekommt eine eigene Dashboard-Fassung, die Finanzwerte werden in der View gar nicht geladen; `KapitaenDashboardTests` prüft Kontext **und** Ausgabe |

## Open Questions

- SMTP-Zugangsdaten des Vereins — vor dem ersten Gruppenmailversand (in der Entwicklung Django-Console-Backend)
- ~~Exakte Beitragssätze und Kategorien des Vereins~~ — Struktur steht (Kategorien mit Platzhalterbeträgen, per Admin überschreibbar). Offen bleibt das **Eintragen der echten Sätze vor dem ersten Produktiv-Beitragslauf** und die Frage der Jahresbeträge (T7b).
- Domain/Hostname für das Deployment — vor T24
- Aufbewahrungsfristen mit Steuerberater bestätigen — Default 36 Monate bis Anonymisierung, 8 Jahre anonymisierte Finanzhistorie nach § 147 AO
- Schlüsselverwaltung für die IBAN-Verschlüsselung: Wo liegt der Fertnet-Schlüssel im Prod-Betrieb (Secret-Datei neben `.env.prod`, nicht im Repo, nicht auf dem DB-Host), und wie wird er rotiert? Grundsatz steht in [ADR-010](../docs/decisions/ADR-010-iban-verschluesselt-in-der-datenbank.md), die Betriebsentscheidung ist offen.
