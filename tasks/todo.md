# Fortschrittsprotokoll: Schachvereins-Software

**Statusquelle ist `tasks/plan.md`** — dort stehen die Checkboxen. Diese Datei protokolliert nur *abgeschlossene* Tasks mit Verifikationsbelegen und nennt die nächsten Schritte. Vollständige Akzeptanzkriterien: `tasks/plan.md` · Spezifikation: `docs/prd.md`

**Release-Schnitt:** v1 = alle M-Tasks · v1.1 = alle S-Tasks erst nach v1-Abnahme

---

## Erledigt

### Phase 1: Fundament

- **T1: Projekt-Scaffold + Docker** — Django-Projekt, `core`-App, Postgres, Compose, Basis-Template mobile-first ab 360 px. *Beleg:* `docker compose up` + `pytest` + Screenshot-Check 360/768/1280 px.
- **T2: Auth, Rollen, Navigation** — Gruppen `admin/kapitaen/mitglied`, rollenbasierte Menüs, Passwort-Reset. *Beleg:* `pytest core/tests/test_access.py`, `test_nav.py` — 403/Redirect-Tests je Rolle, Menüs je Rolle.
- **T3: Mitgliederstammdaten + Admin + Liste/Filter** — Modell `Member` mit Statushistorie, Admin-Liste/Suche, Detailseite, CSV-Export, kein Hard-Delete. *Beleg:* `pytest members/`; 403 für Rolle „mitglied" auf fremder Detailseite.
- **T4: Selbstbedienung + Änderungswunsch-Workflow** — Mitglied reicht Wunsch ein, Admin gibt frei/lehnt ab; Freigabe schreibt den Wert plus Audit-Eintrag. *Beleg:* `members/tests/test_selfservice.py`, Workflow im Browser durchklickt.
- **T5: Audit-Log + Login-Protokoll** — Signale für Stammdaten-Änderungen (Wer/Was/Wann + Alt/Neu) sowie Login/Logout/Abweisung mit IP; Admin-Ansicht löst Fremdschlüssel-IDs in Namen auf, ohne N+1 (Lookup-Tabelle einmal je Seitenaufruf). *Beleg:* `core/tests/test_audit.py` — Audit-Einträge weder anleg- noch änder- noch löschbar.
- **Checkpoint 1** — Rollen-Flow im Browser durchklickt: Menüs je Rolle, 403-Negativtest, Wunsch → Freigabe → Audit-Eintrag mit Alt/Neu, Login-/Logout-Protokoll mit IP.

### Phase 2: Beiträge + Dashboard

