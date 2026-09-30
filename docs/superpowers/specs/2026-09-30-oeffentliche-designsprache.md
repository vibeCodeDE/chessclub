# Spec: Öffentliche Designsprache (T28)

**Quelle:** `schachclubmanager-modern-web-design (1).zip` (Design-Referenz, Next.js)
**Entscheidung:** [ADR-013](../../decisions/ADR-013-oeffentliche-designsprache.md)
**Umsetzung:** T28 in `tasks/plan.md`

## Umfang

Öffentlicher Teil der App: Startseite, Aktuelles (Liste/Detail), Turniere (Liste/Detail
inkl. Anmeldung), Mitglied werden, neue Seite *Der Verein*, 404, Offline-Seite sowie der
Anmeldeeinstieg (Login, 2FA, Passwort-Reset). **Nicht** enthalten: Dashboard und interne
Seiten (eigenes Design, folgt separat) und `/produkt/` (Verkaufsseite, unverändert).

## Dateien

| Datei | Rolle |
| --- | --- |
| `static/css/site.css` | Design-System des öffentlichen Teils (Tokens, Komponenten, Responsive) |
| `templates/public_base.html` | Hülle: Header mit Hauptnavigation, Flash-Meldungen, Footer |
| `templates/auth_base.html` | Hülle für Anmeldung/2FA/Passwort-Reset |
| `templates/404.html` | Fehlerseite in der neuen Designsprache |
| `templates/includes/public_field.html` | Formularfeld-Partial (`.form-field`, Pflicht-/Optional-Markierung) |
| `core/templates/core/home.html` | Startseite (Hero, Wochenband, Kennzahlen, News, Spielplan, Turnier, Mitmachen) |
| `core/templates/core/news_archiv.html` | Archiv mit Kategoriefilter und Aside |
| `core/templates/core/news_detail.html` | Artikelansicht mit Sidebar („Weiterlesen“) |
| `core/templates/core/verein.html` | **neu**: Selbstverständnis, Zeiten, Ligaspielplan, CTA |
| `core/templates/core/offline.html` | Offline-Seite (PWA) |
| `tournaments/templates/tournaments/public_list.html` | Turnierkalender (große Tagesziffern, Archiv) |
| `tournaments/templates/tournaments/public_detail.html` | Turnier-Hero mit Datumsfläche, Eckdaten, Anmeldung, Rangliste |
| `members/templates/members/join_info.html` | Beitragssätze, Einstieg in drei Schritten, Zeiten |
| `core/templates/registration/*.html` | Login, 2FA, Passwort-Reset (vier Schritte) |
| `static/img/*.jpg` | Bildplätze (lokal, austauschbar) |
| `static/js/app.js` | `initPublicNav()` – mobiles Menü (aria-expanded, Escape, Außenklick) |

## Design-Tokens

| Token | Wert | Verwendung |
| --- | --- | --- |
| `--paper` | `#f7f6f1` | Seitenhintergrund |
| `--white` | `#fffefa` | Formular- und Kartenflächen |
| `--ink` | `#202c25` | Fließtext |
| `--forest` / `--forest-deep` | `#1e3b30` / `#192f27` | Buttons, Footer, dunkle Flächen |
| `--sage` | `#e9eee5` | Panels (Spielplan, Eckdaten, Aside) |
| `--lime` | `#dce8a9` | Akzent auf dunklem Grund, Datumsfläche |
| `--rust` | `#a86e50` | Akzent in Serif-Überschriften, aktive Navigation |
| `--muted` / `--line` | `#68766c` / `#d9dfd6` | Sekundärtext, Trennlinien |

Typografie: `--display` (Serif, `clamp()`-Skalierung, Ziffern der Datums- und
Kennzahlenblöcke) und `--sans` (System-Stack). Eyebrows und Tabellenköpfe werden per
`text-transform: uppercase` gesetzt, damit der Template-Quelltext lesbar bleibt.

## Wichtige Bausteine

