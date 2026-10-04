# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Vorstand (Admin / 1. Vorsitzender, Kassenwart, Schriftführer):** Führt den Verein ehrenamtlich in der Freizeit. Benötigt maximale Übersicht, automatisierte jährliche Beitragsläufe, Mahnwesen, revisionssichere Kassenbuchführung und strikte DSGVO-Konformität ohne Excel-Chaos.
- **Mannschaftskapitän:** Organisiert Spieltage, meldet Aufstellungen fristgerecht und erfasst Einzelergebnisse direkt und zügig (häufig mobil am Brett im Spiellokal).
- **Mitglieder (Jugendliche ab 6 Jahren bis Senioren 80+ Jahre):** Heterogene Altersstruktur. Prüfen ihren Beitragsstand, melden sich unkompliziert zu Turnieren an und pflegen eigene Stammdaten per Änderungswunsch-Workflow.
- **Öffentlichkeit & Gastspieler:** Interessierte, Eltern und Gastspieler anderer Vereine. Informieren sich über Trainingszeiten, Klubabende und melden sich barrierefrei zu offenen Turnieren an.

## Product Purpose

Selbst gehostete, vollintegrierte Vereinsverwaltung und Webpräsenz für Schachvereine (< 200 Mitglieder). Löst fragmentierte Einzellösungen (Excel-Tabellen, Messenger-Gruppen, isolierte CMS) durch ein einheitliches, datensouveränes System ab. Erfolg bedeutet: Null Datenverlust, minimaler ehrenamtlicher Administrationsaufwand, absolute DSGVO-Konformität auf eigener Infrastruktur und barrierefreie Nutzung über alle Generationen hinweg.

## Positioning

Die einzige speziell auf Schachvereine zugeschnittene Lösung mit nativer Schweizer-System-Turnierverwaltung, DWZ-/Ligaspielbetrieb und vollständiger Datensouveränität (100 % selbst gehostet, null Drittanbieter-CDNs/Tracker, revisionssichere Buchhaltung per Gegenbuchung).

## Operating Context

- **Einsatzorte & Situationen:** Ruhige bis lebhafte Spielabende im Vereinsheim, Wettkampfatmosphäre an Sonntagen bei Ligaspielen (Mobilnutzung am Smartphone), administrative Vorstandsarbeit am Desktop.
- **Rituale & Zyklen:** Wöchentliche Spielabende & Jugendtraining; jährliche Hauptversammlung mit Kassenbericht; saisonale Beitragsläufe mit SEPA-Dateien; feste Rundenfristen im Ligabetrieb.
- **Systemumgebung:** Lokaler Vereinsserver oder deutscher Host (Docker Compose, Django 5, PostgreSQL). Kein Bank-API-Direktzugriff (SEPA-Einzug erfolgt bankseitig manuell via XML/Pain; IBANs verschlüsselt gespeichert).

## Capabilities and Constraints

- **Kernfunktionen:** Mitgliederverwaltung mit Statusverlauf (aktiv/passiv/ausgetreten) und Änderungswunsch-Freigabe; Beitragsstufen, automatische Beitragsläufe und Mahnwesen (PDF); Kassenbuch mit Jahresabschluss-Export; Turniere mit Schweizer System; Mannschafts- und Ligaspielverwaltung; Ankündigungen und DSGVO-Auskunft/Anonymisierung.
- **Zwei getrennte Oberflächen:** Öffentliche Vereinsseite (`static/css/site.css`, `templates/public_base.html`) und interne Verwaltungs-Shell (`static/css/app.css`, `templates/base.html`), strikt getrennt ohne CSS-Buildschritt.
- **Harte Vorgaben:**
  - DSGVO N1.1: Keine externen CDNs, Tracker oder Drittanbieter-Fonts.
  - Finanzdaten werden nie gelöscht (Storno/Korrektur nur per Gegenbuchung und AuditLog; ADR-005, ADR-006).
  - Kein automatisierter Bank-API-Zugriff; IBAN-Verschlüsselung mit Schlüssel aus Umgebung (ADR-002, ADR-010).
  - Verbindliche Berechtigungsmatrix nach PRD §3.8 mit Negativtests für jede Rolle.

## Brand Commitments

- **Vereinsidentität:** Schachclub Königsspringer Musterstadt e.V. (konfigurierbar über Umgebungsvariablen wie `CLUB_FOUNDED`, `CLUB_LOCATION`, `CLUB_ROOM`, `CLUB_NIGHT_HOURS`).
- **Tonalität:** Verbindlich, gemeinschaftsorientiert, klar und barrierearm ohne bürokratische Hürden.
- **Design-Erbe:** Der öffentliche Auftritt folgt der etablierten, modernen Designsprache (ADR-013, Spec 2026-09-30); der interne Bereich priorisiert hohe Informationsdichte, Lesbarkeit und Scanability.

## Evidence on Hand

- Freigegebenes PRD v1.6 (`docs/prd.md`) und Architekturentscheidungen (`docs/decisions/ADR-*.md`).
- Realistische Seeding-Daten (`manage.py seed_demo`) mit vollständigen Testbenutzern (`vorstand`, `kassenwart`, `kapitaen`, `mitglied`).
- Vereinsbezogene Bildressourcen unter `static/img/`.
- Verkaufsseite für externe Vereine unter `/produkt/` mit festen Tarifen (ADR-014).

## Product Principles

- **Datensouveränität & Unabhängigkeit:** Alle Daten gehören dem Verein und bleiben auf eigener Hardware; keine Abhängigkeiten von externen Cloud-Plattformen oder Trackern.
- **Generationenübergreifende Barrierefreiheit:** Kompromisslose Lesbarkeit und einfache Bedienung für Jugendliche bis hin zu hochbetagten Senioren (WCAG AA/AAA).
- **Ehrenamt entlasten, Fehler ausschließen:** Workflows führen sicher durch komplexe Aufgaben; versehentliches Löschen von Finanz- oder Stammdaten ist technisch unterbunden.
- **Schachspezifische Präzision:** Fachbegriffe, Paarungslogik, Rundenabläufe und Aufstellungsregeln spiegeln exakt die reale Vereinspraxis wider.

## Accessibility & Inclusion

- Verbindliche Erfüllung von WCAG 2.1 AA (teilweise AAA bei Kontrasten und Textabständen).
- Durchgängige Tastaturbedienbarkeit aller Kernabläufe.
- Responsiv ohne horizontalen Overflow bei 360 px (Smartphone am Brett) und 1280 px (Desktop im Vereinsbüro).
- Skalierbare Schriften und klare Hierarchien für optimale Lesbarkeit bei wechselnden Lichtverhältnissen.