- **T6: Dashboard-Gerüst** — `/dashboard/` in drei Fassungen: Vorstand (alle Kennzahlen inkl. Finanzen), Kapitän (nur Spielbetrieb, **keine** Finanzwerte), Mitglied (eigene Beiträge, Einsätze, Termine, News). *Beleg:* `core/tests/test_dashboard.py` mit `KapitaenDashboardTests` — prüft Ausgabe *und* Kontext, dass für den Kapitän weder `uebersicht` noch `offene_posten` noch `kasse` noch `letzte_aktivitaeten` geladen werden. Nav-Badges zählen offene Wünsche, Entwürfe, offene Posten, Mahnungen, laufende Turniere.
- **T7: Beitragssätze** — `FeeCategory` mit Betrag am Datensatz, `Member.beitragskategorie` nullable, Kategorie-CRUD mit Löschschutz bei Vergabe. *Beleg:* `dues/tests/test_beitraege.py::test_kategorie_toggle_und_loeschschutz`; Negativtests negativer Betrag, ausgetretenes Mitglied mit Kategorie. **Abweichung:** ADR-004 (Jahresbetrag je Kategorie) ist nicht umgesetzt → T7b.
- **T8: Beitragslauf** — idempotenter Jahreslauf (`beitragslauf` in `dues/services.py`), Beitragsposten mit Momentaufnahme des Betrags, UI `/beitraege/lauf/` per POST. *Beleg:* `test_lauf_erzeugt_nur_fuer_aktive_mit_kategorie`, `test_lauf_ist_idempotent`; Negativtests 403 für Mitglieder/Kapitäne (ohne Posten-Erzeugung), POST-only, Mitglied ohne Kategorie wird übersprungen statt mit 0 € gebucht.
- **T9: SEPA-Mandate + Zahlungserfassung** — `SepaMandate` (Referenz/Datum/Status/Kontoinhaber), `Payment` je Posten mit Zahlungsart, jede Zahlung erzeugt eine Kassenbuchung in derselben Transaktion, Status aus den Zahlungen (unbezahlt/teilbezahlt/bezahlt/Gutschrift). Kein Bank-API-Zugriff ([ADR-002](../docs/decisions/ADR-002-kein-automatisierter-sepa-einzug.md)), IBAN verschlüsselt statt Klartext ([ADR-010](../docs/decisions/ADR-010-iban-verschluesselt-in-der-datenbank.md)). *Beleg:* `test_teilzahlung_setzt_status_und_bucht_kasse`, `test_vollzahlung_schliesst_posten`, `test_zahlung_validiert_betrag`, `test_ajax_zahlung_aktualisiert_zeile`, `dues/tests/test_keine_bank_api.py`, `dues/tests/test_rollen.py`. **Offen:** Storno per Gegenbuchung fehlt → T9b.
- **T10: Mahnwesen + Beitrags-Export** — Stufe streng +1 (max. 2), `DunningLetter` je Stufe, `mahnung_erfassen`/`mahntext` im Service, Mahnbrief als druckbares HTML, CSV-Export der Jahresbeiträge mit BOM und `;`. *Beleg:* `test_mahnung_erhoeht_stufe_bis_zwei`, `test_bezahlter_posten_kann_nicht_gemahnt_werden`, `test_mahnbrief_ist_druckbar`; Negativtests 403 für Kapitän/Mitglied auf Übersicht, Brief, Export und POST (jeweils ohne Seiteneffekt), zwei Exporte identisch.
- **T10b: Interaktionen ohne Neuladen** — in anderer Form umgesetzt: eigenes Vanilla-JS (`static/js/app.js`) statt HTMX/Alpine, [ADR-011](../docs/decisions/ADR-011-eigenes-javascript-statt-htmx.md) löst [ADR-008](../docs/decisions/ADR-008-htmx-alpine-lokal.md) ab. AJAX-Fragmente für Mahnung, Zahlung und Kategorie-Toggle; jedes Formular funktioniert ohne JavaScript als POST. *Beleg:* `test_ajax_mahnung_und_uebersicht`, `test_ajax_zahlung_aktualisiert_zeile`, `test_ajax_lauf_meldet_ergebnis`.
- **T11: Dashboard-Erweiterung offene Beiträge** — offene Summe, Anzahl, Fortschrittsbalken aus `jahres_uebersicht(jahr)`. *Beleg:* `test_kennzahlen_im_kontext`, `test_offene_posten_werden_aufgelistet`, `test_zahlung_reduziert_offenen_betrag`.
- **Berechtigungsmatrix Beitragswesen** — `dues/tests/test_rollen.py` neu: Übersicht, Beitragslauf, Export, Kategorien, Mandate, Mahnwesen, Mahnung setzen, Mahnbrief, Zahlung, Postendetail jeweils 200 für Admin und 403 für Kapitän und Mitglied; `mein_konto` nur mit eigenen Daten; ein abgelehnter Zugriff erzeugt weder Zahlung noch Mahnabschlag. Damit ist jede Zeile der Matrix für das Beitragswesen mit einem Negativtest belegt.
- **Checkpoint 2** — Beitragslauf-Jahr komplett durchgespielt (Lauf → Zahlung → Mahnung → Export), Dashboard zeigt echte Zahlen.

