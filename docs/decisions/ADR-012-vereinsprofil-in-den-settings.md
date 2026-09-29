# ADR-012: Vereinsprofil in den Settings statt in einer eigenen App

## Status
Accepted (setzt Entscheidung Nr. 3 des T10-Designs außer Kraft; das Design-Dokument bleibt als_historie im Repo)

## Date
2026-09-29

## Context
Der Mahnbrief, die Kopfzeile aller Seiten und der Absender der Gruppen-Mails brauchen dieselben Angaben: Name des Vereins, Kurzname, Kontaktadresse. Der T10-Entwurf legte dafür eine eigene Mini-App `verein` mit einem einzigen Model an, dessen `save()` genau einen Datensatz garantiert, und ausdrücklich nicht in `dues` und nicht in den Settings.

Beim Zusammenführen der beiden Zweige (2026-09-29) kam eine Umsetzung herein, die dieselben Angaben als Settings-Variablen führt (`CLUB_NAME`, `CLUB_SHORT`, `CLUB_CONTACT`), von einem Kontext-Processor in jedes Template gespiegelt und im Mahnbrief direkt gelesen. Die App `verein` ist überflüssig.

## Decision
- **Das Vereinsprofil kommt aus den Settings** (`CLUB_NAME`, `CLUB_SHORT`, `CLUB_CONTACT`, `DEFAULT_FROM_EMAIL`) und wird über `core/context_processors.py` bereitgestellt. Es wird in `.env.prod` bzw. `.env.prod.example` gepflegt.
- **Keine eigene App `verein`.** Für genau einen Datensatz wäre ein Model mit eigener Migration, Admin und Löschschutz unverhältnismäßig; zusätzlich gäbe es zwei Wahrheiten (Settings und Datenbank), die auseinanderlaufen können.
- **Der Mahnbrief liest dieselbe Quelle** wie die Seitenkopfzeile — damit kann der Brief nicht einen anderen Absender nennen als das Portal.
- Aus demselben Grund fließen die Vereinsdaten **nicht** nach `dues` (fachfremd) und **nicht** in `members` (personenbezogen, aber nicht Mitgliederdatum).

## Alternatives Considered

### Eigene App `verein` (T10-Entwurf)
- Pros: über die Oberfläche pflegbar, ohne Dateiänderung; hält Änderungen der Kontaktdaten im Betrieb nachvollziehbar.
- Cons: ein Model für eine Zeile, zusätzliche Migration, und die Daten stehen als Kontaktdaten in der Datenbank statt in der Konfiguration. Bei einem Verein mit < 200 Mitgliedern ändert sich am Absender alle paar Jahre etwas.
- Rejected: der Pflegeaufwand über die Konfiguration ist kleiner als der Pflegeaufwand für eine eigene App.

### Kontaktdaten im `Member`-Datensatz duplizieren
- Rejected: der Verein hat genau eine Absenderadresse; sie gehört nicht in den Mitgliederdatensatz.

### Später in einen `Vereinsdaten`-Datensatz mit Verlauf
- Deferred: erst sinnvoll, wenn Adressänderungen protokolliert werden müssen. Der Mailversand protokolliert bereits Zeitpunkt und Empfänger, das genügt.

## Consequences
- Die App `verein/` und ihre Migration sind aus dem Baum entfernt; die Vereinsdaten werden in den Testumgebungen über die Settings gesetzt.
- Änderungen am Absender brauchen einen Neustart bzw. einen Deploy — für einen Verein dieser Größe die richtige Größenordnung.
- Die T10-Spec (`docs/superpowers/specs/2026-09-29-t10-mahnwesen-export-design.md`) beschreibt in Entscheidung Nr. 3 die alte Lösung. Sie bleibt unverändert im Repo; dieses ADR ist die gültige Quelle.
