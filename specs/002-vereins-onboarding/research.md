# Phase 0: Research & Technical Decisions: Vereins-Onboarding

**Feature**: Onboarding für einen neuen Schachverein (`002-vereins-onboarding`)  
**Datum**: 2026-10-16  
**Status**: Completed  

---

## 1. Wizard-Architektur & Zustandsverwaltung

### Fragestellung
Wie wird der mehrstufige Onboarding-Prozess (`/onboarding/`) architektonisch aufgebaut, damit der Zustand sicher über HTTP-Requests, Browser-Wechsel und Unterbrechungen hinweg erhalten bleibt?

### Entscheidung
- **Modell-gestütztes Singleton `OnboardingProgress` in `core/models.py` (`pk=1`):**
  - Speichert den aktuellen Schritt (`aktueller_schritt`), eine Liste abgeschlossener Schritte (`schritte_abgeschlossen` als JSON-Feld), den Abschluss-Status (`ist_abgeschlossen`), Abschluss-Zeitstempel und das Ausblend-Flag für das Dashboard-Widget (`checklist_ausgeblendet`).
  - Jeder Schritt speichert seine Daten sofort atomar in den jeweiligen Fachmodellen (`ClubProfile`, `ModuleSettings`, `FeeCategory`, `Member`, `StaffInvitation`).
  - Dadurch ist kein volatiles Session-Form-Multi-Step-Management nötig; ein Abbruch oder Reload führt den Administrator exakt an die zuletzt bearbeitete Stelle zurück (Edge-Case-Anforderung).

### Begründung
- Entspricht der bestehenden Singleton-Architektur aus ADR-019 (`ModuleSettings`) und ADR-020 (`ClubProfile`).
- Vollkommen zustandssicher: Daten gehen bei Browser-Crash oder Rechnerwechsel nicht verloren.
- Dünne Function-Based Views (FBV) bleiben einfach testbar und frei von komplexen Session-State-Bugs.

### Verworfene Alternativen
- *Django FormWizard (`django-formtools`)*: Fügt eine externe Abhängigkeit hinzu, speichert Zwischenzustände standardmäßig in der Session (Datenverlust bei Session-Ablauf) und erschwert die schrittweise Persistierung in getrennte relationale Modelle.
- *Reines Client-Side-SPA-Routing*: Widerspricht ADR-001 / PRD §2 (Server-seitig gerenderte Django-Templates ohne SPA-Buildschritt).

---

## 2. Erst-Redirect-Mechanismus für neue Instanzen

### Fragestellung
Wie werden Administratoren bei einer frischen Installation oder unvollständigem Vereinsprofil zuverlässig in den Onboarding-Assistenten geleitet (FR-004), ohne Endlosschleifen oder Behinderungen von Logout/Passwortänderung zu erzeugen?

### Entscheidung
- **Zweistufiger Einstieg ohne invasive Global-Middleware:**
  1. **Login-Handler (`core/auth_views.py`):** Nach erfolgreicher Authentifizierung (und ggf. 2FA) prüft die View, ob der Benutzer der Vorstandsgruppe (`ADMIN_GROUP`) angehört, kein expliziter Zielpfad (`next`) vorliegt und `OnboardingProgress.get_solo().ist_abgeschlossen` noch `False` ist. Trifft dies zu, erfolgt der Redirect nach `core:onboarding_wizard`.
  2. **Dashboard-View (`core/views.py:dashboard`):** Ruft ein Admin das Dashboard auf und `ist_abgeschlossen` ist `False` bei noch leerem Vereinsnamen (`profil.name == ""`), leitet das Dashboard automatisch auf `/onboarding/` um.
- Logout (`/abmelden/`), Passwortänderung, Profil-Selbstbedienung und statische Ressourcen sind von Redirects ausgeschlossen.

### Begründung
- Verhindert das Risiko von zirkulären Redirects (Redirect Loops), wie sie bei generischen Middlewares für jeden Request auftreten können.
- Schützt unbefugte Rollen (`mitglied`, `kapitaen`, `gast`): Diese werden niemals in das Onboarding geleitet und erhalten auf `/onboarding/` strikt einen HTTP 403 Forbidden.

### Verworfene Alternativen
- *Globale Onboarding-Middleware*: Führt bei jeder Anfrage zu Datenbank-Lookups und erfordert eine fehleranfällige Whitelist von ausgenommenen URLs (Static, Media, Auth, Health-Checks).

---

## 3. Hybrid-Datenübernahme (ZPS-Direktabruf & CSV-Import)

### Fragestellung
Wie wird die Benutzerentscheidung (Q1: Option A) für die Hybrid-Auswahl im Schritt „Datenübernahme“ technisch elegant und wartbar umgesetzt?

### Entscheidung
- **Wiederverwendung und Kapselung vorhandener Fachservices:**
  - **Pfad A (ZPS-Direktabruf):** Nutzung des bestehenden Services `members.services.dsb_sync`. Ergänzung einer reinen Servicefunktion `import_dsb_initial(vkz, user=None)`:
    - Ruft die offizielle DSB-Vereinsliste ab (`fetch_dsb_vereinsliste(vkz)`).
    - Legt alle im DSB geführten aktiven Spieler als `Member`-Datensätze mit Status `aktiv`, Vorname, Nachname, Geburtsjahrgang, DWZ, DWZ-Index und `fide_id` atomar an (`transaction.atomic`).
    - Gibt einen strukturierten Erfolgsbericht (Anzahl importierter Spieler, übersprungene Dubletten) zurück.
  - **Pfad B (CSV-Upload):** Nutzung des bewährten `members.services.import_service` (aus T31 / ADR-020):
    - Automatische Erkennung von Kodierung (UTF-8, Latin-1) und Delimitern (Komma, Semikolon).
    - Dry-Run-Validierung mit tabellarischer Vorschau und konkreten Fehlerhinweisen.
    - Atomare Übernahme inklusive verschlüsselter `SepaMandate`-Erzeugung (Fernet, ADR-010).