### Phase 3: Kommunikation

- **T13: News/Ankündigungen + öffentliche Startseite** — `NewsPost` mit Entwurf/veröffentlicht, öffentliche Startseite zeigt nur Veröffentlichtes, Archiv, Admin-CRUD. *Beleg:* `comms/tests/test_news.py` — Entwurf für Gast weder in Liste noch auf Detail, Nicht-Admin 403.
- **T14: E-Mail-Versand an Gruppen** — Opt-in-Flag je Mitglied, Gruppenversand, Versandprotokoll (An, Wann, Status). *Beleg:* `comms/tests/test_mail.py` — Opt-out-Mitglied erhält keine Mail, Nicht-Admin 403, leere Gruppe bricht mit Meldung ab.
- **Checkpoint 3** — News veröffentlicht + Test-Mail im Nur-Test-Modus.

### Phase 4: Spielbetrieb

- **T16: Mannschaften + Ligaspiele** — `Team` mit Kapitän, `LeagueMatch` mit Status und Ergebnis. *Beleg:* `teams/tests/test_spielbetrieb.py` — 403 für Mitglieder beim Anlegen/Bearbeiten, abgeschlossene Spiele nicht mehr änderbar.
- **T17: Aufstellung + Einzelergebnisse** — `LineupEntry`, Ergebnis je Brett, Live-Brettpunkte, Aufstellung ohne JavaScript speicherbar. *Beleg:* `teams/tests/test_spielbetrieb.py` — Kapitän darf aufstellen, Kapitän einer anderen Mannschaft und Mitglied nicht.
- **Checkpoint 3b** — Testspiel komplett (Aufstellung → Ergebnis).

### Phase 4b: Turniere

- **T19: Turnier-Modell + öffentliche Anmeldung** — öffentliche Detailseite, Anmeldung als Mitglied oder Gast, Anmeldeschluss, Teilnehmerliste. *Beleg:* `tournaments/tests/test_turniere.py` — Anmeldung nach Anmeldeschluss abgewiesen, Gastdaten erscheinen nicht in der Mitgliederliste/-suche.
- **T20: Runden + Ergebniserfassung + Zwischenwertung** — Runden, Ergebnisse je Partie, Zwischenstand mit Buchholz. *Beleg:* `tournaments/tests/test_turniere.py` — Ergebnisänderung nur für Turnierverwalter, Doppelpartien abgewiesen, nur letzte Runde löschbar.
- **T21: Schweizer Paarung** — `tournaments/pairing.py` mit Buchholz-Paarung, Bye-Handling, Farbausgleich, Wiederholungsvermeidung, idempotent je Rundennummer. *Beleg:* Paarungs-Tests mit Referenzrechnung; Negativtest Spielerzahl ohne Bye-Regel.
- **Checkpoint 4** — Testturnier über 3 Runden gespielt.

### Phase 5: DSGVO & Betrieb

