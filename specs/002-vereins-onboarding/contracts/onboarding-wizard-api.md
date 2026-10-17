# Interface Contract: Onboarding Wizard

**Bereich**: Web UI & Server-Endpoints  
**Basis-URL**: `/onboarding/`  
**Berechtigung**: Nur Rolle `admin` (`@role_required(ADMIN_GROUP)`)  
**Format**: Server-Side Rendered HTML (Django Templates) mit responsivem Layout (360 px / 1280 px)  

---

## 1. Routen-Übersicht

| Route | HTTP-Methode | Name | Zweck |
|---|---|---|---|
| `/onboarding/` | GET | `core:onboarding_wizard` | Einstiegspunkt; leitet automatisch auf den aktuellen offenen Schritt weiter |
| `/onboarding/schritt/1/` | GET / POST | `core:onboarding_step_1` | Schritt 1: Vereinsidentität & Spielabendzeiten |
| `/onboarding/schritt/2/` | GET / POST | `core:onboarding_step_2` | Schritt 2: Modulauswahl (Satellitenmodule) |
| `/onboarding/schritt/3/` | GET / POST | `core:onboarding_step_3` | Schritt 3: Beitragsstruktur (Vorlagen & Sätze) |
| `/onboarding/schritt/4/` | GET / POST | `core:onboarding_step_4` | Schritt 4: Mitglieder-Datenübernahme (ZPS / CSV) |
| `/onboarding/schritt/5/` | GET / POST | `core:onboarding_step_5` | Schritt 5: Funktionäre einladen |
| `/onboarding/schritt/6/` | GET / POST | `core:onboarding_step_6` | Schritt 6: Zusammenfassung & Produktivstart |
| `/onboarding/zurueck/<int:schritt>/` | GET | `core:onboarding_step_back` | Navigiert zu einem vorherigen, bereits erledigten Schritt |

---

## 2. Endpunkt-Spezifikationen

### 2.1 Schritt 1: Vereinsidentität (`/onboarding/schritt/1/`)

#### GET
- Rendert das Formular für die Grunddaten des Vereins.
- **Kontext**:
  - `form`: `ClubProfileForm` (vorbelegt mit `ClubProfile.get_solo()`)
  - `aktueller_schritt`: `1`
  - `schritte_anzahl`: `6`
  - `fortschritt_prozent`: `16`

#### POST
- Validiert Eingaben und speichert in `ClubProfile`.
- **Felder**: `name` (Pflicht), `kurzname` (Pflicht), `zps_nummer` (optional, 5 Stellen), `kontakt_email` (Pflicht), `ort`, `spiellokal`, `spielabend_zeiten`, `jugend_zeiten`.
- **Erfolg**: Schreibt `AuditLog`, markiert Schritt 1 als erledigt (`OnboardingProgress`), setzt `aktueller_schritt = 2` und führt Redirect nach `/onboarding/schritt/2/`.
- **Fehler**: HTTP 200 mit Inline-Fehlermeldungen nach WCAG 2.1 AA.

---

### 2.2 Schritt 2: Modulauswahl (`/onboarding/schritt/2/`)

#### GET / POST
- Erlaubt das Aktivieren/Deaktivieren der Satellitenmodule (`spielbetrieb_aktiv`, `turniere_aktiv`, `kassenbuch_aktiv`, `nachrichten_aktiv`).
- Speichert in `ModuleSettings.get_solo()`.
- **Erfolg**: Schreibt `AuditLog`, markiert Schritt 2 als erledigt, Redirect nach `/onboarding/schritt/3/`.

---

### 2.3 Schritt 3: Beitragsstruktur (`/onboarding/schritt/3/`)

#### GET
- Zeigt vorhandene Beitragskategorien und bietet die 1-Klick-Aktion „Standard-Kategorien anlegen“ (`DEFAULT_FEE_CATEGORIES`) sowie ein Schnellformular für individuelle Beitragssätze.

