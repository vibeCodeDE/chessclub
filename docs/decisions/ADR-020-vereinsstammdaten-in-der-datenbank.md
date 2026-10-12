# ADR-020: Vereinsstammdaten & Setup-Assistent in der Datenbank

## Status
Accepted (erweitert und löst [ADR-012](ADR-012-vereinsprofil-in-den-settings.md) ab)

## Date
2026-10-12

## Context
In [ADR-012](ADR-012-vereinsprofil-in-den-settings.md) wurde entschieden, das Vereinsprofil (`CLUB_NAME`, `CLUB_SHORT`, `CLUB_CONTACT` etc.) ausschließlich in Umgebungsvariablen (`.env`) und Django-Settings zu führen, um eine zusätzliche Datenbank-Tabelle zu vermeiden.

In der Praxis – insbesondere beim Cloud- und PaaS-Deployment (z. B. Scalingo, Docker) sowie bei der Ersteinrichtung durch Vorstände – erweist sich dieser Ansatz als starr:
- Vereinsvorstände haben keinen direkten Zugriff auf Server-Konfigurationsdateien oder PaaS-Dashboards, um Tippfehler, geänderte Spielabendzeiten, neue Spiellokale oder die SEPA-Gläubiger-ID anzupassen.
- Bei der Inbetriebnahme mit echten Vereinsdaten (Ablösung der Dummy-Daten) müssen neben dem Vereinsprofil auch Beitragskategorien, Mannschaften und Mitglieder (aus Alt-Excel-/CSV-Dateien) strukturiert und fehlerfrei eingepflegt werden können.
- Reine Umgebungsvariablen bieten keine Validierung und keine DSGVO-konforme AuditLog-Protokollierung von Datenänderungen.

## Decision
1. **Singleton-Modell `ClubProfile` in `core/models.py`:**
   - Ein dediziertes Modell mit `pk=1` speichert die Stammdaten des Vereins:
     - Name, Kurzname, Kontakt-E-Mail, Gründungsjahr, Ort
     - Spiellokal, Spielabend-Zeiten (Erwachsene), Trainingszeiten (Jugend), Kurzbeschreibung
     - SEPA-Gläubiger-ID, Gläubiger-Name, Vereins-IBAN, Vereins-BIC
   - **Transparenter Fallback:** Wenn ein Feld im Datenbank-Profil leer ist oder noch kein Datensatz angelegt wurde, greift `ClubProfile.get_solo()` automatisch auf die Settings (`settings.CLUB_*` und `settings.SEPA_*`) zurück. Bestehende Deployments und Tests bleiben voll abwärtskompatibel.
   - `core/context_processors.py`, Mahnbriefe und SEPA-Export beziehen die Daten primär aus `ClubProfile.get_solo()`.

2. **Webbasierter Einrichtungs- & Import-Assistent (`/verein/setup/`):**
   - Ausschließlich für die Vorstandsgruppe (`@role_required(ADMIN_GROUP)`).
   - Vier geführte Abschnitte:
     - **Profil & Stammdaten:** Formular zur Pflege aller Vereins- und Gläubigerdaten inklusive AuditLog-Aufzeichnung.
     - **Beitragskategorien:** Übersicht und Schnellpflege von Kategorien (`FeeCategory`) und Jahresbeträgen (`FeeAmount`).
     - **Mannschaften:** Schnellpflege der Mannschaften (`Team`) und Ligen.
     - **Mitglieder-Import:** CSV-Upload mit Muster-Download, robuster Spaltenerkennung (Semikolon/Komma, UTF-8/Latin1), interaktivem Validierungs-Check (Dry-Run) und atomarer Übernahme in `Member` sowie verschlüsseltem `SepaMandate`.

3. **CLI-Management-Command (`import_members`):**
   - Ermöglicht den Skript- oder One-Off-Container-Import (z. B. `scalingo run python manage.py import_members datei.csv`) mit denselben Validierungsregeln wie die Web-Oberfläche.

## Consequences
- Vorstände können echte Vereinsdaten direkt im Web-Interface hinterlegen und aktualisieren, ohne Container neu zu starten oder Umgebungsvariablen anzupassen.
- Einfacher Onboarding-Pfad für Vereine: CSV hochladen, prüfen, übernehmen.
- Hohe Datensicherheit: Bankverbindungen von Mitgliedern werden nach wie vor mit Fernet verschlüsselt (ADR-010); Profiländerungen werden im AuditLog protokolliert (PRD N1.5).
