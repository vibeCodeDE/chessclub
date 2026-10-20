# ADR-029: Open-Source-Lizenzmodell AGPLv3 und Abgrenzung zum Managed Hosting

## Status

Accepted (ergänzt und präzisiert [ADR-014](ADR-014-preisgestaltung.md))

## Date

2026-10-20

## Context

In der ursprünglichen Preis- und Vertriebsüberlegung ([ADR-014](ADR-014-preisgestaltung.md)) wurde die Bereitstellung als reines Managed-Abo konzipiert („Kein Self-Hosting, keine Einmallizenz“).

Die Praxis im deutschen Vereinswesen sowie Rückmeldungen von Kassenwarten und Vorständen zeigen jedoch klare Rahmenbedingungen:
1. **Ehrenamt & Vertrauen (Vendor Lock-in):** Ehrenamtliche Vorstände scheuen proprietäre Closed-Source-Lösungen kleiner Entwickler aus Sorge vor Ausfall oder Einstellung des Dienstes („Was passiert mit unseren sensiblen Mitgliederdaten, wenn der Betreiber in zwei Jahren aufhört?“). Transparenz und Datenhoheit sind das Verkaufsargument Nr. 1.
2. **Die Bequemlichkeit ist das eigentliche Produkt:** Über 95 % der Vorstände verfügen weder über die Zeit noch die Fachkenntnis, um Linux-Server, Docker, PostgreSQL-Cluster, TLS-Zertifikate, verschlüsselte Offsite-Backups, Mail-Routing und Sicherheits-Patches eigenverantwortlich zu betreiben. Obwohl der Code offenliegt, zahlen Vereine gerne für eine schlüsselfertige Instanz (vergleichbar mit Modellen wie Ghost, Plausible Analytics oder Bitwarden).
3. **Schutz vor proprietärer Ausbeutung:** Eine permissive Lizenz (MIT/Apache) würde es kommerziellen Konkurrenten erlauben, das System als proprietäres SaaS anzubieten, ohne Verbesserungen zurückzugeben.

## Decision

1. **Lizenzierung unter der GNU Affero General Public License v3.0 (AGPLv3):**
   - Das gesamte Quellcode-Repository wird unter der AGPLv3 veröffentlicht.
   - Das starke Netzwerk-Copyleft der AGPLv3 verpflichtet jeden, der die Software über ein Rechnernetzwerk als Dienst bereitstellt, alle Änderungen und Erweiterungen am Quellcode unter denselben Bedingungen offenzulegen.
   - Schachvereine haben damit die formale Garantie, ihre Daten und die Software unabhängig weiterführen zu können (Verhinderung von Vendor Lock-in).

2. **Geschäftsmodell: Managed Hosting auf [Schachverwaltung.de](https://schachverwaltung.de):**
   - Das kommerzielle Angebot monetarisiert nicht die Software-Lizenz, sondern **Betriebssicherheit, Zeiteinsparung und Komfort**.
   - Gemäß [ADR-014](ADR-014-preisgestaltung.md) und [ADR-025](ADR-025-hosting-eu-ebene-scalingo.md) erhalten Kunden auf Schachverwaltung.de eine isolierte Vereinsinstanz im europäischen Rechenzentrum inklusive automatisierten Restic-Backups, Uptime-Monitoring, 2FA-Infrastruktur und regelmäßigen Sicherheitsupdates.

3. **Klare Support-Abgrenzung (Community vs. Managed Service):**
   - **Self-Hosting (Open Source):** Technisch versierte Vereine können das System eigenständig per Docker Compose betreiben ([docs/deployment.md](../deployment.md)). Der Support hierfür erfolgt ausschließlich auf freiwilliger Community-Basis über öffentliche GitHub Discussions / Issues. Es besteht kein Anspruch auf individuellen Support bei Server-, Netzwerk- oder SMTP-Problemen.
   - **Managed Hosting:** Abonnenten auf Schachverwaltung.de erhalten zugesicherten Vorstandssupport (E-Mail/Tickets), Übernahme des Systembetriebs, automatische Migrationen sowie Hilfe bei der Erstinbetriebnahme.

## Consequences

- **Hohe Glaubwürdigkeit:** Vollständige Transparenz bei DSGVO-Prüfungen, Kassenbuch-Revisionen und Sicherheitsaudits durch offengelegten Code.
- **Konvertierungshebel durch Dokumentation:** Die ausführliche Dokumentation für den Eigenbetrieb ([docs/deployment.md](../deployment.md)) verdeutlicht ehrenamtlichen Vorständen transparent den tatsächlichen administrativen Wartungsaufwand, wodurch die Managed-Tarife (10–25 €/Monat) wirtschaftlich attraktiv und nachvollziehbar bleiben.
- **Kein Support-Burnout:** Eindeutige vertragliche und kommunikative Trennung zwischen freier Software-Nutzung und bezahlter Betriebs- und Support-Dienstleistung im Repository und auf der Marketing-Site.
