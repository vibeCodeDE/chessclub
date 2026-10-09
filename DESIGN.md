---
name: Schachclub Königsspringer
description: Klassisch-edles Schachklub-Designsystem für öffentliche Präsenz und Vereinsverwaltung
colors:
  primary: "#1e3b30"
  primary-dark: "#12281e"
  neutral-bg: "#f7f6f1"
  neutral-surface: "#ffffff"
  neutral-ink: "#202c25"
  neutral-muted: "#57685c"
  border: "#d9dfd6"
  accent-rust: "#a86e50"
  accent-gold: "#b88d3b"
  accent-lime: "#dce8a9"
  semantic-success: "#236c3b"
  semantic-warn: "#925f16"
  semantic-danger: "#a42e23"
  surface-sage: "#e9eee5"
typography:
  display:
    fontFamily: '"Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", Georgia, "Times New Roman", serif'
    fontSize: "clamp(55px, 5vw, 72px)"
    fontWeight: 400
    lineHeight: 0.98
    letterSpacing: "-0.035em"
  headline:
    fontFamily: '"Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", Georgia, "Times New Roman", serif'
    fontSize: "34px"
    fontWeight: 400
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  title:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-0.015em"
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "11px"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "0.15em"
rounded:
  xs: "3px"
  sm: "4px"
  md: "7px"
  lg: "11px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  2xl: "48px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.xs}"
    padding: "0 22px"
    height: "54px"
  button-primary-hover:
    backgroundColor: "#2c5040"
  button-lime:
    backgroundColor: "{colors.accent-lime}"
    textColor: "{colors.primary-dark}"
    rounded: "{rounded.xs}"
    padding: "0 22px"
    height: "54px"
  button-lime-hover:
    backgroundColor: "#e9f2c2"
  button-gold:
    backgroundColor: "{colors.accent-gold}"
    textColor: "{colors.primary-dark}"
    rounded: "{rounded.xs}"
    padding: "0 22px"
    height: "54px"
  button-gold-hover:
    backgroundColor: "#c89d56"
  button-admin:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "40px"
---

# Design System: Schachclub Königsspringer

## Overview

**Creative North Star: "The Grandmaster's Study"**

"The Grandmaster's Study" fängt den Geist eines klassischen Schachsalons ein: konzentrierte Stille, haptische Naturmaterialien, tiefes Waldgrün, warmes Holz, glattes Porzellan und der präzise Klang polierter Holzfiguren auf schwerem Brett. Das Designsystem verwirft die visuellen Klischees moderner Startup-Software – keine künstlichen Farbverläufe, keine bunten Illustrationswelten und keine schwebenden Drop-Shadow-Kartenstapel.

Stattdessen gründet das visuelle Erscheinungsbild auf architektonischer Ruhe, handwerklicher Stabilität und publizistischer Würde. Die Typografie verbindet literarische Serif-Schlagzeilen (Iowan Old Style, Palatino, Georgia) für repräsentative Überschriften mit robuster, neutraler System-Sans für hochgradig scannbare Tabellen, Mitgliederlisten und Formulare.

Zwei harmonische Oberflächen teilen dieselbe Seele: Die öffentliche Vereinspräsenz empfängt Besucher und Interessierte auf warmem Naturpapier mit redaktioneller Großzügigkeit; das interne Verwaltungs-Dashboard bietet Vorstand, Kassenwart und Mannschaftskapitänen eine dichte, ruhige und fehlerfreie Arbeitsumgebung auf hellem Porzellan.

**Key Characteristics:**
- Deep Forest Green und Antique Warm Paper / Porcelain als natürliche, erdende Farbträger.
- Architektonische Flachheit: Flächen ruhen stabil auf dem Grund; Strukturierung durch feine 1px-Haarlinien statt diffuser Schattenwolken.
- Würdevolle Typografie-Hierarchie: Literarische Serif-Titel im Zusammenspiel mit neutraler, tabellarischer System-Schrift.
- Kompromisslose Privatsphäre: 100 % Systemschriften und lokale Assets ohne Fremd-CDNs oder Tracker (DSGVO N1.1).

## Colors

Ein harmonisches Farbspektrum aus historischem Schachklub-Grün, Naturpapier, hellem Porzellan und punktuellen Akzenten aus Terracotta-Rost, Bernstein-Gold und Frühlings-Limette.