### Begründung
- Nutzt 100 % des vorhandenen, getesteten Codes (`dsb_sync` und `import_service`). Keine Code-Duplizierung, maximale Robustheit.
- Beide Pfade protokollieren lückenlos im `AuditLog`.

### Verworfene Alternativen
- *Direkter Verbandsschreibzugriff*: Verband (DSB/nuLiga) bietet keine Schreib-API (siehe ADR-016).
- *Manueller Einzeldatensatz-Zwang*: Für ehrenamtliche Vorstände mit 50–150 Mitgliedern unzumutbar.

---

## 4. Funktionärseinladungs-System (`StaffInvitation`)

### Fragestellung
Wie werden Vorstandskollegen und Mannschaftsführer sicher und barrierefrei per E-Mail eingeladen, sodass sie ihr Passwort selbst festlegen (Q3: Option A)?

### Entscheidung
- **Modell `StaffInvitation` in `core/models.py`:**
  - Felder: `email`, `vorname`, `nachname`, `rolle` (`admin` oder `kapitaen`), `token` (`secrets.token_urlsafe(32)`), `gueltig_bis` (7 Tage), `status` (`offen`, `angenommen`, `abgelaufen`), `eingeladen_von` (FK User).
- **Service-Funktionen in `core/services.py`:**
  - `create_staff_invitation(email, vorname, nachname, rolle, invited_by, send_mail=True)`: Erzeugt das Token, speichert die Einladung und versendet die E-Mail mit personalisiertem Link `/einladung/<token>/`.
  - `accept_staff_invitation(token, passwort)`: Prüft Gültigkeit und Status, legt den Django-`User` an (oder verknüpft ein vorhandenes Mitglied), weist die Gruppe (`admin` oder `kapitaen`) zu, setzt das Passwort und markiert die Einladung als `angenommen`.
- **Rückfallebene bei fehlendem SMTP-Versand:**
  - In der UI wird der generierte Einladungslink nach dem Anlegen zusätzlich direkt in der Maske angezeigt (mit 1-Klick-Kopierbutton), falls der Mailserver in Test-/Dev-Umgebungen noch nicht aktiv ist.

### Begründung
- Höchste Sicherheit: Keine Übertragung von Klartext-Initialpasswörtern.
- Erfüllt PRD §3.8: Die Berechtigungsgruppe wird bei Annahme automatisch gesetzt.
- Entlastet den Vorstand: Kolleginnen und Kollegen vergeben ihr Wunschpasswort selbst.

### Verworfene Alternativen
- *Vorgefertigtes Benutzerkonto mit Initialpasswort im Klartext*: Unsicher bei unverschlüsselter E-Mail-Übertragung.
- *Nutzung von Standard-Password-Reset-Tokens für nicht existierende Benutzer*: Djangos `default_token_generator` benötigt zwingend einen bereits existierenden `User`-Datensatz mit Passwort-Hash.

---

## 5. Dashboard „Erste Schritte“-Widget (Getting Started Tracker)

### Fragestellung
Wie ermittelt das Vorstandsdashboard dynamisch und performant den Erledigungsstatus der Onboarding-Aufgaben, ohne N+1-Abfragen zu erzeugen?

### Entscheidung
- **Service-Funktion `get_onboarding_checklist_status(user=None)` in `core/services.py`:**
  - Führt wenige gezielte Aggregat-Queries aus:
    1. `ClubProfile.get_solo()`: Prüft, ob Name, Spiellokal und Kontakt-E-Mail gepflegt sind.
    2. `FeeCategory.objects.exists()`: Prüft, ob Beitragskategorien definiert sind.
    3. `Member.objects.filter(status="aktiv").count()`: Prüft, ob mindestens 1 aktives Mitglied existiert.
    4. `Team.objects.exists()`: Prüft, ob mindestens 1 Mannschaft existiert.
    5. `StaffInvitation.objects.exists() or User.objects.filter(groups__name=ADMIN_GROUP).count() > 1`: Prüft, ob Funktionäre eingeladen oder mehrere Admins vorhanden sind.
  - Berechnet Gesamtanzahl (z. B. 5), erledigte Anzahl (z. B. 4) und Prozentwert für den Fortschrittsbalken.
  - Prüft `OnboardingProgress.get_solo().checklist_ausgeblendet`: Wenn `True`, wird das Widget nicht gerendert.
- **1-Klick-Ausblendung:** POST-Route `/onboarding/checklist/ausblenden/` setzt `checklist_ausgeblendet = True`.

### Begründung
- Die Prüfung basiert auf echten Datenbank-Zuständen, nicht nur auf gesetzten Häkchen.
- Gesamte Abfrage benötigt maximal 4 schnelle `EXISTS`/`COUNT`-Queries (`assertNumQueries` im Test garantiert eingehalten).
- Erfüllt WCAG 2.1 AA: Semantischer Fortschrittsbalken mit `aria-valuenow`, `aria-valuemin`, `aria-valuemax` und barrierefreiem Text.
