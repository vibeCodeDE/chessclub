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
- **T7: Beitragssätze** — `FeeCategory` (Name, Beschreibung, aktiv), `Member.beitragskategorie` nullable, Kategorie-CRUD mit Löschschutz bei Vergabe. *Beleg:* `dues/tests/test_beitraege.py::test_kategorie_toggle_und_loeschschutz`; Negativtests negativer Betrag, ausgetretenes Mitglied mit Kategorie.
- **T7b: Jahresbeträge je Kategorie** — Schließt [ADR-004](../docs/decisions/ADR-004-beitragssaetze-kategorie-und-betrag-getrennt.md) ab: Trennung von Kategorie und Jahresbetrag über `FeeAmount` (Kategorie × Jahr × Betrag, `UniqueConstraint`). `beitragslauf` nimmt den Satz des Laufjahrs; fehlt für eine aktive Beitragskategorie ein Satz, bricht der Lauf per `ValidationError` ab und legt atomar **nichts** an. Migration `dues/0004` überführte bestehende Sätze, `FeeCategoryAdmin` bindet `FeeAmountInline` ein, `FeeCategoryForm` und `seed_demo` pflegen Jahresbeträge. *Beleg:* `pytest dues/tests/test_beitraege.py::JahresbetraegeTests` (5 Tests: 2026/2027 getrennt gepflegt, Änderung von 2027 lässt 2026 unberührt; Negativtests: Lauf ohne Satz bricht ab und legt nichts an, negativer Betrag abgewiesen, doppelter Satz abgewiesen, ausgetretenes Mitglied mit Kategorie abgewiesen).
- **T8: Beitragslauf** — idempotenter Jahreslauf (`beitragslauf` in `dues/services.py`), Beitragsposten mit Momentaufnahme des Betrags, UI `/beitraege/lauf/` per POST. *Beleg:* `test_lauf_erzeugt_nur_fuer_aktive_mit_kategorie`, `test_lauf_ist_idempotent`; Negativtests 403 für Mitglieder/Kapitäne (ohne Posten-Erzeugung), POST-only, Mitglied ohne Kategorie wird übersprungen statt mit 0 € gebucht.
- **T9: SEPA-Mandate + Zahlungserfassung** — `SepaMandate` (Referenz/Datum/Status/Kontoinhaber), `Payment` je Posten mit Zahlungsart, jede Zahlung erzeugt eine Kassenbuchung in derselben Transaktion, Status aus den Zahlungen (unbezahlt/teilbezahlt/bezahlt/Gutschrift). Kein Bank-API-Zugriff ([ADR-002](../docs/decisions/ADR-002-kein-automatisierter-sepa-einzug.md)), IBAN verschlüsselt statt Klartext ([ADR-010](../docs/decisions/ADR-010-iban-verschluesselt-in-der-datenbank.md)). *Beleg:* `test_teilzahlung_setzt_status_und_bucht_kasse`, `test_vollzahlung_schliesst_posten`, `test_zahlung_validiert_betrag`, `test_ajax_zahlung_aktualisiert_zeile`, `dues/tests/test_keine_bank_api.py`, `dues/tests/test_rollen.py`.
- **T9b: Storno von Zahlungen per Gegenbuchung** — `Payment.storno_von` (Selbstbezug), Gegenbuchung mit negativem Betrag und Verweis auf Originalzahlung, Statusaktualisierung des Beitragspostens, Kassenstorno in derselben Transaktion, Audit-Eintrag mit Actor. Kein Hard-Delete, Löschfunktion im Django-Admin gesperrt. *Beleg:* `pytest dues/tests/test_beitraege.py` (`test_storno_vollzahlung_setzt_posten_und_kasse_zurueck`, `test_storno_teilzahlung_setzt_status_auf_teilweise`, `test_storno_ueber_route_und_doppelstorno_schutz`), `dues/tests/test_rollen.py`.
- **T10: Mahnwesen + Beitrags-Export** — Stufe streng +1 (max. 2), `DunningLetter` je Stufe, `mahnung_erfassen`/`mahntext` im Service, Mahnbrief als druckbares HTML, CSV-Export der Jahresbeiträge mit BOM und `;`. *Beleg:* `test_mahnung_erhoeht_stufe_bis_zwei`, `test_bezahlter_posten_kann_nicht_gemahnt_werden`, `test_mahnbrief_ist_druckbar`; Negativtests 403 für Kapitän/Mitglied auf Übersicht, Brief, Export und POST (jeweils ohne Seiteneffekt), zwei Exporte identisch.
- **T10b: Interaktionen ohne Neuladen** — in anderer Form umgesetzt: eigenes Vanilla-JS (`static/js/app.js`) statt HTMX/Alpine, [ADR-011](../docs/decisions/ADR-011-eigenes-javascript-statt-htmx.md) löst [ADR-008](../docs/decisions/ADR-008-htmx-alpine-lokal.md) ab. AJAX-Fragmente für Mahnung, Zahlung und Kategorie-Toggle; jedes Formular funktioniert ohne JavaScript als POST. *Beleg:* `test_ajax_mahnung_und_uebersicht`, `test_ajax_zahlung_aktualisiert_zeile`, `test_ajax_lauf_meldet_ergebnis`.
- **T11: Dashboard-Erweiterung offene Beiträge** — offene Summe, Anzahl, Fortschrittsbalken aus `jahres_uebersicht(jahr)`. *Beleg:* `test_kennzahlen_im_kontext`, `test_offene_posten_werden_aufgelistet`, `test_zahlung_reduziert_offenen_betrag`.
- **T11b: Kassenbericht Beiträge (Jahresübersicht)** — Reine Lese-Sicht auf Beitragszahlungen je Mitglied für ein gewähltes Jahr, Jahressumme der Beitragseinnahmen, offene Posten zum Stichtag sowie CSV-Export (PRD M2.6). *Beleg:* `pytest dues/tests/test_kassenbericht.py` (4 Tests) — 10 Mitglieder / 8 Zahlungen → genau 8 Zeilen, Jahressumme entspricht berechneter Modellsumme, leeres Jahr zeigt Hinweistext („keine Buchungen") statt 0-€-Zeilen, CSV-Export summiert identisch zur Anzeige; Negativtests in `dues/tests/test_rollen.py` (403 für Rolle „mitglied" und „kapitaen" auf Sicht und Export).
- **Berechtigungsmatrix Beitragswesen** — `dues/tests/test_rollen.py`: Übersicht, Beitragslauf, Export, Kassenbericht, Kassenbericht-Export, Kategorien, Mandate, Mahnwesen, Mahnung setzen, Mahnbrief, Zahlung, Postendetail jeweils 200 für Admin und 403 für Kapitän und Mitglied; `mein_konto` nur mit eigenen Daten; ein abgelehnter Zugriff erzeugt weder Zahlung noch Mahnabschlag. Damit ist jede Zeile der Matrix für das Beitragswesen mit einem Negativtest belegt.
- **T12: Zugriffsprotokoll Detailansicht** — Protokollierung des Aufrufs einer Mitglieder-Detailansicht (sowohl Frontend als auch Django-Admin `change_view`), Protokollierung aller DSGVO-Exporte (HTML, PDF, JSON); `AuditLogQuerySet.aufbewahrungsfrist_abgelaufen(tage=365)` und Property `aufbewahrungsfrist_abgelaufen` auf `AuditLog` für 12-Monats-Aufbewahrungsfrist (PRD N1.5). *Beleg:* `pytest members/tests/test_views.py`, `pytest core/tests/test_dsgvo.py`, `pytest core/tests/test_audit.py` — Negativtests: Listenansicht erzeugt keinen Lese-Eintrag, Rollen „mitglied" und „kapitaen" erhalten 403 auf Detail und alle Auskunfts-Exporte ohne AuditLog-Seiteneffekt.
- **Checkpoint 2** — Beitragslauf-Jahr komplett durchgespielt (Lauf → Zahlung → Mahnung → Export → Kassenbericht), Dashboard zeigt echte Zahlen.

### Phase 3: Kommunikation

- **T13: News/Ankündigungen + öffentliche Startseite** — `NewsPost` mit Entwurf/veröffentlicht, öffentliche Startseite zeigt nur Veröffentlichtes, Archiv, Admin-CRUD. *Beleg:* `comms/tests/test_news.py` — Entwurf für Gast weder in Liste noch auf Detail, Nicht-Admin 403.
- **T14: E-Mail-Versand an Gruppen** — Opt-in-Flag je Mitglied, Gruppenversand, Versandprotokoll (An, Wann, Status). *Beleg:* `comms/tests/test_mail.py` — Opt-out-Mitglied erhält keine Mail, Nicht-Admin 403, leere Gruppe bricht mit Meldung ab.
- **Checkpoint 3** — News veröffentlicht + Test-Mail im Nur-Test-Modus.

### Phase 4: Spielbetrieb

- **T16: Mannschaften + Ligaspiele** — `Team` mit Kapitän, `LeagueMatch` mit Status und Ergebnis. *Beleg:* `teams/tests/test_spielbetrieb.py` — 403 für Mitglieder beim Anlegen/Bearbeiten, abgeschlossene Spiele nicht mehr änderbar.
- **T16b: iCal-Feed der Ligaspiele** — Abonnierbarer Kalender-Feed (`.ics`) nach RFC 5545 für jede Mannschaft einzeln sowie global für alle Ligaspiele; Zugriff über geheime Token-URLs ohne Login; Admin kann Tokens erneuern (macht alte Links sofort ungültig); reine Feed-Generierungsfunktion in `teams/services.py`; abgesagte Spiele werden mit `STATUS:CANCELLED` ausgegeben; keine Personen- oder Aufstellungsdaten im Feed (PRD S4.6). *Beleg:* `pytest teams/tests/test_spielbetrieb.py::ICalFeedTests` (8 Tests: Team-Feed enthält nur Team-Spiele, Gesamtfeed enthält alle, Negativtest: 404 bei ungültigem/fehlendem Token ohne Information Leak, Datenschutztest: keine Mitglieds-/Aufstellungsdaten, `STATUS:CANCELLED` für abgesagte Spiele, Token-Erneuerung invalidiert alte Links, 403 für Nicht-Admin bei Token-Erneuerung, `assertNumQueries` genau 2 für Feeds).
- **T17: Aufstellung + Einzelergebnisse** — `LineupEntry`, Ergebnis je Brett, Live-Brettpunkte, Aufstellung ohne JavaScript speicherbar. *Beleg:* `teams/tests/test_spielbetrieb.py` — Kapitän darf aufstellen, Kapitän einer anderen Mannschaft und Mitglied nicht.
- **T18: Tabellenberechnung inkl. Buchholz** — Automatische Ligatabellenberechnung nach Mannschaftspunkten, Brettpunkten und Buchholz-Wertung (Summe der Mannschaftspunkte aller gespielten Gegner) als Tiebreak (PRD S4.5). Darstellung der Buchholz-Spalte in `tabelle_list.html`, `match_detail.html` und `team_detail.html`. *Beleg:* `pytest teams/tests/test_spielbetrieb.py::TabellenTests` (5 Tests: 4 Mannschaften × 3 Spiele mit bekanntem Referenzergebnis, Buchholz-Tiebreak bei gleichen Mannschafts- und Brettpunkten, Negativtest: ungespielte/geplante/aufgestellte/abgesagte Spiele fließen nicht in die Tabelle ein, HTML-Rendering mit Buchholz-Spalte).
- **Checkpoint 3b** — Testspiel komplett (Aufstellung → Ergebnis).

### Phase 4b: Turniere

- **T19: Turnier-Modell + öffentliche Anmeldung** — öffentliche Detailseite, Anmeldung als Mitglied oder Gast, Anmeldeschluss, Teilnehmerliste. *Beleg:* `tournaments/tests/test_turniere.py` — Anmeldung nach Anmeldeschluss abgewiesen, Gastdaten erscheinen nicht in der Mitgliederliste/-suche.
- **T20: Runden + Ergebniserfassung + Zwischenwertung** — Runden, Ergebnisse je Partie, Zwischenstand mit Buchholz. *Beleg:* `tournaments/tests/test_turniere.py` — Ergebnisänderung nur für Turnierverwalter, Doppelpartien abgewiesen, nur letzte Runde löschbar.
- **T21: Schweizer Paarung** — `tournaments/pairing.py` mit Buchholz-Paarung, Bye-Handling, Farbausgleich, Wiederholungsvermeidung, idempotent je Rundennummer. *Beleg:* Paarungs-Tests mit Referenzrechnung; Negativtest Spielerzahl ohne Bye-Regel.
- **T22: Turnierexport im ChessResults-Format** — Export nach ChessResults-/Swiss-Manager-Struktur mit Abschnitten `[TRN]` (Turnier-Metadaten), `[ARB]` (Organisation/Schiedsrichter) und `[RAN]` (Rangliste und Rundenergebnisse `R1...Rn`), Semikolon-Trennzeichen, UTF-8-BOM und Kennungen `TRN`/`ARB`/`RAN`. A4-optimierte Druckansicht mit `@page { size: A4 portrait }` und Tabellenformatierung (PRD S3.5). *Beleg:* `pytest tournaments/tests/test_turniere.py` (23 Tests: Strukturprüfung `[TRN]`/`[ARB]`/`[RAN]`, deterministischer Export; Negativtests: 403 für Nicht-Admin [Kapitän, Mitglied] und Redirect für Gäste auf Export und Druckansicht; Datenschutzprüfung: keine privaten Kontaktdaten/E-Mails/Notizen in der CSV).
- **Checkpoint 4** — Testturnier über 3 Runden gespielt.

### Phase 5: DSGVO & Betrieb

- **T24: Deployment + Backup + Restore-Doku** — Caddy TLS-Reverse-Proxy (`Caddyfile`, auto TLS, Reverse-Proxy auf `app:8000`, direktes Ausliefern von `/static/*`, Security-Header), verschlüsseltes nächtliches `pg_dump`-Backup per OpenSSL AES-256-CBC PBKDF2 (`tools/backup.sh`), Wiederherstellungsskript (`tools/restore.sh`) mit Pflichtprüfung des Schlüssels und `--check-only`-Vorabprüfung ohne Datenbankänderung, `docker-compose.prod.yml` mit Caddy-, App-, DB- und Backup-Diensten, `.env.prod.example` um `BACKUP_ENCRYPTION_KEY` ergänzt, `docs/deployment.md` mit EU/DE-Standortnachweis (PRD N1.1, Hetzner/Netcup), Restore-Anleitung, Restore-Testprotokoll (< 4 h) und Updatepfad (PRD N2.1, N2.4). *Beleg:* `pytest config/tests/test_deployment.py` (11 Tests: Compose-Struktur, Caddyfile, Pflichtvariablen, Dokumentation, bitgenaue Entschlüsselung, Negativtests: fehlender Schlüssel bricht ab, falscher Schlüssel bricht mit Fehler 2 ab, korrupte/unvollständige Backup-Dateien werden vor jeglicher DB-Änderung abgewiesen).
- **T25: Härtung** — Sicherheits-Header-Middleware (nosniff, X-Frame-Options, Referrer-Policy, Permissions-Policy, COOP, CSP wenn `DEBUG=0`), Fehlerbenachrichtigung per E-Mail an `DJANGO_ADMINS`, Argon2 als erster Hasher, `config/production.py` (verweigert Dev-Secret-Key und Console-Mail-Backend), `docs/wartung.md`. *Beleg:* `core/tests/test_haertung.py`, `config/tests/test_production_settings.py` — inklusive der Prüfung, dass `docker-compose.prod.yml` `DJANGO_SETTINGS_MODULE=config.production` setzt und die Vorlage dieselbe Mail-Variable nutzt wie die Settings.
- **T26: 2FA für die Vorstandsgruppe** — TOTP als Eigenimplementierung in `core/twofa.py`, `TwoFactorDevice`, erzwungen über `TWOFA_PFLICHT`. *Beleg:* `core/tests/test_haertung.py` — Admin-Login ohne gültiges Token abgewiesen, Token außerhalb des Zeitfensters nicht akzeptiert, andere Rollen ohne 2FA.
- **T26b: Brute-Force-Schutz (django-axes) und Dev-Tooling (django-debug-toolbar, django-extensions)** — Brute-Force-Schutz nach 5 Fehlversuchen mit 1 Stunde Sperre und barrierefreier deutscher Sperrseite (`core/lockout.html`) gemäß [ADR-015](../docs/decisions/ADR-015-brute-force-schutz-und-dev-profiling.md). Entwicklungs-Profiling mit `django-debug-toolbar` (N+1-Query-Prüfung, SQL-Budgets) aktiv bei `DEBUG=True`, vollständig abgeschaltet in Produktion (`DEBUG=False`). Entwicklungs-Tools via `django-extensions` (`shell_plus`, `show_urls`, `validate_templates` mit 0 Syntaxfehlern). 2FA-Vervollständigung unterstützt explizites Auth-Backend. *Beleg:* `pytest core/tests/test_axes_and_toolbar.py` (8 Tests: regulärer Login erfolgreich, 4 Fehlversuche mit Fehler, 5. Fehlversuch sperrt den Zugang mit HTTP 429 und Lockout-Template [Negativtest], erfolgreicher Login setzt Zähler zurück, Debug-Toolbar in Produktion 404 [Negativtest], Toolbar-Callback prüft `DEBUG` und schließt AJAX-Fragmente aus, Extensions-Befehle registriert, Extensions in Produktion nicht aktiv [Negativtest]); Gesamtlauf `pytest` → **425 passed, 210 subtests passed** (100% grün).
- **T27: PWA** — Manifest, Service Worker (Precache Offline + Statics, Network-First für Pages), iOS-Meta-Tags, Icons, `tools/generate_icons.py`. *Beleg:* `core/tests/test_pwa.py` + DevTools „Add to home screen".
- **T28: Öffentliche Designsprache (Referenz-ZIP)** — Designsprache der nächsten Design-Referenz auf den öffentlichen Teil portiert: neues `static/css/site.css`, Hüllen `public_base.html`/`auth_base.html`, Startseite (Hero, Wochenband, Kennzahlen, News, Ligatermine, Turnierbühne, Mitmachen), Aktuelles mit Kategoriefilter, Artikelansicht mit Sidebar, Turnierkalender + Turnierdetail mit Anmeldung, Beitragsseite, **neue Seite `/verein/`** (Selbstverständnis, Zeiten, Ligaspielplan), 404, Offline und der Anmeldeeinstieg (Login, 2FA, Passwort-Reset). Alle Inhalte aus den vorhandenen Modellen, Vereinsprofil aus den Settings (ADR-012); interne Seiten bleiben unverändert ([ADR-013](../docs/decisions/ADR-013-oeffentliche-designsprache.md), [Spec](../docs/superpowers/specs/2026-09-30-oeffentliche-designsprache.md)).
  *Beleg:* `pytest core/tests/test_oeffentliches_design.py` (25 Tests) — jede im öffentlichen Bereich verwendete Klasse ist in `site.css` definiert, öffentliche Templates laden weder `app.css` noch `landing.css`, kein externes Asset im HTML, Kategoriefilter und Turnieranmeldung geprüft. **Negativtests:** unbekannte Kategorie versteckt nichts, Entwürfe bleiben verborgen, nicht öffentliches Turnier bleibt 404, geschlossene Anmeldung zeigt kein Formular, ohne gepflegte Vereinsdaten keine erfundenen Angaben.
  *Weitere Belege:* vollständiger Lauf `pytest` → **334 Tests grün** (1 Skip nur mit PostgreSQL, 172 Subtests), `manage.py check` ohne Befund; alle internen Links (22) und Assets (9) der öffentlichen Seiten liefern 200; HTML-Tag-Balance aller öffentlichen Seiten geprüft; mobiles Menü automatisiert getestet (öffnen/schließen, `aria-expanded`, Icon-Wechsel, `Escape`, Klick außerhalb) bei 0 JS-Fehlern.
  *Trennung:* die öffentlichen Hüllen laden `static/js/public.js` (Mobilmenü, Ladebalken, Toasts, Service Worker); das interne `app.js` bleibt Dashboard und Verwaltung vorbehalten. Beide Tests und ADR-013 halten das fest.
- **T15: Kassenbuch** — `CashEntry` mit Kategorie, Betrag, Belegnummer, Jahresfilter, Jahresabschluss, CSV-Export. *Beleg:* `cashbook/tests/test_kasse.py` — 403 für Nicht-Admin, CSV-Summe stimmt fürs gefilterte Jahr.
- **T15b: Kassenbuch stornieren statt löschen** — Schließt [ADR-006](../docs/decisions/ADR-006-storno-per-gegenbuchung.md) für das Kassenbuch ab: `storniere_kassenbuchung` erzwingt Begründung und Actor, erzeugt Gegenbuchung mit Verweis und schreibt `AuditLog`. Löschroute `kasse/<pk>/loeschen/` und `entry_delete` entfernt (liefert 404). Frontend bietet Storno-Dialog mit Pflichtfeld für die Begründung; Django-Admin verbietet Löschaktionen. *Beleg:* `pytest cashbook/tests/test_kasse.py` (12 Tests: Storno stellt Saldo exakt wieder her, Doppelstornoschutz, Storno einer Gegenbuchung abgewiesen, stornierte Buchung nicht editierbar; Negativtests: `/loeschen/` liefert 404, Storno ohne Begründung abgewiesen, Storno ohne Actor abgewiesen, 403 für Nicht-Admin auf alle Routen, `has_delete_permission` im Admin ist `False`).

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

### Nachträglich übernommene Arbeit aus den Arena-Zweigen (2026-09-30)

- `arena/01a0ed6b-chessclub` („Sprachpflege") wurde geprüft und **verworfen**: der Cherry-Pick auf master war leer, alle Änderungen (CSV-Datum `dd.mm.yyyy` statt ISO, Formular-Label „Wunschwert", Audit-Aktionen „Anmeldung/Anmeldung abgelehnt", „Anmelde-Ereignisse", Prosa-Gedankenstriche) liegen bereits im Ursprungszweig.
- `arena/01a0ed14-chessclub` („Constraint & Soft-Delete-Garantie, Superuser-Rolle, Härtung") basierte auf einem alten Stand und wurde **nicht gemergt**, sondern Stück für Stück auf master übertragen, wo die Änderung noch fehlte:
  1. **Echter Fehler behoben:** `AuditLog.alt_wert`/`neu_wert` waren `CharField(max_length=200)`, während `Member.email` bis 254 Zeichen erlaubt – der Save wäre am Audit-Signal mit „value too long" gescheitert und die Stammdatenänderung wäre komplett verloren gegangen. Beide Felder sind jetzt `TextField`, Migration `core/0005_auditlog_werte_als_textfeld`. *Beleg:* `core/tests/test_audit.py` (Regressionsfall mit 254-Zeichen-E-Mail).
  2. **Zwei Konfigurationslücken geschlossen:** `.env.prod.example` dokumentiert `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` und `SECURE_SSL_REDIRECT`/`SECURE_HSTS_SECONDS` – `config/settings.py` bzw. `config/production.py` lasen davon nichts, SMTP lief also ohne Zugangsdaten und die Seite blieb über HTTP erreichbar. Beide werden jetzt gelesen. *Beleg:* `config/tests/test_email_settings.py::ProductionHardeningTests` – **Negativtests:** HSTS lässt sich abschalten, und ohne `IBAN_FERNET_KEY` wirft der Produktions-Import (ADR-010).
  3. **CI ergänzt:** `.github/workflows/ci.yml` (Ruff, `makemigrations --check`, `check --deploy`, Tests gegen Postgres 16). Zwei Lücken der übernommenen Fassung korrigiert: `POSTGRES_HOST` fehlte (die Tests wären auf SQLite gelaufen und hätten den `select_for_update`-Pfad nicht abgedeckt), und dem Deploy-Schritt fehlte `IBAN_FERNET_KEY` – `config/production.py` bricht ohne ihn beim Import ab. Variablennamen an `EMAIL_*` angeglichen (die Fassung des Zweigs nutzte `DJANGO_EMAIL_*`).
  4. **Hygiene:** `pyproject.toml` (Ruff-Konfiguration, `known-first-party` um alle acht Apps ergänzt), `requirements-dev.txt`, `.dockerignore` und `.gitignore` um Caches/Coverage ergänzt.
  5. **Bestandsschulden behoben:** `ruff check .` meldete 26 Befunde – 23 ungenutzte Importe, 3 unsortierte Importblöcke, 2 ungenutzte Schleifenvariablen, 1 toter Block in `tournaments/pairing.py`. Alle behoben, damit die neue CI grün ist. *Beleg:* `ruff check .` → `All checks passed!`
- **Verworfen:** `MemberQuerySet.delete()` (Soft-Delete auch für `queryset.delete()`), der partielle `UniqueConstraint` auf offene Wünsche und die Superuser-Rolle in `core/roles.py` – Feature-Arbeit aus einem überholten Zweigstand, der eigene Migrationen und andere Nummern mitbringt. Bewusst **nicht** übernommen; als eigene Task zu planen.
- **Beleg:** `docker compose exec app pytest` → 343 Tests grün, 172 Subtests; `ruff check .` ohne Befund; `makemigrations --check` ohne offene Migration; `check --deploy` mit gesetzten Pflichtvariablen ohne ERROR.

### T25b: NFR-Nachweis — Performance, Barrierefreiheit (WCAG 2.1 AA) und universelle Zugänglichkeit (2026-10-04)

- **Umsetzung:**
  1. `core/tests/test_a11y.py` erstellt (10 dedizierte automatisierte Tests für `lang="de"`, unblockiertes Viewport-Scaling bis 200 %, Skip-Links auf allen Hüllen, `:focus-visible` in allen Stylesheets, semantische HTML5-Landmarks, Überschriften-Hierarchie `<h1>`, ARIA-Attribute und Label-Zuordnung bei Formularen).
  2. Skip-Links (`.skip-link` in `app.css`, `site.css`) und IDs (`#main-content`, `#inhalt`, `#auth-card`) auf allen Hüllen (`base.html`, `public_base.html`, `auth_base.html`) durchgängig integriert.
  3. `docs/nfr-pruefung.md` als systematischer Prüfbericht mit Messwerten (alle 5 Kernflächen < 180 ms), Methodik, Kontrastwerten (Fließtext 11.8:1 / 14.1:1, AAA) und Responsive-Ergebnissen (360 px bis 4K) angelegt.
  4. `docs/prd.md` auf v1.6 aktualisiert mit geschärften Anforderungen für alle Generationen (Schüler bis Senioren 80+ Jahre).
### T29: DSB- / DWZ-Synchronisation und Drift Detection (2026-10-07)

- **Problem:** DWZ-Zahlen ändern sich laufend; Spielleiter mussten DWZ und ZPS-Passnummern manuell nachschlagen.
- **Umsetzung (gemäß ADR-016 / K3.6):**
  1. **Datenmodell (`Member`):** Bundeseinheitliche Verbandskennungen und Wertungszahlen ergänzt (`zps_nummer`, `pkz`, `dwz`, `dwz_index`, `fide_id`, `spielberechtigung`), Hilfseigenschaft `dwz_formatiert`, Migration `members/migrations/0005_member_dwz_member_dwz_index_member_fide_id_and_more.py`.
  2. **Fachservice (`members/services/dsb_sync.py`):** Reiner Service ohne HTTP-Kontext für den Abruf der offiziellen JSON-Schnittstelle des DSB-Wertungsportals (`https://www.schachbund.de/wertungsportal-api/vereinsliste`), 24-stündiges serverseitiges Caching (Ratenbegrenzung zum Schutz der Verbandsserver), standardkonforme Normalisierung und Matching-Logik (PKZ, ZPS, Name).
  3. **Diskrepanzerkennung (Drift Detection):** Systematischer Abgleich von Vereins- und Verbandsdaten (`detect_drift`):
     - *DWZ-Abweichungen:* automatische Erkennung veralteter DWZ/DWZ-Indizes.
     - *Fehlt im Verband:* im Verein aktive Mitglieder, die in der Verbandsliste fehlen (Portalmeldung ausstehend).
     - *Fehlt im Verein:* im Verband geführte Spieler, die im Verein fehlen oder als ausgetreten geführt werden.
     - *Status-Abweichungen:* Diskrepanzen zwischen Vereins- und Verbandsstatus (z. B. Verein aktiv vs. Verband passiv).
     - *Synchrone Mitglieder:* vollständig übereinstimmende Datensätze.
  4. **Wertungszahlen-Übernahme (`sync_dwz_from_report`, `sync_dwz_for_member`):** Idempotente Übernahme geänderter DWZ, Indizes und Kennungen per Einzel- oder Sammelaktion, AuditLog-Protokollierung mit Akteur und Detailwerten.
  5. **UI & Navigation:** Neue Verwaltungsfläche `/mitglieder/dsb-sync/` mit Tabs, Status-Kacheln und Schnellübernahme-Buttons, Verlinkung im Navigationsmenü und der Mitgliederliste, Anzeige von DWZ und Verbandsdaten im Mitgliederdetail und Admin.
- **Beleg:** `docker compose exec app pytest members/tests/test_dsb_sync.py` → 16 passed in 5.34s; `docker compose exec app pytest` → **444 passed, 210 subtests passed** in 38.00s (100% grün).

### T9c: SEPA-XML-Export (pain.008) für Beitragsläufe (2026-10-07)

- **Problem & Kontext:** Nach ADR-002 gibt es bewusst keine Bank-API (kein FinTS/EBICS), um Zugangsdaten und Risiken zu vermeiden. Das manuelle Abtippen von Dutzenden oder Hunderten Lastschriften im Online-Banking ist zeitintensiv und fehleranfällig.
- **Umsetzung (gemäß ADR-017 / S2.7):**
  1. **Standardisiertes SEPA-Format:** ISO 20022 `pain.008.001.02` (EPC SEPA Core Direct Debit, B2C, `RCUR`) mit vollständigem Group Header (`GrpHdr`), Zahlungsinformation (`PmtInf`), Gläubigeridentifikation (`CdtrSchmeId`) und Einzeltransaktionen (`DrctDbtTxInf`).
  2. **Fachservice (`dues/services.py`):** `erstelle_sepa_xml` und `sepa_sanitize` als reine Funktionen ohne HTTP-Abhängigkeit; XML-Generierung rein per Standardbibliothek (`xml.etree.ElementTree`) ohne Fremdpakete oder Netzwerkbibliotheken (ADR-002 und `test_keine_bank_api.py` garantiert eingehalten).
  3. **Kryptografie & DSGVO (ADR-010 / N1.5):** IBANs bleiben in der Datenbank Fernet-verschlüsselt; flüchtige Entschlüsselung ausschließlich im RAM während des Exports; lückenlose Protokollierung jedes Downloads im `AuditLog` (Aktion: `SEPA-XML-Export`) mit Jahr, Postenanzahl und Gesamtsumme ohne Klartext-IBANs.
  4. **Query-Effizienz & Filterung:** O(1)-Query-Budget via `select_related("member", "member__sepa_mandat")` und `prefetch_related("zahlungen")`. Posten ohne Mandat, mit widerrufenem Mandat, ohne offene Beträge oder im Status `bezahlt`/`erlassen` werden automatisch ausgeschlossen; bei Teilzahlungen wird nur der offene Restbetrag eingezogen.
  5. **UI & Konfiguration:** Dialog `#sepa-dialog` und Export-Button `SEPA-XML {jahr}` in `dues/templates/dues/overview.html`, Route `/beitraege/sepa-export.xml`, Gläubigereinstellungen `SEPA_CREDITOR_ID`, `SEPA_CREDITOR_IBAN`, `SEPA_CREDITOR_BIC` in `config/settings.py` und `.env.prod.example`.
- **Beleg:** `docker compose exec app pytest dues/tests/test_sepa_export.py dues/tests/test_rollen.py` → **25 passed, 39 subtests passed** in 4.14s; Gesamttestlauf `docker compose exec app pytest` → **454 passed, 213 subtests passed** in 37.94s (100% grün).

### T30: Modul-Toggles im Admin-Panel (2026-10-11)

- **Problem & Kontext:** Kleine Vereine und unterschiedliche Betriebsmodelle (ADR-014 Managed-Abo) benötigen Flexibilität, ungenutzte Satellitenmodule (`teams`, `tournaments`, `cashbook`, `comms`) auszublenden, ohne Daten oder Datenbank-Integrität zu gefährden. Dynamisches Entladen von Django-Apps aus `INSTALLED_APPS` scheidet aus.
- **Umsetzung (gemäß ADR-019 / S7.4):**
  1. **Singleton-Modell (`core/models.py`):** `ModuleSettings` (garantiert `pk=1`, `delete` unterbunden) mit Schaltern für `spielbetrieb_aktiv`, `turniere_aktiv`, `kassenbuch_aktiv`, `nachrichten_aktiv`. Kernmodule (`core`, `members`, `dues`) bleiben fest. Migration `core/migrations/0007_modulesettings.py`.
  2. **Fachservice (`core/services.py`):** Reine Funktionen `is_module_active` und `get_module_settings` mit Request-Caching für O(1)-Query-Budget.
  3. **URL-Schutz (`core/middleware.py`):** `ModulAktivMiddleware` prüft `resolver_match` und blockt inaktive Module mit HTTP 404.
  4. **Dynamische Navigation (`core/context_processors.py`):** Inaktive Menüpunkte und Sektionen werden ausgeblendet; Badges inaktiver Module werden gar nicht erst abgefragt. `module_settings` global im Template-Kontext verfügbar.
  5. **Admin & AuditLog (`core/admin.py`):** `ModuleSettingsAdmin` für den Vorstand/Superadmin im Django-Admin; jede Einstellungsänderung wird im `AuditLog` protokolliert.
  6. **UI- & Suchintegration:** Dashboard (`core/templates/core/dashboard*.html`), Vereinsseite und globale Suche (`core/views.py:suche`) berücksichtigen inaktive Module dynamisch.
  7. **Finanzintegrität:** Beitragszahlungen schreiben bei `kassenbuch_aktiv=False` im Hintergrund weiterhin unverändert den revisionssicheren `CashEntry` (ADR-005, ADR-006).
- **Beleg:** `pytest core/tests/test_module_toggles.py` sichert Singleton-Garantie, Admin-Berechtigungen (Negativtest für Nicht-Admin), Navigation, 404-URL-Sperren, Suchausblendung und Finanzintegrität ab.


### T24b: Monitoring mit Uptime Kuma (2026-10-11)

- **Problem & Kontext:** Für den Ausfallsicherheits- und Beobachtbarkeitsnachweis (PRD N2.8 / ADR-009) muss die Erreichbarkeit der Anwendung und das verlässliche Durchlaufen des täglichen verschlüsselten Datenbank-Backups lückenlos überwacht werden, ohne dass personenbezogene Daten nach außen dringen.
- **Umsetzung (gemäß ADR-009 / PRD N2.8):**
  1. **Container (`docker-compose.prod.yml`):** Service `uptime-kuma` (`louislam/uptime-kuma:1-alpine`) mit persistentem Volume `kuma_data:/app/data` hinzugefügt. Portbindung auf `127.0.0.1:3001:3001` beschränkt (Negativkriterium: kein offener Port nach außen ohne SSH-Tunnel/Login).
  2. **Backup-Push-Monitor (`tools/backup.sh`):** Push-Ping-Logik integriert (`$KUMA_PUSH_URL`). Nach jedem fehlerfreien, verschlüsselten Dump wird Uptime Kuma angepingt. Fehler beim Ping fangen graceful ab (`|| true`), damit das Backup niemals wegen eines Monitoring-Fehlers scheitert.
  3. **Konfiguration (`.env.prod.example`):** Variable `KUMA_PUSH_URL` für den Push-Endpunkt dokumentiert und in Compose an den Backup-Dienst durchgereicht.
  4. **Dokumentation (`docs/deployment.md`):** Abschnitt 7 vollständig überarbeitet mit Anleitungen für den sicheren Zugriff (SSH-Tunnel), HTTP-Healthcheck-Monitor (`http://app:8000/health/`), Backup-Push-Monitor, SMTP-Alarmierung und manueller Ausfallsimulation.
  5. **Automatisierte Absicherung (`config/tests/test_deployment.py`):** Tests für Compose-Services, Volumes, Port-Restriktion auf `127.0.0.1`, `KUMA_PUSH_URL`-Präsenz und Push-Logik in `tools/backup.sh`.
- **Beleg:** `pytest config/tests/test_deployment.py` → 12 passed in 0.78s; Gesamttestlauf `docker compose exec app pytest` → **481 passed, 213 subtests passed** in 43.67s (100% grün). `docker compose -f docker-compose.prod.yml config` syntaktisch valide.

### T31: Vereins-Setup & Onboarding-Tool (Web & CSV-Import) (2026-10-12)

- **Problem & Kontext:** Nach dem initialen Deployment (z. B. auf Scalingo) und Anlegen des Superusers fehlte eine barrierefreie Möglichkeit, das Vereinsprofil (Name, Anschrift, Spielabendzeiten, SEPA-Gläubiger-ID) in der Datenbank zu hinterlegen und echte Mitgliederdaten (aus Altsystemen oder Excel) zu importieren, statt Dummy-Daten zu nutzen (ADR-020).
- **Umsetzung (gemäß ADR-020, S7.5, S1.7):**
  1. **Singleton-Modell (`core/models.py`):** `ClubProfile` mit `pk=1`, Löschschutz und transparentem Fallback auf Django-Settings (`settings.CLUB_*`, `settings.SEPA_*`), falls Felder noch leer sind. Migration `core/migrations/0008_clubprofile.py`.
  2. **Fachservice (`members/services/import_service.py`):** Reine Funktionen `parse_members_csv` (Encoding-Erkennung UTF-8/Latin-1, Delimiter `;`/`,`), `validate_members_import` (Validierung von Pflichtfeldern, Datumsformaten, IBAN-Muster) und `execute_members_import` (atomare Anlage von `Member`, Fernet-verschlüsseltem `SepaMandate` und AuditLog).
  3. **Web-Interface (`/verein/setup/`):** Strukturierte Reiterführung mit `@role_required(ADMIN_GROUP)` für Profil & Stammdaten, Beitragskategorien, Mannschaften und geführten CSV-Import mit Vorschau, Fehlerhinweisen und Download einer CSV-Mustervorlage.
  4. **CLI-Command (`members/management/commands/import_members.py`):** Unterstützung für Skript- und One-Off-Container-Import (`--dry-run`).
  5. **Integration & Querschnitt:** Templates, Kontextprozessor (`core/context_processors.py`), Dashboard-Banner und SEPA-Export lesen vorrangig die Datenbank-Stammdaten.
- **Beleg:** `docker compose exec app pytest core/tests/test_club_profile.py members/tests/test_member_import.py` → **13 passed** in 6.13s; Gesamttestlauf `docker compose exec app pytest` → **511 passed, 239 subtests passed** in 34.82s (100% grün). Negative Rollentests (403 für Nicht-Admins) und Dry-Run-Integrität nachgewiesen.

### T32: django-import-export im Django Admin (Mitglieder & Kassenbuch) (2026-10-13)

- **Problem & Kontext:** Im Django-Admin fehlte eine standardisierte Möglichkeit für Vorstände, Mitgliederdaten und Kassenbuchungen flexibel als CSV/TSV/JSON zu exportieren und zu importieren (PRD M1.5, S1.7, S6.2, ADR-021).
- **Umsetzung (gemäß ADR-021):**
  1. **Abhängigkeit & Konfiguration:** `django-import-export>=4.0` in `requirements.txt` ergänzt, `"import_export"` in `INSTALLED_APPS` und `IMPORT_EXPORT_USE_TRANSACTIONS = True` in `config/settings.py`.
  2. **Ressourcen:**
     - `MemberResource` (`members/resources.py`): Export/Import aller relevanten Profil- und Verbandskennungen (`zps_nummer`, `dwz` etc.), `ForeignKeyWidget` für `FeeCategory` über den Kategorienamen, `clean_model_instances = True`, Übernahme des Benutzers (`_changed_by`) zur Historisierung von Statuswechseln (`MemberStatusChange`).
     - `CashEntryResource` (`cashbook/resources.py`): Abbildung von Einnahmen/Ausgaben und Storno-Gegenbuchungen, automatische Erfasser-Zuweisung (`erfasst_von`), `clean_model_instances = True` für Betrags- und Vorzeichenvalidierung.
  3. **Admin-Integration (`ImportExportModelAdmin`):** `MemberAdmin` und `CashEntryAdmin` um Import-/Export-Routen erweitert; Löschschutz (`has_delete_permission = False`) bleibt strikt intakt; Hooks `get_data_for_export()` und `process_result()` protokollieren jeden Export und Import automatisch im `AuditLog` (DSGVO N1.5).
### T33: Operative Exzellenz, Spieltags-Workflows & Design-Hebel (2026-10-13)

- **Problem & Kontext:** Analyse der Vereins-Workflows ergab operative Reibungspunkte: Nach einem SEPA-Banklauf mussten Beiträge einzeln als bezahlt markiert werden; am Spielabend fehlte ein normierter A4-Spielberichtsbogen zum Unterschreiben und ein schneller WhatsApp-Ticker; Ergebniseingabe auf Smartphones am Brett war per `<select>` fummelig; Aushang der Turnierrunden am Schwarzen Brett war unvollständig; Mitglieder hatten keinen personalisierten Kalender für ihre Einsätze; Mitgliederliste bot keine Schnellfilter (U18, Senioren, fehlendes Mandat/Kategorie); Typografie und A4-Druckbild waren noch nicht für den Vereinssaal optimiert.
- **Umsetzung (8 Hebel):**
  1. **F1 SEPA-Sammelverbuchung:** Atomare Funktion `sepa_sammelverbuchung` in `dues/services.py` mit Kassenbucheintrag und AuditLog; View `sepa_sammelverbuchung_view` in `dues/views.py` und Bestätigungs-Modal in `dues/templates/dues/overview.html`.
  2. **F2 Spielbericht A4 & WhatsApp-Ticker:** Druckfertige Ansicht `match_print` (`/spiele/<pk>/drucken/`) in `teams/views.py` und Template `teams/templates/teams/match_print.html` mit Aufstellung, Brettpunkten und Unterschriftenfeldern. WhatsApp-Ticker-Kopierbutton in `teams/templates/teams/match_detail.html`.
  3. **D1 Touch-Pills am Brett:** Mobile Radio-Touch-Pills (≥ 44×44 px nach WCAG 2.5.5) mit automatischem Autosave per JavaScript in `teams/templates/teams/match_detail.html`.
  4. **F3 Rundenaushang A4:** Ansicht `round_print` (`/turniere/verwalten/<pk>/runden/<nr>/drucken/`) in `tournaments/views.py` und Template `tournaments/templates/tournaments/round_print.html` für das Schwarze Brett am Spielabend.
  5. **F4 Persönlicher iCal-Feed:** Widerrufbares Zufallstoken `ical_token` auf `Member` (`Member.renew_ical_token`), ICS-Feed `personal_calendar_feed` (`/mitglieder/kalender/<token>.ics`), 1-Klick-Erneuerung `/profil/ical-token-erneuern/` im Mitgliederprofil mit AuditLog-Protokollierung (`members/templates/members/profil.html`).
  6. **F5 Mitglieder-Schnellfilter & Smart Badges:** Filter-Typen (U18, Senioren, ohne Kategorie, ohne SEPA-Mandat) und Zähler-Pills in `members/views.py` und `members/templates/members/member_list.html`.
  7. **D2 & D4 Typografie & Kontraste:** Klassische Serif-Schrift (`--display`), `font-variant-numeric: tabular-nums` für Tabellen/DWZ/Ergebnisse und WCAG AAA-Kontrastverbesserung in `static/css/app.css`.
  8. **D3 Systemweite Print-Engine:** `@media print`-Optimierung für sauberen A4-Druck ohne Header/Sidebar/Buttons in `static/css/app.css`.
### T34: Demo-Daten-Steuerung im Django Admin Panel (Ein/Aus, 2026-10-14)

- **Problem & Kontext:** Für Präsentationen und Vorführungen (z. B. auf Scalingo oder bei Vorständen ohne CLI-Zugriff) müssen Demo-Daten direkt im Browser erzeugt und wieder sauber entfernt werden können. Dabei muss sichergestellt sein, dass niemals versehentlich echte Vereinsdaten gelöscht werden und alle Vorgänge revisionssicher im `AuditLog` protokolliert werden (S7.6, ADR-022).
- **Umsetzung (gemäß ADR-022):**
  1. **Reine Fachlogik (`core/services.py`):**
     - `get_demo_data_status()`: Liefert Echtzeit-Metriken (Mitglieder, Beiträge, Mannschaften, Turniere, Kasse) und prüft über Heuristiken (`has_real_data`), ob echte Mitglieder oder Konten existieren.
     - `install_demo_data(user)`: Führt Seeding aus und protokolliert im `AuditLog`.
     - `remove_demo_data(user, confirm)`: Verlangt Checkbox-Bestätigung, verweigert Löschen bei erkannten Produktivdaten (`has_real_data`), leert bei reinem Demo-Bestand atomar die Daten und erfasst dies im `AuditLog`.
  2. **Admin-Integration:**
     - Proxy-Modell `DemoData` in `core/models.py` (Migration `core/0009_demodata.py`).
     - `DemoDataAdmin` in `core/admin.py` mit `change_list_template = "admin/core/demodata/change_list.html"`.
     - Schnelleinstieg über den Header in `templates/admin/base_site.html`.
     - `--clear`-Option in `core/management/commands/seed_demo.py` ergänzt.
  3. **UI & Barrierefreiheit:**
     - Dashboard mit Statuskarten, Kennzahlen, Demo-Zugangsdaten (`vorstand`, `kassenwart`, `kapitaen`, `mitglied` / `schach2026`).
     - Zwei getrennte Aktionen: Grüner Button „Demo-Daten jetzt laden“ und roter Button „Demo-Daten entfernen“ mit Sicherheits-Checkbox und Sperre bei echten Daten.
     - Tabelle der letzten Audit-Einträge mit horizontalem Scroll-Wrapper für 360 px Responsive-Design.
- **Beleg:** `docker compose exec app pytest core/tests/test_admin_demodata.py core/tests/test_seed_demo.py` → **15 passed**; Gesamttestlauf `docker compose exec app pytest` → **555 passed, 239 subtests passed** in 49.11s (100% grün). Negativtests: Nicht-Staff abgewiesen (302/403), Löschen ohne Checkbox abgewiesen, Löschen bei echten Daten verweigert.

---

### T30b: Vereinshomepage als modulares Add-on (`homepage_aktiv`, ADR-023)
- **Problem & Kontext:** Klarstellung der Produktarchitektur: Hauptanwendung ist die Schachverwaltung, die Vereinshomepage ist ein de-/aktivierbares Satellitenmodul (`homepage_aktiv`).
- **Umsetzung (gemäß ADR-023):**
  - Boolean-Feld `homepage_aktiv` in `ModuleSettings` (`core/models.py`).
  - Fachlogik `is_module_active("homepage")` in `core/services.py`.
  - URL-Schutz mit 404 für `/verein/` über `ModulAktivMiddleware`.
  - Intelligente Weiterleitung bei `/`: Eingeloggte Nutzer zum Dashboard, Gäste zum Login bei inaktiver Homepage.
  - Dynamisches Ausblenden von „Vereinsseite“ in `core/context_processors.py`.
  - Auswahlkarte im Onboarding-Wizard Schritt 2 (`step_2_modules.html`).
- **Beleg:** `docker compose exec app pytest core/tests/test_module_toggles.py` → **passed**; Negativtest: `/verein/` liefert 404 bei deaktivierter Homepage.

---

### T30c: Marketing-Site-Routing auf schachverwaltung.de (`IS_MARKETING_SITE`, ADR-024)
- **Problem & Kontext:** Zwei-Welten-Routing für SaaS-Vertrieb vs. Vereinsbetrieb: Auf der Haupt-Marketingdomain (`schachverwaltung.de`) oder bei `IS_MARKETING_SITE=True` rendert `/` direkt die Produkt-Landingpage (`/produkt/`); auf Vereins-Subdomains oder Vereinsinstallationen verbleibt `/` auf der Vereinsinstanz.
- **Umsetzung (gemäß ADR-024):**
  - Reiner Fachservice `core.services.is_marketing_site()`.
  - Konfigurationsvariablen `IS_MARKETING_SITE` und `PRODUCT_HOSTS` in `config/settings.py` und `.env.prod.example`.
  - Routing-Weiche in `core/views.py:home`.
- **Beleg:** `docker compose exec app pytest core/tests/test_produkt.py` → **passed**; Negativtest: Vereins-Subdomain liefert keine Verkaufssätze auf der Startseite.

---

### T30d: Schmerzpunkte, Lösungen & Interaktive Vorschau auf `/produkt` (Feature 003)
- **Problem & Kontext:** Interessierte Vereinsvorstände und Funktionäre möchten auf der Landingpage sofort verstehen, wie die Software ihre akuten Vereinsprobleme löst. Abstrakte Funktionslisten reichen nicht aus – gefragt ist eine zielgruppengenaue Ansprache je Vereinsrolle inklusive erlebbarer Vorschau.
- **Umsetzung:**
  - Modulare Inhaltsdatenstruktur `ROLLEN_SCHMERZPUNKTE` in `core/produkt.py` für 5 Rollen (`vorstand`, `kassenwart`, `spielleiter`, `kapitaen`, `mitglieder`) mit je 3 konkreten Vorher/Nachher-Paaren, Zeiteinsparung und Mockup-Konfiguration.
  - View-Weitergabe in `core/views.py:produkt_seite` an `core/templates/core/produkt.html`.
  - Interaktive CSS `:checked` Radio-Tab-Architektur (`.lp-pains-showcase`) mit Live-Umschaltung ohne JavaScript oder Fremdbibliotheken (0 Tracker, 0 Cookies, strikte CSP, Progressive Enhancement).
  - Interaktiver UI-Mockup-Simulator (`.lp-mock-interactive`) im App-Fensterstil mit Status-Pills, Kennzahlen-Kacheln und schaltbaren Arbeitsabläufen.
  - Zeiteinsparungs-Badges je Rolle und aggregierter Gesamtnutzen-Banner („Bis zu 80 Stunden weniger Büroarbeit pro Saison“).
  - Rollenbezogene Demo-Anfrage-Schaltflächen mit vorbefülltem Betreff (`mailto:...?subject=Demo-Anfrage...`).
- **Beleg:** `docker compose exec app pytest core/tests/test_produkt.py` (27 passed, 38 subtests passed) sowie Gesamtsuite `docker compose exec app pytest` (614 passed, 256 subtests passed); Negativtests auf ungültige Rollen und strikte CSP; Browser-Prüfung ohne horizontalen Overflow bei 360 px und 1280 px.

---

### T35: Automatische Dateisystem-Bereinigung mit django-cleanup (ADR-026)
- **Problem & Kontext:** Beim Ersetzen oder Löschen von Django-Modellinstanzen mit Dateianhängen (`FileField`/`ImageField`) verbleiben physische Dateien standardmäßig auf der Festplatte. Das führt zu Speicherlecks und widerspricht dem DSGVO-Grundsatz der Datenminimierung und Speicherbegrenzung (Art. 5 DSGVO).
- **Umsetzung:**
  - Aufnahme von `django-cleanup>=9.0` in `requirements.txt`.
  - Registrierung von `django_cleanup.apps.CleanupConfig` in `INSTALLED_APPS` ([config/settings.py](file:///C:/Users/xyxyx/Desktop/development/config/settings.py)).
  - Definition von `MEDIA_URL = "media/"` und `MEDIA_ROOT = BASE_DIR / "media"` sowie Ausschluss von `media/` in [.gitignore](file:///C:/Users/xyxyx/Desktop/development/.gitignore).
  - Einbindung der Media-Dateien-Auslieferung in [config/urls.py](file:///C:/Users/xyxyx/Desktop/development/config/urls.py) für `DEBUG=True`.
  - Transaktionssicherheit via `transaction.on_commit()`: Dateien werden erst nach erfolgreichem DB-Commit gelöscht; Rollbacks belassen Dateien auf der Festplatte.
  - Erstellung der Architekturentscheidung [ADR-026](file:///C:/Users/xyxyx/Desktop/development/docs/decisions/ADR-026-dateibereinigung-mit-django-cleanup.md).
---

### T36: Saisonverwaltung für den Vorstand (z. B. 2026/2027, S4.7, ADR-027)
- **Problem & Kontext:** Die sportliche Strukturierung in Spielzeiten (z. B. August bis Juli) war im System bisher nicht isoliert abgebildet. Beim Saisonübergang im Sommer mussten Mannschaften manuell neu angelegt werden, und alte Aufstellungen waren nicht vor versehentlicher Überschreibung geschützt.
- **Umsetzung:**
  - Datenmodell `Season` (`teams/models.py`) mit Status-Workflow (`vorbereitung`, `aktiv`, `archiviert`), Start- und Enddatum sowie automatischem Slug.
  - Modellerweiterung: `Team.saison` (`models.PROTECT`, `UniqueConstraint(name, saison)`) und `Tournament.saison` (`models.SET_NULL`).
  - Dreistufige Migration (`teams.0003`, `teams.0004`, `teams.0005`, `tournaments.0002`) mit automatischer Datenmigration aller Bestandsteams in eine initiale Standardsaison.
  - Reines Fachfunktions-Servicemodul (`teams/services.py`): `create_season`, `set_active_season`, `archive_season`, `reopen_season`, `delete_season`, `rollover_teams`, `validate_match_season_bounds`, `check_match_edit_allowed`.
  - Globaler Context-Processor `season_context` (`aktive_saison`, `alle_saisons`, `gewaehlte_saison`).
  - Dünne FBVs mit Rollenschutz `@role_required(ADMIN_GROUP)` in `teams/views.py`.
  - Wiederverwendbare barrierefreie Filterkomponente `teams/templates/teams/includes/season_filter.html` in `team_list.html`, `match_list.html` und `manage_list.html`.
  - Geführter 1-Klick-Saisonwechsel-Assistent (`teams/season_rollover.html`) mit unberührter Vorsaison-Historie und frischen iCal-Tokens.
  - Schreibschutz-Archivierung mit Warnung bei ungespielten Partien, PermissionDenied-Blockade bei Editierversuchen und Archiv-Hinweisbanner in `match_detail.html`.
  - Revisionssichere Dokumentation aller statusändernden Aktionen im `AuditLog`.
  - Architekturentscheidung [ADR-027](file:///C:/Users/xyxyx/Desktop/development/docs/decisions/ADR-027-saisonverwaltung-fuer-den-vorstand.md).
- **Beleg:** 41 dedizierte Tests in `teams/tests/test_season.py`, `test_season_matches.py`, `test_season_rollover.py`, `test_season_archival.py` und `tournaments/tests/test_season_tournaments.py`; Gesamtsuite `docker compose exec app pytest` (664 passed, 1 warning, 256 subtests passed); Negativtests für 403-Zugriffsverweigerung (Gast/Mitglied/Kapitän), Datumsvalidierungsfehler, PermissionDenied bei Schreibschutz, Löschblockade bei belegten Saisons; `assertNumQueries`-Budgets ohne N+1 verifiziert.

---

### T37: Rate-Limiting für öffentliche Endpunkte (django-ratelimit, N1.1/N1.6, ADR-028)
- **Problem & Kontext:** Öffentlich zugängliche Formulare (Schnupper-Anfrage, Turnieranmeldungen für Gäste, Passwort-Reset, Einladungsannahme) waren bisher ungedrosselt und anfällig für Spam/DDoS. Proprietäre Captchas (Google reCAPTCHA, Cloudflare Turnstile) verstoßen gegen DSGVO N1.1 (Verbot von Drittanbieter-Trackern und externen CDNs).
- **Umsetzung:**
  - Aufnahme von `django-ratelimit>=4.1.0` in [requirements.txt](file:///C:/Users/xyxyx/Desktop/development/requirements.txt).
  - Konfiguration in [config/settings.py](file:///C:/Users/xyxyx/Desktop/development/config/settings.py): `RATELIMIT_ENABLE = True`, `RATELIMIT_USE_CACHE = "default"`, `RATELIMIT_VIEW = "core.views.ratelimited_view"`, `RATELIMIT_IP_META_KEY = "REMOTE_ADDR"`, Registrierung von `django_ratelimit.middleware.RatelimitMiddleware` in `MIDDLEWARE`.
  - In [config/settings_test.py](file:///C:/Users/xyxyx/Desktop/development/config/settings_test.py): `RATELIMIT_ENABLE = False` standardmäßig, um allgemeine Tests nicht zu verlangsamen; dedizierte Tests aktivieren das Limit gezielt per `@override_settings(RATELIMIT_ENABLE=True)`.
  - Dekoration der sensiblen öffentlichen POST-Endpunkte mit `@ratelimit(key="ip", rate="5/m", method="POST", block=True)`:
    - [members/views.py](file:///C:/Users/xyxyx/Desktop/development/members/views.py): `join_info` (Schnupper-Anfrage / Kontaktformular)
    - [tournaments/views.py](file:///C:/Users/xyxyx/Desktop/development/tournaments/views.py): `public_detail` (öffentliche Turnieranmeldung für Gastspieler)
    - [core/auth_views.py](file:///C:/Users/xyxyx/Desktop/development/core/auth_views.py): `password_reset` (Passwort-Reset-Formular)
    - [core/auth_views.py](file:///C:/Users/xyxyx/Desktop/development/core/auth_views.py): `accept_invitation` (Funktionärs-Einladungsannahme)
  - Fehleransicht `core.views.ratelimited_view` mit HTTP-Status 429 Too Many Requests, `Retry-After: 60`, barrierefreiem Template [core/templates/core/ratelimited.html](file:///C:/Users/xyxyx/Desktop/development/core/templates/core/ratelimited.html) (im Design von `auth_base.html` / `site.css`), [templates/429.html](file:///C:/Users/xyxyx/Desktop/development/templates/429.html) und JSON-Fallback für AJAX-Anfragen.
  - Architekturentscheidung [ADR-028](file:///C:/Users/xyxyx/Desktop/development/docs/decisions/ADR-028-rate-limiting-mit-django-ratelimit.md).
- **Beleg:** 8 Tests in `core/tests/test_ratelimit.py`; 32 Tests in `core/tests/test_oeffentliches_design.py`; vollständige Testsuite `docker compose exec app pytest` (675 passed, 256 subtests passed, 0 failures); Negativtests: 6. POST-Versuch liefert 429 auf allen geschützten Routen; GET-Anfragen (Lesen von Turnieren/Seiten) bleiben unbegrenzt möglich; verschiedene IP-Adressen besitzen isolierte Kontingente; AJAX-Header liefert sauberes JSON mit HTTP 429.

---

### T31b: Dateigrößen-Begrenzung beim Mitglieder-CSV-Upload (DoS-Schutz, S1.7/N2.2)
- **Problem & Kontext:** `MemberCsvUploadForm` besaß keine Dateigrößenbegrenzung. Der Dateiinhalt wurde bei Uploads mit `read()` vollständig in den RAM geladen und in die Benutzersitzung (`request.session["pending_import_csv"]`) geschrieben. Sehr große Dateien (> hunderte MB) bargen ein DoS-Risiko durch OOM-Abstürze oder ein Aufblähen der Datenbanksitzungstabelle `django_session`.
- **Umsetzung:**
  - `MAX_MEMBER_CSV_SIZE_MB = 2` und `MAX_MEMBER_CSV_SIZE_BYTES = 2 * 1024 * 1024` in [core/forms_setup.py](file:///C:/Users/xyxyx/Desktop/development/core/forms_setup.py) definiert.
  - Feldvalidierung `clean_csv_file()` in `MemberCsvUploadForm`, die Dateien über 2 MB mit ValidationError abweist.
  - Hinweistext im Formularfeld und Helptext um Angabe der maximalen Dateigröße (2 MB) ergänzt.
  - Fehlerbehandlung in [core/views_setup.py](file:///C:/Users/xyxyx/Desktop/development/core/views_setup.py) verfeinert: Spezifische Formularfehler werden in die Flash-Nachrichten übernommen; `pending_import_csv` in der Session wird bei Bestätigung zusätzlich vor Übergröße geschützt.
  - Zusätzliche Absicherung in [core/views_onboarding.py](file:///C:/Users/xyxyx/Desktop/development/core/views_onboarding.py) (Schritt 4, CSV-Import) gegen Uploads über 2 MB.
- **Beleg:** 12 Tests in `members/tests/test_member_import.py` (inkl. `MemberCsvUploadFormTests` und Negativtests `test_upload_file_exceeding_max_size_is_rejected_negative_test`, `test_confirmation_with_oversized_session_data_rejected_negative_test`); 13 Tests in `core/tests/test_onboarding.py` (inkl. `test_step_4_rejects_oversized_csv_negative_test`).

---

### T26c: 2FA-Erzwingung bei Annahme von Vorstands-Einladungen (N1.6)
- **Problem & Kontext:** Beseitigung einer Sicherheitslücke / eines 2FA-Bypasses bei Annahme von Vorstands-Einladungen (`core/auth_views.py:accept_invitation`). Für Vorstände (`rolle="admin"`) ist die Zwei-Faktor-Authentifizierung laut PRD N1.6 und `core.auth_views.zwei_faktor_pflicht` verbindlich. Bisher rief die View nach Annahme der Einladung jedoch direkt `login(request, user)` auf und leitete auf `core:dashboard` weiter, wodurch ein neuer Administrator ohne 2FA-Einrichtung sofort vollen Vorstands-Zugriff erhielt.
- **Umsetzung:**
  - In [core/auth_views.py](file:///C:/Users/xyxyx/Desktop/development/core/auth_views.py) (`accept_invitation`): Prüfung via `_braucht_zwei_faktor(user)`.
  - Bei erforderlicher 2FA: Vorherige Sessions werden sauber beendet (`logout(request)`), 2FA-Sessionvariablen (`SESSION_SCHLUESSEL = user.pk`, `_2fa_backend`, `_2fa_next = ""`, `SESSION_FEHLSCHLAEGE = 0`) gesetzt und zwingend auf `core:zwei_faktor` zur Ersteinrichtung umgeleitet. `login()` wird nicht direkt aufgerufen.
  - Rollen ohne 2FA-Pflicht (z. B. Kapitän) oder Deaktivierung in der Entwicklung (`TWOFA_PFLICHT=False`) loggen weiterhin direkt ein und leiten auf `core:dashboard` weiter.
- **Beleg:** 15 Tests in `core/tests/test_staff_invitation.py` (inkl. neuer Sicherheits- und Negativtests: `test_accept_invitation_view_admin_enforces_2fa_negativtest` prüft Umleitung auf 2FA, Unauthentifiziertheit vor 2FA-Bestätigung, 403/Login-Redirect auf geschützte Routen, Abweisung ungültiger TOTP-Tokens und erfolgreichen Abschluss mit Geräteregistrierung; `test_accept_invitation_view_kapitaen_no_2fa` prüft direkte Anmeldung für Rollen ohne 2FA; `test_accept_invitation_logs_out_existing_session_before_2fa` prüft die Abmeldung vorheriger Nutzersitzungen).

---

### T26d: Step-Up Authentication bei 2FA-Gerätewechsel (N1.6)
- **Problem & Kontext:** In `core/auth_views.py:zwei_faktor_neu` konnte ein eingeloggter Benutzer sein `TwoFactorDevice` ohne erneute Passworteingabe löschen und neu initialisieren. Bei ungesperrten Bildschirmen oder kompromittierten Sitzungen ermöglichte dies eine dauerhafte Kontoübernahme durch Umregistrierung auf ein fremdes 2FA-Gerät.
- **Umsetzung:**
  - In [core/auth_views.py](file:///C:/Users/xyxyx/Desktop/development/core/auth_views.py) (`zwei_faktor_neu`): Abfrage des Kontopassworts (GET rendert Formular, POST validiert via `request.user.check_password(password)`).
  - Fehlversuche senden das Signal `user_login_failed`, loggen eine Fehlermeldung und liefern HTTP 400 mit Formularfehler zurück; das bisherige 2FA-Gerät wird keinesfalls gelöscht.
  - Erfolgreiche Bestätigung löscht das Gerät, initialisiert die 2FA-Session (`SESSION_SCHLUESSEL`), dokumentiert den Vorgang im [AuditLog](file:///C:/Users/xyxyx/Desktop/development/core/models.py) ("2FA-Gerät zurückgesetzt") und leitet zur Neueinrichtung auf `core:zwei_faktor` weiter.
  - View durch `@ratelimit(key="ip", rate="5/m", method="POST", block=True)` gegen Brute-Force-Angriffe abgesichert.
  - Template [core/templates/registration/zwei_faktor_neu.html](file:///C:/Users/xyxyx/Desktop/development/core/templates/registration/zwei_faktor_neu.html) im einheitlichen öffentlichen Design (`auth_base.html`).
  - Menüpunkt / Aktionskarte für 2FA-Gerätewechsel im Benutzerprofil (`members/views.py:profil`, `members/templates/members/profil.html`) für Vorstände und Nutzer mit aktivem 2FA-Gerät integriert.
  - Wartungsdokumentation in [docs/wartung.md](file:///C:/Users/xyxyx/Desktop/development/docs/wartung.md) aktualisiert.
- **Beleg:** 10 Tests in `core/tests/test_haertung.py` (inkl. `test_geraetewechsel_get_zeigt_passwortabfrage`, `test_geraetewechsel_mit_korrektem_passwort_loescht_alte_konfiguration`, Negativtests `test_negativ_geraetewechsel_ohne_passwort_loescht_geraet_nicht`, `test_negativ_geraetewechsel_mit_falschem_passwort_wird_abgelehnt`); 44 Tests in `members/tests/test_selfservice.py` (inkl. `test_profil_zeigt_zwei_faktor_fuer_admin` und Negativtest `test_negativ_profil_ohne_admin_und_ohne_geraet_zeigt_kein_zwei_faktor`); Gesamttestsuite mit 725 Tests zu 100% grün (`docker compose exec app pytest`).

---

### T25c: Schutz gegen CSV Formula Injection in Export-Endpunkten (CWE-1236 / SEC-06, N1.6)
- **Problem & Kontext:** In mehreren CSV-Export-Views (`dues`, `cashbook`, `tournaments`) wurden Benutzereingaben und Textfelder ungefiltert in die CSV-Dateien geschrieben. Wenn Felder mit `=`, `+`, `-`, `@`, Tab oder Return beginnen, führen Tabellenprogramme (Excel, LibreOffice Calc) beim Öffnen Formeln oder DDE-Befehle aus (z. B. `=cmd|' /C calc'!A0`).
- **Umsetzung:**
  - Zentrale Sanitizer-Funktion `sanitize_csv(...)` in [core/ui.py](file:///C:/Users/xyxyx/Desktop/development/core/ui.py): Stellt Textfeldern, die mit `=`, `+`, `-`, `@`, `\t` oder `\r` beginnen, ein einfaches Hochkomma (`'`) voran.
  - Konsequenter Einsatz in sämtlichen CSV-Views:
    - [dues/views.py](file:///C:/Users/xyxyx/Desktop/development/dues/views.py) (`export`): `nachname`, `vorname`, `kategorie_name`, `status`.
    - [dues/views.py](file:///C:/Users/xyxyx/Desktop/development/dues/views.py) (`kassenbericht_export`): `nachname`, `vorname`, `kategorie_name`, `zahlungsart`, `notiz`.
    - [cashbook/views.py](file:///C:/Users/xyxyx/Desktop/development/cashbook/views.py) (`export`): `art`, `kategorie`, `beschreibung`, `belegnummer`, `erfasst_von`.
    - [tournaments/views.py](file:///C:/Users/xyxyx/Desktop/development/tournaments/views.py) (`export_csv`): `name`, `ort`, `format`, `status`, `CLUB_NAME`, `CLUB_CONTACT`, `teilnehmer.name`, `teilnehmer.verein`, Rundenergebnisse / Freilos-Marker.
- **Beleg:** Negativtests in allen Fachmodulen:
  - `dues/tests/test_beitraege.py`: `test_export_escapes_csv_formulas`
  - `dues/tests/test_kassenbericht.py`: `test_kassenbericht_export_escapes_csv_formulas`
  - `cashbook/tests/test_kasse.py`: `test_export_escapes_csv_formulas`
  - `tournaments/tests/test_turniere.py`: `test_export_escapes_csv_formulas`
  - `members/tests/test_views.py`: `test_export_escapes_csv_formulas`
  - Gesamttestsuite mit 725 Tests zu 100% grün (`docker compose exec app pytest`).

---

### T26e: Open-Redirect-Schutz bei der Anmeldung (CWE-601 / SEC-15, N1.6)
- **Problem & Kontext:** In `core/auth_views.py` (`anmelden`, `zwei_faktor`) wurde der Parameter `next` ungeprüft aus `request.POST` bzw. `request.GET` bzw. der Session (`_2fa_next`) übernommen (`redirect(ziel or "core:dashboard")`). Ein Angreifer konnte manipulierte Phishing-Links (z. B. `https://schachverein.de/anmelden/?next=https://evil-phishing.com/login`) versenden, woraufhin Benutzer nach erfolgreicher Authentifizierung und 2FA-Bestätigung nahtlos auf die externe Phishing-Seite weitergeleitet wurden (Open Redirect, CWE-601).
- **Umsetzung:**
  - Zentrale Hilfsfunktion `_sicheres_ziel(ziel, request)` in [core/auth_views.py](file:///C:/Users/xyxyx/Desktop/development/core/auth_views.py) unter Verwendung von Djangos Sicherheitsfunktion `url_has_allowed_host_and_scheme(ziel, allowed_hosts={request.get_host()}, require_https=request.is_secure())`.
  - Strikte Validierung in `anmelden` vor Login-Weiterleitung und vor Session-Ablage in `_2fa_next`.
  - Strikte Validierung in `zwei_faktor` nach erfolgreicher TOTP-Bestätigung (Defense-in-Depth auch gegen manipulierte Sessionwerte).
  - Validierung bei bereits eingeloggten Benutzern sowie Sanitisierung vor Übergabe an den Template-Kontext (`login.html`), damit Phishing-Links nicht in `<input type="hidden" name="next">` gerendert werden.
- **Beleg:** 13 Tests in `core/tests/test_auth.py` (inkl. neuer Positiv- und Negativtests: `test_login_redirect_with_safe_next_url`, `test_negativ_login_rejects_open_redirect_external_url`, `test_negativ_login_rejects_open_redirect_scheme_relative`, `test_negativ_login_page_sanitizes_external_next_parameter`, `test_login_page_renders_safe_next_hidden_input`, `test_authenticated_user_with_safe_next_url`, `test_negativ_authenticated_user_rejects_open_redirect`, `test_two_factor_preserves_safe_next_url`, `test_negativ_two_factor_rejects_open_redirect_url`, `test_negativ_two_factor_rejects_tampered_session_next`); Gesamttestsuite mit 735 Tests zu 100% grün (`docker compose exec app pytest`).

---

### T38: Sofortmaßnahme Release-Sicherheit (MultiFernet, 2FA-Reset CLI, Mail-Queue, N1.6/M5.2/ADR-010)
- **Problem & Kontext:** Drei kritische Betriebsthemen vor dem Produktiv-Release:
  1. *IBAN Key-Rotation:* Wenn der AES-Fernet-Schlüssel für SEPA-Mandate gewechselt wird, konnten bestehende Datensätze nicht ohne Datenverlust oder manuelle DB-Eingriffe entschlüsselt werden.
  2. *2FA Aussperrschutz:* Verliert der einzige Admin sein TOTP-Gerät oder Smartphone, bestand Aussperrgefahr ohne CLI-Notfallzugriff.
  3. *SMTP-Timeouts bei Massenmails:* Synchroner SMTP-Versand in `sende_gruppenmail` bei 100+ Mitgliedern führt im HTTP-Request zu Timeouts.
- **Umsetzung:**
  - *MultiFernet IBAN Key-Rotation:* In `dues/crypto.py` Unterstützung von `IBAN_FERNET_KEYS` (kommagetrennte Liste) mit Fallback auf `IBAN_FERNET_KEY` via `cryptography.fernet.MultiFernet`. Verschlüsselung erfolgt mit dem Primärschlüssel, Entschlüsselung mit allen Schlüsseln. Management-Command `python manage.py rotate_iban_keys [--dry-run]` schlüsselt Mandats-IBANs auf den Primärschlüssel um und schreibt `AuditLog`-Einträge ohne Klartext-IBAN.
  - *2FA Notfall-Aussperrschutz:* Management-Command `python manage.py reset_2fa <username>` in `core/management/commands/reset_2fa.py`. Löscht das `TwoFactorDevice`, schreibt Revisions-Eintrag in `AuditLog` und gibt Erfolgsmeldung aus. Dokumentation in `docs/wartung.md`.
  - *Asynchrone E-Mail-Queue & Batching:* Schlankes Datenbankmodell `QueuedMail` in `comms/models.py`. Migration `comms/0003_alter_maillog_status_queuedmail.py`. Reiner Fachservice `process_mail_queue_batch` in `comms/services.py` mit `limit`, `max_retries` und `dry_run`. Management-Command `python manage.py process_mail_queue`. Entkopplung in `sende_gruppenmail` (`async_send=True` setzt `MailLog.Status.QUEUED`, synchroner Fallback weiterhin nahtlos unterstützt).
- **Beleg:**
  - `dues/tests/test_iban_verschluesselung.py`: 14 Tests (inkl. `test_multi_key_entschluesselung_alter_und_neuer_daten`, `test_rotate_iban_keys_dry_run_aendert_nichts`, `test_rotate_iban_keys_erfolgreiche_rotation_und_audit_log`, Negativtests: `test_ungueltige_schluessel_in_keys_werfen_improperly_configured_negativtest`, `test_fehlerhafte_mandats_chiffre_wird_als_fehler_gezaehlt`).
  - `core/tests/test_reset_2fa.py`: 4 Tests (inkl. `test_erfolgreicher_reset_loescht_geraet_und_schreibt_audit_log`, `test_reset_unbestaetigtes_geraet`, Negativtests: `test_nicht_existierender_benutzer_wirft_command_error_negativtest`, `test_benutzer_ohne_2fa_wirft_command_error_negativtest`).
  - `comms/tests/test_mail.py`: 15 Tests (inkl. `test_async_queue_stellt_in_warteschlange_ohne_sofortigen_versand`, `test_process_mail_queue_dry_run_aendert_keine_zustaende`, `test_process_mail_queue_batch_limit_und_vollstaendige_abarbeitung`, Negativtest: `test_smtp_fehler_und_max_retries_negativtest`).

## Nächste Schritte

1. **Pilotbetrieb & Abnahme** durch den Testverein mit den erstellten Mustern (`docs/einfuehrung_testverein.md`, `docs/abnahme.md`)
2. Ersteinrichtung der echten Beitragssätze und Schlüssel vor Go-Live (`docs/ersteinrichtung.md`)

---

## Noch offen (Blocker, keine Designfragen)

- **Beitragssätze und Kategorien des Vereins** — vor dem ersten echten Beitragslauf im Django-Admin unter *Dues → Beitragskategorien* eintragen. Platzhalter kommen aus `seed_demo`.
- **Verschlüsselungsschlüssel für die IBAN & Backups** — für den Produktivbetrieb erzeugen (`IBAN_FERNET_KEY` und `BACKUP_ENCRYPTION_KEY`) und in `.env.prod` sowie im Passwortmanager getrennt vom DB-Host ablegen; nie ins Repo.
- SMTP-Zugangsdaten — vor dem ersten Gruppenmailversand (in der Entwicklung Django-Console-Backend)
- Domain/Hostname — für Caddy TLS-Zertifikat in `.env.prod` (`DJANGO_ALLOWED_HOSTS`)
- Aufbewahrungsfristen mit Steuerberater bestätigen — Default 36 Monate bis Anonymisierung, 8 Jahre anonymisierte Finanzhistorie nach § 147 AO

