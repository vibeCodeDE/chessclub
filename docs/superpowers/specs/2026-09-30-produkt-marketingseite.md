# Spec: Produkt-Marketingseite (T29)

**Anforderungen:** PRD §3.10 (S10.1–S10.4)
**Entscheidung:** [ADR-014](../../decisions/ADR-014-produkt-marketingseite-im-oeffentlichen-design.md)
**Vorgänger:** [Spec Öffentliche Designsprache (T28)](2026-09-30-oeffentliche-designsprache.md)

## Umfang

Neubau der Verkaufsseite `/produkt/` (Verkauf der Vereinsverwaltung an andere Vereine)
sowie der rechtlichen Seiten `/impressum/` und `/datenschutz/` in der Designsprache des
öffentlichen Auftritts — mit eigenem Produkt-Branding statt Vereins-Navigation.
**Nicht** enthalten: Vereinsseite und interner Bereich (unverändert), neue Inhalte für
Preise oder Vertrag (weiterhin Platzhalter in `core/produkt.py`).

## Dateien

| Datei | Rolle |
| --- | --- |
| `templates/produkt_base.html` | **neu**: Hülle der Verkaufsseite — Header mit Produkt-Marke und Anker-Navigation, Abschluss-CTA-Bereich im Footer, rechtliche Links; lädt nur `site.css`, kein Skript |
| `core/templates/core/produkt.html` | Verkaufsseite: Hero, Kennzahlenband, Nutzen, Funktionen, Rollen, Datenschutz, Einstieg, Preise, FAQ |
| `core/templates/core/rechtliches.html` | Impressum/Datenschutzerklärung in derselben Gestaltung (`.page-intro` + `.prose`) |
| `core/produkt.py` | alle Inhalte: `HERO`, `KENNZAHLEN`, `PROBLEM`, `ROLLEN`, `DEMO`, `PREIS_HINWEIS` neben den bestehenden `PREISSTUFEN`, `FUNKTIONEN`, `DATENSCHUTZ_PUNKTE`, `SCHRITTE`, `FAQ` |
| `core/views.py` | `produkt_seite` reicht die neuen Inhalte an das Template |
| `static/css/site.css` | Abschnitt „Produkt-Marketingseite“ inkl. eigener Responsive-Regeln |
| `static/css/landing.css` | **gelöscht** (ADR-014) |

## Seitenstruktur `/produkt/`

| Abschnitt | Anker | Quelle in `produkt.py` |
| --- | --- | --- |
| Hero mit Demo-CTA und Vorschau-Panel | — | `HERO`, `DEMO` |
| Kennzahlenband (dunkel) | — | `KENNZAHLEN` |
| Nutzen (vorher/nachher) | — | `PROBLEM` |
| Funktionen (6 Kacheln) | `#funktionen` | `FUNKTIONEN` |
| Rollen (3 Spalten) | — | `ROLLEN` |
| Datenschutz (dunkel, Punkte mit Haken) | `#datenschutz` | `DATENSCHUTZ_PUNKTE` |
| Einstieg in drei Schritten | `#ablauf` | `SCHRITTE` |
| Preisstufen (3 Flächen, eine hervorgehoben) | `#preise` | `PREISSTUFEN`, `PREIS_HINWEIS` |
| FAQ (klappbar, `<details>`) | `#faq` | `FAQ` |
| Abschluss-CTA | — | `PRODUCT_CONTACT` |

Kontaktwege ausschließlich mailto an `PRODUCT_CONTACT` (Betreff „Demo anfragen“, je
Preisstufe mit Stufennamen). Die Demo-Vorschau ist ein explizites Mock (nur Gestaltung,
`role="img"` mit erklärendem `aria-label`) — sie zeigt, wie das Dashboard aussieht, und
erhebt keine Zahlenansprüche.

## Bausteine und Klassen

Wiederverwendet aus dem Bestand: `.container`, `.site-header`/`.header-inner`/`.brand*`,
`.nav-link`, `.header-join`, `.site-footer`/`.footer-*`, `.skip-link`, `.eyebrow`,
`.section-title`, `.hero-eyebrow`, `.hero-intro`, `.hero-actions`, `.underlined-link`,
`.button`/`.button-dark`/`.button-lime`, `.page-intro`, `.prose`.

Neu, Präfix `produkt-` (alle in `site.css` definiert, Class-Coverage-Test):
`produkt-nav`, `produkt-hero`, `produkt-checks`, `produkt-demo*`, `produkt-strip`,
`produkt-nutzen`, `produkt-vorher*`, `produkt-cards`, `produkt-card`, `produkt-rollen`,
`produkt-dsgvo*`, `produkt-steps`, `produkt-step`, `produkt-plans`, `produkt-plan`,
`produkt-hinweis`, `produkt-faq`, `produkt-cta`.

Responsive eigene Regeln: ab 980 px einspaltig, ab 640 px Kacheln und Preisflächen
untereinander; Kennzahlenband 2×2. Ab 360 px ohne horizontalen Overflow (PRD N2.6).

## Verifikation

- `pytest core/tests/test_produkt.py core/tests/test_oeffentliches_design.py`
  - produkt-Templates stehen in `PUBLIC_TEMPLATES` (Klassendeckung, Stylesheet-Trennung),
    `/produkt/`, `/impressum/`, `/datenschutz/` im Fremdquellen-Test (N1.1)
  - **Negativtest:** `/produkt/` lädt weder `app.css` noch `landing.css` noch irgendein
    Skript; `landing.css` existiert nicht mehr; keine Vereins-Navigation auf der
    Verkaufsseite; Preise sind als Platzhalter markiert
- Vollständiger Lauf: `pytest` grün
- Browser-Check 360 px und 1280 px ohne horizontalen Overflow
