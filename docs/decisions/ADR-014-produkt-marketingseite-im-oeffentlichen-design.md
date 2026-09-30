# ADR-014: Produkt-Marketingseite in der Designsprache des öffentlichen Auftritts

**Status:** angenommen (2026-09-30)
**Löst ab:** die Ausklammerung „`/produkt/` bleibt vorerst unverändert" aus
[ADR-013](ADR-013-oeffentliche-designsprache.md)
**Betrifft:** `templates/produkt_base.html`, `core/templates/core/produkt.html`,
`core/templates/core/rechtliches.html`, `static/css/site.css`, `static/css/landing.css`
(gelöscht), `core/produkt.py`, `core/views.py`, `core/tests/test_produkt.py`

## Kontext

Die Verkaufsseite `/produkt/` (die Vereinsverwaltung wird als Dienstleistung an andere
Vereine verkauft) nutzte bislang ein eigenes Layout: `static/css/landing.css` mit dem
Klassenpräfix `lp-`, dazu zusätzlich `app.css` aus dem internen Design-System. Damit
existierten drei Gestaltungsebenen nebeneinander (intern, öffentliche Vereinsseite,
Produktseite). Die Produktseite teilte sich keine Bausteine mit einer der anderen
Ebenen, lud versehentlich das interne Stylesheet mit und musste separat gepflegt
werden. ADR-013 hatte die Seite bewusst ausgeklammert, um T28 klein zu halten.

## Entscheidung

1. **Eine Designsprache für alles Öffentliche.** `/produkt/` sowie `/impressum/` und
   `/datenschutz/` werden in der Designsprache des öffentlichen Auftritts umgesetzt:
   ausschließlich `static/css/site.css`, dieselben Tokens und Bausteine
   (`.site-header`, `.brand`, `.site-footer`, `.page-intro`, `.prose`) wie auf der
   Vereinsseite. `landing.css` entfällt ersatzlos (Datei gelöscht).
2. **Eigene Hülle mit Produkt-Branding.** Neu ist `templates/produkt_base.html` als
   Hülle. Die Seite richtet sich an andere Vereine, nicht an die Mitglieder des
   Demo-Vereins — sie bekommt deshalb keine Vereins-Navigation und keinen Vereins-Footer,
   sondern Marke (`PRODUCT_NAME`) und Kontakt (`PRODUCT_CONTACT`) aus den Settings.
   Die Navigation ist eine reine Anker-Navigation innerhalb der Seite.
3. **Kein JavaScript.** Die Verkaufsseite lädt weder `public.js` noch `app.js`: die FAQ
   ist ein `<details>`-Element, die Navigation reine Sprunglinks, es gibt keine Formulare
   und daher keine Toasts oder Ladebalken. Die Seite funktioniert ohne JavaScript
   vollständig. (PRD S10.4)
4. **Inhalte zentral in `core/produkt.py`.** Hero, Kennzahlen, Nutzen-Argumentation,
   Rollen und Demo-Vorschau stehen neben Preisstufen, Funktionen, Datenschutzpunkten,
   Einstiegsschritten und FAQ in `core/produkt.py`; die Templates enthalten nur
   Darstellung. Die Preise bleiben Platzhalter und werden auf der Seite als solche
   gekennzeichnet. (PRD S10.2)
5. **Kontakt nur per E-Mail.** Jede Demo-Anfrage läuft über mailto-Links an
   `PRODUCT_CONTACT`. Es gibt keinen Bestellprozess und keine Preis- oder Vertragsdaten
   in der Datenbank. (PRD S10.3)

## Konsequenzen

- Eine Gestaltungsebene weniger: Änderungen an Tokens oder Bausteinen wirken jetzt auch
  auf die Produktseite; ein eigenes Corporate Design der Produktmarke (eigene Farben,
  eigene Schriften) wäre ein späterer, separater Beschluss.
- `site.css` wächst um den Abschnitt „Produkt-Marketingseite“; die Klassendeckung wird
  wie bei allen öffentlichen Templates durch `core/tests/test_oeffentliches_design.py`
  erzwungen (produkt-Templates stehen in `PUBLIC_TEMPLATES`).
- Die Verkaufsseite lädt kein Skript — daraus folgt auch, dass sie nicht am Service
  Worker der Vereinsseite teilnimmt und keine dynamischen Meldungen zeigen kann.
- `landing.css` ist gelöscht; ADR-013 bleibt als Dokument bestehen, seine Abgrenzung
  zu `/produkt/` ist durch diesen Beschluss ersetzt.

## Abgrenzung

Das interne Design (Dashboard, Verwaltung, Django-Admin) bleibt wie in ADR-013
unberührt und folgt weiterhin `app.css`; eine eigene interne Optik ist separat
geplant.
