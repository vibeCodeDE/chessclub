# Quickstart & Validation Guide: Vereins-Onboarding

**Feature**: Onboarding für einen neuen Schachverein (`002-vereins-onboarding`)  
**Fokus**: End-to-End-Validierungsszenarien und Abnahmetests  

---

## 1. Vorbedingungen & Test-Setup

```bash
# Testumgebung vorbereiten
docker compose exec app pytest core/tests/test_club_profile.py

# Optional: Datenbank für einen sauberen Testlauf zurücksetzen oder Testdatenbank nutzen
docker compose exec app python manage.py migrate
```

---

## 2. Validierungsszenarien

### Szenario 1: Erst-Login als Administrator führt zum Onboarding (FR-004)
1. **Ausgangslage**: `ClubProfile.get_solo().name` ist leer, `OnboardingProgress.get_solo().ist_abgeschlossen` ist `False`.
2. **Aktion**: Anmeldung als Benutzer mit Gruppe `admin` (`/anmelden/`).
3. **Erwartetes Ergebnis**:
   - HTTP 302 Redirect zu `/onboarding/schritt/1/`.
   - Der Administrator sieht die Begrüßungsseite mit Schrittindikator (Schritt 1 von 6).

---

### Szenario 2: Schritt 1 – Vereinsstammdaten & Verbandsschlüssel
1. **Aktion**: Eingabe von:
   - Vereinsname: `Schachclub Matt 2026 e.V.`
   - Kurzname: `SC Matt 2026`
   - ZPS-Nummer: `C0101`
   - Kontakt-E-Mail: `kontakt@sc-matt.de`
   - Spiellokal & Zeiten: `Bürgerhaus Raum 3, Fr 19:30`
2. **Klick**: „Weiter zu Schritt 2“.
3. **Erwartetes Ergebnis**:
   - Daten in `ClubProfile` gespeichert.
   - `OnboardingProgress.aktueller_schritt` steht auf `2`.
   - `AuditLog` verzeichnet Profil-Aktualisierung.

---

### Szenario 3: Schritt 2 – Modulauswahl
1. **Aktion**: Kassenbuch und Turniere aktiv lassen, Kommunikation deaktivieren.
2. **Klick**: „Speichern & Weiter“.
3. **Erwartetes Ergebnis**:
   - `ModuleSettings.nachrichten_aktiv` ist `False`.
   - Weiterleitung zu Schritt 3 (`/onboarding/schritt/3/`).

---

### Szenario 4: Schritt 3 – Standard-Beitragskategorien per 1-Klick
1. **Aktion**: Klick auf „Standard-Kategorien anlegen“.
2. **Erwartetes Ergebnis**:
   - Die 4 schachspezifischen Standardkategorien (Erwachsene 72 €, Jugend 36 €, Senioren 50 €, Passiv 30 €) werden angelegt.
   - Klick auf „Weiter zu Schritt 4“ führt zu `/onboarding/schritt/4/`.

---

### Szenario 5a: Schritt 4 – ZPS-Direktabruf (Hybrid-Pfad A)
1. **Aktion**: Auswahl „Aus Verband (DSB) abrufen“, Eingabe ZPS `C0101` und Klick auf „Spieler jetzt laden“.
2. **Erwartetes Ergebnis**:
   - Spieler werden aus der Verbands-Schnittstelle importiert.
   - Mitgliederliste zählt die importierten Mitglieder.
   - Klick auf „Weiter zu Schritt 5“.

---

### Szenario 5b: Schritt 4 – CSV-Import (Hybrid-Pfad B)
1. **Aktion**: Upload einer gültigen Mitglieder-CSV mit Semikolon-Trennung.
2. **Erwartetes Ergebnis**:
   - Dry-Run zeigt Vorschau der Datensätze ohne Fehler.
   - Klick auf „Mitglieder importieren“ legt die Datensätze atomar an.

---

### Szenario 6: Schritt 5 – Funktionärseinladung per E-Mail
1. **Aktion**: Eingabe von Vorname `Anna`, Nachname `Müller`, E-Mail `kasse@sc-matt.de`, Rolle `admin`.
2. **Klick**: „Einladung senden“.
3. **Erwartetes Ergebnis**:
   - `StaffInvitation` mit 7 Tagen Frist erzeugt.
   - Einladungs-Link wird in der UI angezeigt.
   - Klick auf „Weiter zu Schritt 6“.

---

### Szenario 7: Schritt 6 – Zusammenfassung & Produktivstart
1. **Aktion**: Prüfung der Zusammenfassung; Klick auf „Einrichtung abschließen & Produktivbetrieb starten“.
2. **Erwartetes Ergebnis**:
   - `OnboardingProgress.ist_abgeschlossen` wird `True`.
   - Redirect zum Vorstandsdashboard (`/dashboard/`).
   - Dashboard zeigt das „Erste Schritte“-Widget mit dem aktuellen Erledigungsstand (z. B. 4 von 5 erledigt).

---

### Szenario 8: Einladungsannahme durch Funktionär
1. **Aktion**: Aufruf des Einladungslinks `/einladung/<token>/` in einem privaten Browserfenster.
2. **Eingabe**: Benutzername `anna.kasse`, Passwort zweimal eingeben.
3. **Erwartetes Ergebnis**:
   - Neuer Benutzer wird angelegt und der Gruppe `admin` zugewiesen.
   - Benutzer ist sofort angemeldet und sieht das Admin-Dashboard.

---

### Szenario 9: Rollen- & Negativtests (PRD §3.8 / AGENTS.md)
1. **Test A (Zugriffsschutz)**: Ein Benutzer mit Rolle `mitglied` oder `kapitaen` ruft `/onboarding/` auf → **HTTP 403 Forbidden**.
2. **Test B (Gegenbuchung/Finanzschutz)**: Das Onboarding berührt niemals Kassenbuch-Löschungen.
3. **Test C (360-px-Responsivität)**: Browser auf 360 px Breite skalieren → Kein horizontaler Overflow in allen Schritten des Wizards.

---

## 3. Testausführung

```bash
# Automatisierte Tests für das Onboarding ausführen
docker compose exec app pytest core/tests/test_onboarding.py
```