- **`.container`** – `min(1360px, 100% − 80px)`, mobil `100% − 40px`.
- **Buttons** – `.button`/`.button-dark`/`.button-lime`, `.underlined-link`, `.round-arrow`.
- **`.news-row`** – Datum (Tag/Monat), Kicker, Titel, Auszug, Pfeil; Hover färbt Titel rost.
- **`.fixtures-panel`** – Ligaspiele der nächsten Wochen.
- **`.tournament-index-item`** – Datum | Ausschreibung | Rundpfeil.
- **`.fact-row`** – Icon, Label, Wert (Eckdaten der Turnierseite).
- **`.table-scroll` + `.ranking-table`** – scrollbare Tabellen (Rangliste, Teilnehmerliste).
- **`.schedule-*`** – Spielplan-Zeilen der Vereinsseite.
- **Meldungen** – `.public-alert` (info/error/success) aus Django-Messages.
- **Responsive** – Brüche bei 1200/980/640 px; Tabelle der Referenz übernommen.

## Datenbindung

| Seitenbereich | Quelle |
| --- | --- |
| Kennzahlen der Startseite | `Member` (aktiv), `Team` (aktiv), `Tournament` (öffentlich, künftig), `LeagueMatch` (künftig) |
| „Jahre Vereinsgeschichte“ | `CLUB_FOUNDED` (nur wenn gesetzt, sonst zeigt die Kachel Ligaspiele) |
| News | `NewsPost` (`veroeffentlicht=True`), Kategoriefilter über `?kategorie=` |
| Turnierkalender | `Tournament` (`oeffentlich=True`), Status über `anmeldung_offen` |
| Anmeldung | `PublicRegistrationForm` → `Participant` (unverändert) |
| Ligaspiele | `LeagueMatch` (`datum >= heute`) |
| Beitragssätze | `FeeCategory` (`aktiv=True`) |
| Zeiten/Treffpunkt | `CLUB_NIGHT_HOURS`, `CLUB_YOUTH_HOURS`, `CLUB_ROOM` |

## Bilder

| Datei | Einsatz | Motiv |
| --- | --- | --- |
| `static/img/klubabend.jpg` | Startseite, Hero | Vereinsabend an mehreren Brettern |
| `static/img/turnier-bretter.jpg` | Startseite, Turnierabschnitt | Figuren und Schachuhr |
| `static/img/gemeinschaft.jpg` | Startseite, Mitmach-Abschnitt | gemeinsame Analyse |
| `static/img/vereinsheim.jpg` | Vereinsseite, Chronik | vorbereitete Bretter im Raum |

Die Motive sind Beispielbilder (per Bildgenerierung erzeugt, lokal ausgeliefert). Für den
Livegang sind echte Vereinsfotos unter denselben Dateinamen vorgesehen; die
Bildunterschriften sind bewusst neutral gehalten.

## Neue Einstellungen (ADR-012)

`CLUB_FOUNDED`, `CLUB_LOCATION`, `CLUB_ROOM`, `CLUB_NIGHT_HOURS`, `CLUB_YOUTH_HOURS`,
`CLUB_DESCRIPTION` – alle optional; die Templates blenden leere Werte aus. Vorlage:
`.env.prod.example`, Doku: `README.md`.

## Offene Punkte

- **Echte Vereinsfotos** ersetzen die Beispielbilder (kein Codeänderungsbedarf).
- **Eigene Schriften** wären ein eigenes Paket (Lizenz, Dateigröße, DSGVO) – heute System-Stack.
- **Internes Design** (Dashboard, Verwaltung) folgt separat; die Trennung ist vorbereitet.
- `/produkt/` bleibt in der bisherigen Gestaltung (`landing.css`).

## Verifikation

- `pytest core/tests/test_oeffentliches_design.py` – Klassendeckung, Stylesheet-Trennung,
  keine Fremd-URLs, Filterverhalten, 404, leere Vereinsdaten, Bildbestand.
- Vollständiger Lauf: `pytest` → 331 Tests grün, 1 Skip (nur mit PostgreSQL), 160 Subtests.
- Manueller Abgleich aller Links/Assets und der HTML-Struktur (Tag-Balance) gegen die
  laufende Instanz; Interaktionen des mobilen Menüs automatisiert geprüft (jsdom).
