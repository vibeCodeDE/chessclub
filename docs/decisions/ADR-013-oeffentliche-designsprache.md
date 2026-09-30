# ADR-013: Designsprache der öffentlichen Vereinsseite

**Status:** angenommen (2026-09-30)
**Betrifft:** `core/templates/core/*`, `tournaments/templates/tournaments/public_*`, `members/templates/members/join_info.html`, `templates/public_base.html`, `templates/auth_base.html`, `static/css/site.css`, `static/js/public.js`

## Kontext

Die Design-Referenz `schachclubmanager-modern-web-design (1).zip` (Next.js/React,
Tailwind-Basis, aber faktisch handgeschriebenes CSS in `src/app/globals.css`) beschreibt
eine neue Designsprache für den öffentlichen Teil: Papierweiß `#f7f6f1`, Tannengrün
`#1e3b30`, Limette `#dce8a9`, Rost `#a86e50`, große Serif-Überschriften, kantige Flächen
statt schwebender Karten, Startseite mit Hero/Statistikband/News/Spielplan, Seiten
*Aktuelles*, *Turniere*, *Der Klub*, *Mitglied werden* und eine 404-Seite.

Die Django-App bringt bereits ein eigenes, handgeschriebenes Design-System für den
internen Bereich mit (`static/css/app.css`, dunkelblaue Verwaltungsoptik). Für die
Vorstandschaft ist ein **eigenständiges** internes Design geplant, das noch geliefert wird.

Rahmenbedingungen aus dem PRD, die die Umsetzung einschränken:

- **N1.1:** keine Drittanbieter-Assets – kein CDN, keine externen Schriften, keine Tracker.
- **Kein CSS-Buildschritt** (`tasks/plan.md`, Architektur-Entscheidungen): kein Node im Betrieb.
- Die öffentliche Seite ist Teil derselben Django-Anwendung, dieselben Views/Daten.

## Entscheidung

1. **Portierung statt Übernahme.** Die Designsprache wird als **handgeschriebenes
   Stylesheet `static/css/site.css`** in Django-Templates umgesetzt. Die Next.js-Dateien
   bleiben unverändert als Referenz im Repository liegen; es wird kein Node-Toolchain,
   kein Tailwind und kein Buildschritt eingeführt.
2. **Zwei getrennte Design-Systeme.** `site.css` gilt ausschließlich für den öffentlichen
   Teil (Hüllen `templates/public_base.html` und `templates/auth_base.html`), `app.css`
   weiterhin ausschließlich für den internen Bereich (`templates/base.html`). Öffentliche
   Templates laden **nie** `app.css`; interne Templates **nie** `site.css`. Das interne
   Design kann damit später ohne Kollision ersetzt werden.
3. **Schriften aus dem System-Stack.** Statt `@fontsource`-Webfonts (Referenz) nutzt die
   Umsetzung `--font-display` (Iowan Old Style/Palatino/Georgia) und `--font-sans`
   (Segoe UI/system-ui). Das erfüllt N1.1 ohne Webfont-Auslieferung; ein eigenes Fontpaket
   wäre ein späterer, separater Beschluss.
4. **Echte Daten statt Referenztexte.** Alle Inhalte kommen aus den bestehenden Modellen
   (`NewsPost`, `Tournament`, `LeagueMatch`, `Team`, `Member`, `FeeCategory`). Die im
   Design erfundenen Texte/Zahlen werden nicht als Factoids eingebaut. Das Vereinsprofil
   (Gründungsjahr, Ort, Raum, Zeiten) kommt aus den Settings (ADR-012); leere Werte
   blenden die betroffene Zeile aus, statt einen Platzhalter zu erfinden.
5. **Bilder lokal, keine Fremdquellen.** Die Bildplätze der Referenz werden mit lokalen
   Dateien unter `static/img/` belegt (Beispielmotive, per Bildgenerierung erzeugt) und
   sind für echte Vereinsfotos austauschbar; die Dateinamen stehen in der Spec.
6. **Barrierefreiheit und Bedienbarkeit** bleiben erhalten: Skip-Link, `aria-current`
   für die aktive Seite, `aria-expanded`/`Escape` für das mobile Menü, Fokus-Ringe,
   `prefers-reduced-motion`. Formulare funktionieren ohne JavaScript.
7. **Getrennte Skripte.** Die öffentlichen Seiten laden `static/js/public.js` mit genau
   ihrem Bedarf (mobiles Menü, Ladebalken beim Seitenwechsel, Toasts,
   Service-Worker-Registrierung). Das interne `static/js/app.js` bleibt dem
   Dashboard/der Verwaltung vorbehalten; beide Dateien sind unabhängig und keine
   öffentliche Hülle lädt `app.js`. Erzwungen durch
   `core/tests/test_oeffentliches_design.py` (öffentliche Hüllen laden nur `public.js`,
   `public.js` kennt keine internen Bausteine).

## Konsequenzen

- Der öffentliche Teil kann unabhängig weiterentwickelt werden; interne Templates bleiben
  unberührt und behalten ihre Tests.
- Die Referenz-ZIP bleibt als Designquelle im Repository (Änderungen dort sind Vorlagen,
  keine Laufzeitabhängigkeit).
- Neue öffentliche Seiten müssen `site.css` und die Klassen der Spec verwenden; ein Test
  (`core/tests/test_oeffentliches_design.py`) prüft, dass jede verwendete Klasse definiert
  ist, dass die Trennung der Stylesheets hält und dass keine Fremd-URLs im HTML landen.
- Doppelte Pflege von Gestaltung: `site.css` und `app.css` haben getrennte Variablensätze.
  Bewusst akzeptiert – die beiden Bereiche sollen sich nicht gegenseitig überschreiben.

## Abgrenzung

Diese ADR regelt **nur** den öffentlichen Teil. Das interne Design (Dashboard,
Verwaltung) ist nicht Gegenstand; es wird in einer eigenen Entscheidung behandelt,
sobald die Vorlage vorliegt. Die Verkaufsseite `/produkt/` (eigene Landingpage mit
`landing.css`) bleibt vorerst unverändert.