- **T23: DSGVO-Auskunfts-Export + Löschfristen** — Auskunft je Mitglied als HTML, PDF (reportlab) und JSON; `anonymize_former_members` mit `--dry-run` und konfigurierbarer Frist; Verzeichnis der Verarbeitungstätigkeiten als CSV. HTML- und PDF-Export werden im `AuditLog` protokolliert, der JSON-Export noch nicht → gehört zu T12. *Beleg:* `core/tests/test_dsgvo.py`, `test_dsgvo_quellen.py` — Dry-Run ändert nichts, nach Anonymisierung ist die Namenssuche leer, die Finanzhistorie intakt.
- **T25: Härtung** — Sicherheits-Header-Middleware (nosniff, X-Frame-Options, Referrer-Policy, Permissions-Policy, COOP, CSP wenn `DEBUG=0`), Fehlerbenachrichtigung per E-Mail an `DJANGO_ADMINS`, Argon2 als erster Hasher, `config/production.py` (verweigert Dev-Secret-Key und Console-Mail-Backend), `docs/wartung.md`. *Beleg:* `core/tests/test_haertung.py`, `config/tests/test_production_settings.py` — inklusive der Prüfung, dass `docker-compose.prod.yml` `DJANGO_SETTINGS_MODULE=config.production` setzt und die Vorlage dieselbe Mail-Variable nutzt wie die Settings.
- **T26: 2FA für die Vorstandsgruppe** — TOTP als Eigenimplementierung in `core/twofa.py`, `TwoFactorDevice`, erzwungen über `TWOFA_PFLICHT`. *Beleg:* `core/tests/test_haertung.py` — Admin-Login ohne gültiges Token abgewiesen, Token außerhalb des Zeitfensters nicht akzeptiert, andere Rollen ohne 2FA.
- **T27: PWA** — Manifest, Service Worker (Precache Offline + Statics, Network-First für Pages), iOS-Meta-Tags, Icons, `tools/generate_icons.py`. *Beleg:* `core/tests/test_pwa.py` + DevTools „Add to home screen".
- **T28: Öffentliche Designsprache (Referenz-ZIP)** — Designsprache der nächsten Design-Referenz auf den öffentlichen Teil portiert: neues `static/css/site.css`, Hüllen `public_base.html`/`auth_base.html`, Startseite (Hero, Wochenband, Kennzahlen, News, Ligatermine, Turnierbühne, Mitmachen), Aktuelles mit Kategoriefilter, Artikelansicht mit Sidebar, Turnierkalender + Turnierdetail mit Anmeldung, Beitragsseite, **neue Seite `/verein/`** (Selbstverständnis, Zeiten, Ligaspielplan), 404, Offline und der Anmeldeeinstieg (Login, 2FA, Passwort-Reset). Alle Inhalte aus den vorhandenen Modellen, Vereinsprofil aus den Settings (ADR-012); interne Seiten bleiben unverändert ([ADR-013](../docs/decisions/ADR-013-oeffentliche-designsprache.md), [Spec](../docs/superpowers/specs/2026-09-30-oeffentliche-designsprache.md)).
  *Beleg:* `pytest core/tests/test_oeffentliches_design.py` (22 Tests) — jede im öffentlichen Bereich verwendete Klasse ist in `site.css` definiert, öffentliche Templates laden weder `app.css` noch `landing.css`, kein externes Asset im HTML, Kategoriefilter und Turnieranmeldung geprüft. **Negativtests:** unbekannte Kategorie versteckt nichts, Entwürfe bleiben verborgen, nicht öffentliches Turnier bleibt 404, geschlossene Anmeldung zeigt kein Formular, ohne gepflegte Vereinsdaten keine erfundenen Angaben.
  *Weitere Belege:* vollständiger Lauf `pytest` → **334 Tests grün** (1 Skip nur mit PostgreSQL, 172 Subtests), `manage.py check` ohne Befund; alle internen Links (22) und Assets (9) der öffentlichen Seiten liefern 200; HTML-Tag-Balance aller öffentlichen Seiten geprüft; mobiles Menü automatisiert getestet (öffnen/schließen, `aria-expanded`, Icon-Wechsel, `Escape`, Klick außerhalb) bei 0 JS-Fehlern.
  *Trennung:* die öffentlichen Hüllen laden `static/js/public.js` (Mobilmenü, Ladebalken, Toasts, Service Worker); das interne `app.js` bleibt Dashboard und Verwaltung vorbehalten. Beide Tests und ADR-013 halten das fest.
- **T15: Kassenbuch** — `CashEntry` mit Kategorie, Betrag, Belegnummer, Jahresfilter, Jahresabschluss, CSV-Export. *Beleg:* `cashbook/tests/test_kasse.py` — 403 für Nicht-Admin, CSV-Summe stimmt fürs gefilterte Jahr. **Offener Mangel:** `cashbook:entry_delete` löscht Buchungen hart → T15b.