#### POST (Aktion: Vorlagen übernehmen)
- Parameter: `action=apply_defaults`
- Erzeugt Standardkategorien mit Jahresbeträgen für das aktuelle Jahr, falls noch keine Kategorien existieren.
- **Erfolg**: Erfolgsmeldung via Django Messages, Reload von Schritt 3.

#### POST (Aktion: Weiter)
- Parameter: `action=next`
- Prüft, ob mindestens eine Beitragskategorie angelegt ist (oder erlaubt explizites Überspringen für reine Spielgemeinschaften ohne Beiträge).
- **Erfolg**: Markiert Schritt 3 als erledigt, Redirect nach `/onboarding/schritt/4/`.

---

### 2.4 Schritt 4: Mitglieder-Datenübernahme (`/onboarding/schritt/4/`)

Bietet die Hybrid-Auswahl gemäß Benutzerentscheidung:

#### POST (Aktion A: ZPS-Direktimport)
- Parameter: `action=import_zps`, `zps_nummer` (z. B. `C0101`).
- Führt `import_dsb_initial(zps_nummer, user=request.user)` aus.
- **Erfolg**: JSON/HTML-Meldung: „X spielberechtigte Mitglieder erfolgreich aus dem DSB-Wertungsportal importiert.“

#### POST (Aktion B: CSV-Upload & Dry-Run)
- Parameter: `action=validate_csv` oder `action=execute_csv`, `csv_datei` (File-Upload).
- Nutzt `parse_members_csv` und `execute_members_import`.
- **Erfolg**: Zeigt Dry-Run-Ergebnis bzw. Vollzugsmeldung.

#### POST (Aktion C: Überspringen / Manuelle Anlage)
- Parameter: `action=skip`
- Markiert Schritt 4 als erledigt, Redirect nach `/onboarding/schritt/5/`.

---

### 2.5 Schritt 5: Funktionäre einladen (`/onboarding/schritt/5/`)

#### GET
- Listet bisher ausgesprochene Einladungen (`StaffInvitation`) mit Status (`offen`, `angenommen`, `abgelaufen`) und zeigt das Einladungsformular.

#### POST (Einladung erstellen)
- Felder: `email`, `vorname`, `nachname`, `rolle` (`admin` oder `kapitaen`).
- Erzeugt `StaffInvitation` mit Token und versendet Einladungs-Mail.
- Zeigt in der UI den generierten Link an (Kopierfunktion).

#### POST (Schritt abschließen)
- Parameter: `action=next`
- Markiert Schritt 5 als erledigt, Redirect nach `/onboarding/schritt/6/`.

---

### 2.6 Schritt 6: Zusammenfassung & Produktivstart (`/onboarding/schritt/6/`)

#### GET
- Zeigt eine aggregierte Übersicht aller hinterlegten Daten (Vereinsname, aktive Module, Anzahl Beitragssätze, Anzahl importierter Mitglieder, eingeladene Funktionäre).
- Prüft, ob Demo-Daten aktiv sind (`core.services.get_demo_data_status()`). Falls ja, wird ein prominenter Bereinigungsschalter angezeigt.

#### POST (Produktivstart bestätigen)
- Parameter: `cleanup_demodata=1` (optional, falls Demo-Daten noch vorhanden).
- Setzt `OnboardingProgress.ist_abgeschlossen = True`, `abgeschlossen_am = now()`, `abgeschlossen_von = request.user`.
- Schreibt abschließenden `AuditLog`-Eintrag.
- **Redirect**: Führt direkt zum Haupt-Dashboard (`core:dashboard`) mit Willkommens-Meldung.

---

## 3. Sicherheits- und Rollenregeln

- Jeder Aufruf prüft `@role_required(ADMIN_GROUP)`.
- Benutzer mit Rollen `kapitaen`, `mitglied` oder `gast` erhalten HTTP 403 Forbidden.
- Unangemeldete Besucher erhalten HTTP 302 Redirect zur Anmeldeseite (`/anmelden/?next=/onboarding/`).