### Primary
- **Deep Forest Green** (#1e3b30 / #12281e): Die normative Identitätsfarbe des Vereins. Verankert Brand-Header, primäre Aktionsschaltflächen, Tabellenköpfe und das Navigationsband.

### Secondary
- **Antique Paper & Porcelain** (#f7f6f1 / #ffffff / #f5f7f4): Träger aller Inhaltsflächen. Erzeugt die ruhige Haptik eines hochwertigen Schachbuchs und vermeidet grelles Display-Weiß.

### Tertiary
- **Terracotta Rust** (#a86e50): Literarischer Akzentton für Kursiv-Hervorhebungen in Serif-Titeln, Trennlinien (`.small-rule`), aktive Navigationsindikatoren und Fokusringe.
- **Warm Amber Gold** (#b88d3b): Würdevoller Akzent im Verwaltungsbereich für Auszeichnungen, Ranglisten-Details und Vorstandskonturen.
- **Spring Lime** (#dce8a9): Lebendiger Frischeakzent für Eyebrow-Punkte, Terminkarten und aufmerksamkeitsstarke Einladungs-Buttons.

### Neutral
- **Deep Ink** (#202c25 / #1a2820): Hauptschriftfarbe mit maximaler Schärfe und Kontraststärke (WCAG AAA tauglich) ohne die Kälte von reinem Schwarz.
- **Muted Pine** (#68766c / #5e7164): Sekundäre Beschriftungen, Metadaten, Zeitstempel und Tabellenunterzeilen.
- **Hairline Border** (#d9dfd6 / #dee6dd): Präzise 1px-Trennlinien zwischen Containern, Spalten und Zeilen.

### Named Rules
**The Grounded Surface Rule.** Flächen liegen flach auf Papier bzw. Porzellan auf wie ein massives Holzschachbrett. Struktur und Hierarchie entstehen durch tonalen Kontrast und 1px-Haarlinien, niemals durch diffuse Schwebeschatten.
**The Restraint of Accent Rule.** Terracotta-Rost (#a86e50), Bernstein-Gold (#b88d3b) und Frühlings-Limette (#dce8a9) nehmen zusammen maximal 5 % einer Bildschirmansicht ein. Ihre Seltenheit garantiert ihre Signalkraft.

## Typography

**Display Font:** "Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", Georgia, "Times New Roman", serif
**Body Font:** -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif
**Label/Mono Font:** System-Sans mit erzwungenem `tabular-nums`

**Character:** Würdevolle, klassische Buchsatz-Tradition trifft auf nüchterne, ergonomische System-Sans für ermüdungsfreie Lesbarkeit über alle Generationen (6 bis 80+ Jahre).

### Hierarchy
- **Display** (400, `clamp(55px, 5vw, 72px)`, `line-height: 0.98`): Großflächige Leit-Headlines auf öffentlichen Seiten.
- **Headline** (400, `34px`, `line-height: 1.1`, `letter-spacing: -0.03em`): Artikel-, Turnier- und Berichtsüberschriften.
- **Title** (600, `17px`–`28px`, `line-height: 1.25–1.4`): Modul- und Kachelüberschriften in der Verwaltung.
- **Body** (400, `14.5px`–`17px`, `line-height: 1.55`–`1.85`, max. Zeilenlänge 65–75ch): Fließtext, Ankündigungstexte, Reglements.
- **Label** (700, `10px`–`12px`, `letter-spacing: 0.15em`, `text-transform: uppercase`): Eyebrows, Brettnummern, DWZ-Status, Spaltenköpfe.

### Named Rules
**The Classical Pairing Rule.** Überschriften auf öffentlichen Seiten und redaktionellen Artikeln nutzen ausnahmslos die klassische Serif-Familie; Tabellenwerte, interaktive Bedienelemente und dichte Daten nutzen strikt die neutrale System-Sans.
**The Tabular Rigor Rule.** Sämtliche DWZ-Zahlen, Rundenwertungen, Partieergebnisse und Geldbeträge werden ausnahmslos mit `font-variant-numeric: tabular-nums` gerendert.

## Layout

Das Raumsystem gliedert sich kontextspezifisch in zwei optimierte Bereiche:
1. **Öffentlicher Bereich:** Großzügiger Container (`width: min(1360px, calc(100% - 80px))`), asymmetrischer 2-Spalten-Hero (Statement & Porträt), vertikale Rhythmen von 40px bis 90px Abstand für entspanntes Erfassen.
2. **Verwaltungs-Dashboard:** Funktionale, dichte Shell mit fester 250px-Sidebar und 68px-Topbar; Arbeitsfläche in kompaktem 8px/16px/24px-Raster.
- **Responsive Stabilität:** Beide Layouts garantieren absolute Umbruchstabilität ohne horizontalen Überlauf (getestet von 360 px mobil am Brett bis 1280 px Desktop).

## Elevation & Depth

Das System ist "Tonal Layered & Flat-at-Rest". Es vermeidet die schwebende, unruhige Tiefenwirkung typischer Web-Apps.

### Shadow Vocabulary
- **Subtle Rest** (`--shadow-xs` / `--shadow-sm: 0 1px 3px rgba(27, 56, 43, 0.06)`): Hauchfeine Verankerung von Kacheln im internen Dashboard.
- **Hover Lift** (`box-shadow: 0 14px 32px rgba(16, 39, 25, 0.12)` mit `transform: translateY(-2px / -4px)`): Reaktives Feedback bei interaktiven Karten und Schaltflächen.
- **Modal Elevation** (`--shadow-lg: 0 16px 40px rgba(18, 40, 30, 0.12)`): Dialoge, Modalfenster und Dropdowns heben sich klar vom Hintergrund ab.

### Named Rules
**The Flat-by-Default Rule.** Oberflächen ruhen flach. Schatten entstehen nicht als Dekoration, sondern ausschließlich als reaktives Zustandsfeedback (Hover, Fokus, Modalüberlagerung).

## Shapes

- **Radien:** Diskrete, buchbinderische Kantenradien: 3px bei Buttons im öffentlichen Bereich, 4–7px bei internen Feldern und Karten, 11px bei Hauptkacheln. Keine weichen, übertriebenen Riesenradien.
- **Fugen:** 1px-Haarlinien (`border: 1px solid var(--line)`) strukturieren und trennen Inhaltsbereiche.
- **Signature Forms:** Quadratische Brand-Icons (46x46px mit 5px Radius), 7px runde Signal-Punkte (`.status-dot`, `.eyebrow-dot`) und feine 27px x 1px Linientrenner (`.small-rule`).

## Components

### Buttons
- **Shape:** Kantig-diskreter Radius (3px öffentlich, 7px intern)
- **Primary:** Deep Forest Green (#1e3b30) mit weißer Schrift, Höhe 54px (öffentlich) bzw. 40px (intern), `padding: 0 22px`.
- **Hover / Focus:** Dunkleres Tannengrün (#2c5040), sanfter Auftrieb (`translateY(-2px)`), sichtbarer Fokusring (`outline: 2px solid var(--rust)`).
- **Lime Accent:** Spring Lime (#dce8a9) mit dunklem Text (#12281e) für primäre Konversionsziele (z. B. "Mitglied werden").

### Chips & Badges
- **Style:** 7px Farbindikator-Punkt, 11px serifenlose Versalien, `letter-spacing: 0.15em`, dezenter Fond (`var(--forest-soft)` oder `var(--gold-soft)`).
- **State:** Grüne Punkte für freigegeben/aktiv, Bernstein für offen/in Bearbeitung, Terracotta für Fristen/Warnungen.

### Cards / Containers
- **Corner Style:** 3px bis 7px Radius.
- **Background:** Warmes Porzellan (#ffffff) oder getöntes Papier (#f7f6f1).
- **Shadow Strategy:** Flach im Ruhezustand; Schatten nur bei Interaktion.
- **Border:** 1px Haarlinie (`#d9dfd6` / `#dee6dd`).
- **Internal Padding:** 24px bis 32px.

### Inputs / Fields
- **Style:** Porzellan-Hintergrund (#ffffff), 1px Rahmen (`#border`), Radius 4–7px, Höhe 42px.
- **Focus:** Waldgrüner Rahmen mit 3px transluzentem Begleitring (`rgba(27, 56, 43, 0.15)`).

### Navigation
- **Header:** 88px Höhe (öffentlich), 1px Begrenzung nach unten, aktive Menüeinträge mit 2px Rost-Unterstreichung markiert.
- **Sidebar (Admin):** 250px Breite, fester Anker, ruhige Farbgebung in Salbeitönen (`#ecf1eb`) mit feinen 1px-Trennfugen.

### Signature Component: The Chess Fixture & Result Board
- Tabellarische Paarungs- und Ergebnisanzeige mit festen Spaltenbreiten, serifenloser Monospace-/Tabular-Typografie, farblich neutraler Kennzeichnung der Bretter und deutlicher Hervorhebung des Gesamtergebnisses.

## Do's and Don'ts

### Do:
- **Do** Flächen durch 1px-Haarlinien und tonale Farbwechsel strukturieren (`border: 1px solid var(--line)`).
- **Do** Überschriften auf öffentlichen Seiten und in Artikeln in der literarischen Serif-Schrift setzen (`--font-display`).
- **Do** Ziffern, DWZ-Werte, Geldbeträge und Partieergebnisse ausnahmslos mit `tabular-nums` auszeichnen.
- **Do** Tastaturfokus mit kontrastreichem Außenring (2px Rost `#a86e50` oder 3px Tannengrün) sicherstellen.
- **Do** Oberflächen bei 360 px und 1280 px auf absolute Overflow-Freiheit prüfen.

### Don't:
- **Don't** diffuse, schwebende Schattenwolken um Standardkarten legen.
- **Don't** externe CDNs, Google Fonts oder Web-Tracker einbinden (striktes Verbot nach DSGVO N1.1).
- **Don't** bunte Farbverläufe, Neon-Töne oder verspielte Comic-Icons einfügen.
- **Don't** die beiden Stylesheets `static/css/site.css` und `static/css/app.css` vermischen (ADR-013).
- **Don't** Buttons mit übertriebenen Riesenradien (außer bei kreisrunden Icons) versehen.