### Zusammenführung der Zweige (2026-09-29)

- `origin/master` enthielt eine zweite, konkurrierende Umsetzung derselben Phasen (T1–T23 in der Zählung des Ursprungszweigs). Beide Seiten wurden zu einem Baum zusammengeführt; die Implementierung folgt der umfassenderen Fassung (`MembershipFee`/`DunningLetter`, `teams`, `tournaments`, `comms`, `cashbook`, DSGVO, 2FA, PWA, Deployment).
- **Aufgelöste Konflikte:** Code-Dateien aus `config/`, `core/`, `dues/`, `members/`, `static/css/` zugunsten des Ursprungszweigs, mit drei Ausnahmen: `AuditLog.anzeige_wert()` wurde übernommen (Fremdschlüssel-IDs als Namen, ohne N+1), das Design-System `static/css/app.css` bleibt handgeschrieben, und `README.md`/`.gitignore` wurden vereinigt.
- **Entfernt, weil der Produktcode nicht mehr existiert:** `dues/export.py`, `dues/mahnung.py`, die Templates `posten_liste.html`/`mahnliste.html`, die Migrationen `dues/0002…0005`, `members/0003_member_beitragskategorie`, die App `verein/` (Vereinsdaten kommen jetzt aus den Settings, [ADR-012](../docs/decisions/ADR-012-vereinsprofil-in-den-settings.md)), die Tailwind-Pipeline (`package.json`, `src/tailwind.css`, `static/css/tailwind.css`) sowie 9 Testmodule der früheren `dues`-Linie. Deren Regelwerk ist in `dues/tests/test_beitraege.py` und neu in `dues/tests/test_rollen.py` abgedeckt; der Bank-API-Garantietest `dues/tests/test_keine_bank_api.py` aus [ADR-002](../docs/decisions/ADR-002-kein-automatisierter-sepa-einzug.md) ist bewusst erhalten geblieben.
- **Zwei Fehler aus dem Ursprungszweig gefunden und behoben:**
  1. Der Kapitän bekam die vollständige Finanzübersicht des Vorstands (offene Beiträge, Zahlungen im Monat, Beitragsposten mit Namen und Mahnstufe, Beitrags-CSV, Kassenabschluss, Audit-Protokoll) — Verstoß gegen PRD §3.8. Die View lädt diese Daten für den Kapitän jetzt gar nicht erst, das Dashboard hat eine eigene Kapitän-Fassung.
  2. `docker-compose.prod.yml` startete `config.settings` statt `config.production`, sodass der Dev-Fallback-Secret-Key greifen konnte; zusätzlich las `config/production.py` eine andere Mail-Variable als `settings.py` und `.env.prod.example`. Beides korrigiert und mit Tests abgesichert.
