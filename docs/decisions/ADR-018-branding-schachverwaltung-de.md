# ADR-018: Produkt-Branding und Domainausrichtung auf schachverwaltung.de

## Status

Accepted (präzisiert Produktname, Default-Settings und Subdomain-Muster aus ADR-014, Einführungskonzept und Pilotvereinbarung)

## Date

2026-10-09

## Context

Für das kommerzielle Managed-Hosting-Angebot an Schachvereine ([ADR-014](ADR-014-preisgestaltung.md)) wurden in der Codebasis und Dokumentation bisher uneinheitliche Platzhalternamen geführt (`Schachclub-Manager`, `schachclub-cloud.de`, `schachclub-manager.example`, `Schachklub Manager`).

Vor dem Start der Pilotphase und dem Vertrieb an Vorstände und Kassenwarte im Deutschen Schachbund (DSB) und der DACH-Region muss ein konsistenter, professioneller und vertrauenerweckender Markenauftritt etabliert werden. Die Kernzielgruppe (ehrenamtliche Vereinsfunktionäre) legt besonderen Wert auf Datensicherheit, deutsche Serverstandorte, Transparenz und Verlässlichkeit für Finanzen (SEPA) und Mitgliederdaten.

## Decision

1. **Markenname und Plattform-Domain:** Die Software firmiert als **Schachverwaltung.de** (Hauptdomain: `schachverwaltung.de`).
2. **Landingpage & Absender:**
   - Standardwert `PRODUCT_NAME = "Schachverwaltung.de"` in `config/settings.py` und `.env.prod.example`.
   - Offizielle Kontaktadresse: `PRODUCT_CONTACT = "kontakt@schachverwaltung.de"`.
   - Die Produkt-Landingpage (`/produkt/`) sowie Rechtstexte-Entwürfe (`/impressum/`, `/datenschutz/`) treten unter diesem Namen auf.
3. **Mandanten- und Pilot-Instanzen (Subdomain-Konvention):**
   - Standardmäßig gehostete Vereinsinstanzen erhalten eine Subdomain nach dem Schema `[vereinskuerzel].schachverwaltung.de` (z. B. `kunde1.schachverwaltung.de`, `sc-pilot.schachverwaltung.de`).
   - Große Vereine (Tarifstufe „Verband“) können optional ihre eigene Domain bzw. Subdomain betreiben (z. B. `portal.schachverein.de`).
4. **App-Shell (Dashboard & Verwaltung):**
   - Das Header-/Sidebar-Branding in `templates/base.html` wird einheitlich auf `schachverwaltung.de` geführt (`schach` mit Subline `verwaltung.de`).
   - Die Identität des jeweiligen Kundenvereins (`CLUB_NAME`, `CLUB_SHORT`) bleibt über den Club-Switcher und das Vereinsprofil gemäß [ADR-012](ADR-012-vereinsprofil-in-den-settings.md) vollständig erhalten.
5. **Django-Administration:**
   - Der Rückfall-Titel der Administration (`templates/admin/base_site.html`) lautet standardmäßig `Schachverwaltung.de`.

## Consequences

- Klare Markenidentität, die exakt das Kernbedürfnis (Verwaltung von Schachvereinen inkl. Finanzen und Spielbetrieb) adressiert.
- Vollständige Konsistenz über Konfiguration, Templates, Pilotenvereinbarung und Dokumentation.
- Saubere Rollentrennung: `Schachverwaltung.de` ist der Software- und Hostinganbieter, während jeder Verein seine eigene Identität und Datenhoheit behält.