- **Neu entschieden:** Die IBAN wird nicht im Klartext gespeichert, sondern verschlüsselt — das löst die IBAN-Sperre aus [ADR-002](../docs/decisions/ADR-002-kein-automatisierter-sepa-einzug.md) teilweise ab; die **Bank-API-Sperre bleibt**. Siehe [ADR-010](../docs/decisions/ADR-010-iban-verschluesselt-in-der-datenbank.md). *Umsetzung:* `dues/crypto.py` (Fernet, Präfix `v1:` für Rotation), `dues/fields.py` (`VerschluesseltesIbanField`), Migration `dues/0002_iban_verschluesselt` (Bestand einmalig umgeschrieben), `iban_kurz` als nicht umkehrbares Feld für Listen, `IBAN_FERNET_KEY` Pflicht in `config/production.py`. *Beleg:* `dues/tests/test_iban_verschluesselung.py` (8 Tests) — kein Klartext in der Datenbank, Maske im Klartext für Listen, zwei Verschlüsselungen derselben IBAN sind verschieden, ohne Schlüssel bricht der Zugriff ab, falscher Schlüssel meldet sich und lässt die Daten unverändert; Dev-Datenbank geprüft: `dues_sepamandate.iban` enthält nur `v1:`-Chiffretext.
- **Beleg:** `docker compose exec app pytest` → 288 Tests grün, 98 Subtests; `manage.py check` ohne Befund; `makemigrations --check` ohne offene Migration.
- **Browser-Check (PRD N2.6, 360 px und 1280 px, echter Browser):** Bei der Sichtprüfung fiel auf, dass das Dashboard bei 360 px um 201 px nach rechts scrollte. Ursache war kein Template, sondern das Stylesheet: `grid-template-columns: 1fr` lässt die minimale Spaltenbreite zu `min-content` werden, wodurch `.table-wrap { overflow-x: auto }` gar nicht greift. Behoben durch `minmax(0, 1fr)` in `.grid*` und `.form-grid*` plus `min-width: 0` für die Kinder von `.main-side`. Danach ohne horizontalen Overflow: Dashboard (Vorstand, Kapitän, Mitglied), Beiträge, Kategorien, Mandate, Mahnwesen, Kassenbuch und Jahresabschluss, Ligaspiele, Ligatabellen, Turniere, Ankündigungen, E-Mail-Versand, Audit-Protokoll, Mitgliederliste und Mitgliederdetail, Suche – jeweils bei 360 px und 1280 px. Zwei weitere Seiten fielen auf: die Mandatsliste zeigt nur maskierte IBAN (`DE24 •••• •••• 0004`), der Kapitän-Dashboard-Kopf nennt nur Spielbetrieb.
- **Nebenbei:** `docker-compose.yml` (Entwicklung) setzt jetzt `TWOFA_PFLICHT=0`, wie es die README für die lokale Vorführung schon beschrieben hat.

---

## Nächste Schritte

Reihenfolge und Akzeptanzkriterien stehen in `tasks/plan.md`. V1-relevant (blockiert die Abnahme):

1. [T12](plan.md) Zugriffsprotokoll Detailansicht — schließt die letzte Lücke bei N1.5 und protokolliert zusätzlich den JSON-Export
2. [T24](plan.md) Deployment: Backup verschlüsseln (restic), Restore-Test durchführen, EU/DE-Nachweis — N2.1 ist heute nicht erfüllt
3. [T9b](plan.md) Storno von Zahlungen per Gegenbuchung — schließt ADR-006 für Zahlungen
4. [T7b](plan.md) Jahresbeträge je Kategorie — holt ADR-004 nach
5. [T11b](plan.md) Kassenbericht Beiträge — schließt M2.6
6. [T25b](plan.md) NFR-Nachweis auf der Zielhardware, WCAG-Durchgang, `docs/nfr-pruefung.md`
7. [T28](plan.md) öffentlicher Teil — umgesetzt; offen bleiben nur die echten Vereinsfotos und das **interne Design** (Dashboard/Verwaltung), das separat geliefert wird
8. **Abnahme** durch den Vorstand gegen `docs/abnahme.md`

**Danach (v1.1):** T15b · T16b · T18 · T22 · T24b

---

## Noch offen (Blocker, keine Designfragen)

- **Beitragssätze und Kategorien des Vereins** — vor dem ersten echten Beitragslauf im Django-Admin unter *Dues → Beitragskategorien* eintragen. Platzhalter kommen aus `seed_demo`.
- **Verschlüsselungsschlüssel für die IBAN** — für den Produktivbetrieb erzeugen und neben `.env.prod` ablegen, getrennt vom DB-Host; nie ins Repo.
- SMTP-Zugangsdaten — vor dem ersten Gruppenmailversand (in der Entwicklung Django-Console-Backend)
- Domain/Hostname — vor T24
- Aufbewahrungsfristen mit Steuerberater bestätigen — Default 36 Monate bis Anonymisierung, 8 Jahre anonymisierte Finanzhistorie nach § 147 AO
