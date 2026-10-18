# Research & Architecture Decisions: Mannschaftskampf-Autopilot

**Feature**: `001-mannschaftskampf-autopilot` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

---

## 1. Magic-Link-Authentifizierung & Token-Architektur

### Kontext & Anforderung
Stamm- und Ersatzspieler müssen ohne Login, ohne Passwort und mit maximal 2 Klicks auf dem Smartphone ihre Rückmeldung abgeben können (FR-003, FR-011, SC-005). Gleichzeitig dürfen keine unberechtigten Dritten Aufstellungen manipulieren oder persönliche Profildaten ausspähen.

### Entscheidung
- **Token-Erzeugung**: `secrets.token_urlsafe(32)` generiert ein kryptografisch unvorhersehbares 256-Bit-Token.
- **Speicherung**: In der Datenbank wird ein SHA-256-Hash des Tokens gespeichert (`token_hash = hashlib.sha256(raw_token.encode()).hexdigest()`), sodass selbst bei einem Datenbank-Dump keine verwendbaren Zugangslinks vorliegen. Das rohe Token wird ausschließlich in der versandten E-Mail bzw. im `wa.me`-Link mitgegeben.
- **Gültigkeit & Lebenszyklus**:
  - Token ist an eine konkrete Abfragezeile gebunden (`PlayerAvailability` bzw. `SubRequestCandidate`).
  - Gültig ab Versand bis zum Spielbeginn (`match.datum + match.uhrzeit`).
  - Ein Klick auf den Link führt zu einer signierten, vereinfachten mobilen Antwortseite.
  - Reversible Antworten: Der Spieler kann seine Antwort vor dem Meldeschluss revidieren, solange bei Absage der Platz noch nicht an einen Ersatzspieler vergeben wurde.
- **Sicherheitsregeln**:
  - Kein Zugriff auf andere Vereinsdaten, Finanzen oder Kontaktdaten Dritter.
  - Rate-Limiting gegen Brute-Force über Django-Axes bzw. IP-Drosselung.
  - Generierung von CSRF-Token für die POST-Antwort oder idempotente Bestätigungs-Buttons.

### Verworfene Alternativen
- *Django Password-Reset-Token*: Verlangt ein verknüpftes Django `User`-Objekt. Viele Vereinsmitglieder besitzen im System jedoch kein aktives Login-Konto.
- *Signierte JWTs in der URL*: Erlauben keine serverseitige Invalidierung bei vorzeitigem Rückzug oder manueller Umbesetzung durch den Kapitän.

---

## 2. Meldelisten-Import & Datenmodell (Roster)

### Kontext & Anforderung
Einmaliger Import der offiziellen Mannschaftsmeldeliste zu Saisonbeginn (FR-001, US 2). Mannschaften (1. bis 4. Mannschaft), Stammbretter (1 bis 8) und Ersatzreihenfolge (Rang 9+ bzw. mannschaftsübergreifende Rangfolge).

### Entscheidung
- **Modell `TeamRoster` & `RosterEntry`**:
  - `TeamRoster`: Verknüpft Mannschaft, Saison (z. B. "2026/2027") und Status (aktiv/archiviert).
  - `RosterEntry`: Zuordnung `team_roster`, `member` (FK zu `Member`), `rangnummer` (z. B. 1..30), `stammbrett` (1..8 oder NULL für Ersatzspieler) und `sperre_bemerkung`.
- **Import-Format & Validierung**:
  - CSV- / Excel-Upload (`django-import-export` kompatibel bzw. leichtgewichtiger Tabellen-Parser in `teams/services.py`).
  - Pflichtspalten: `mannschaft`, `rang`, `brett`, `mitgliedsnummer_oder_name`.
  - Dry-Run-Phase: Vor dem Speichern prüft das System Mitgliederabgleich (Name/Mitgliedsnummer), zeigt Unstimmigkeiten (z. B. doppelte Rangnummer, unbekanntes Mitglied) an und verlangt Bestätigung.
- **Traceability**: Import wird im `AuditLog` mit Benutzer, Dateiname und importierter Zeilenanzahl dokumentiert.

### Verworfene Alternativen
- *Hardcoding in Python-Settings*: Nicht wartbar für Vorstände und Mannschaftsführer.
- *Web-Scraping von Verbandsportalen*: Fragil, rechtlich heikel und abhängig von wechselnden Verbands-HTML-Layouts.

---

## 3. Regelkonforme Ersatzspieler-Ermittlung & Festspiel-Regelwerk

### Kontext & Anforderung
Sagt ein Spieler ab, müssen sofort berechtigte Ersatzspieler aus tieferen Mannschaften vorgeschlagen werden (FR-005, FR-006). Dabei muss die Festspielgrenze nach DSB-Turnierordnung (TO) geprüft und visualisiert werden.

### Entscheidung
- **Reine Funktion `get_eligible_substitutes(match, target_board)` in `teams/services.py`**:
  1. **Mannschafts-Hierarchie**: Ermittelt untere Mannschaften (z. B. Spiel der 1. Mannschaft → Suche in 2., 3., 4. Mannschaft in aufsteigender Reihenfolge).
  2. **Ranglisten-Sortierung**: Kandidaten werden nach offizieller `RosterEntry.rangnummer` geordnet.
  3. **Terminkollisions-Check**: Hat die Mannschaft des Kandidaten am selben Tag zur selben Zeit ein eigenes Ligaspiel? Wenn ja, wird der Kandidat markiert („Spielt zeitgleich in Mannschaft 2“) und standardmäßig nicht vorselektiert.
  4. **Berechnung der Festspiel-Einsätze**:
     - Zählt tatsächliche Einsätze des Spielers in höheren Mannschaften der gleichen Saison (`LineupEntry.objects.filter(...)`).
     - Konfigurierbarer Schwellenwert: `team.festspiel_schwelle` (Standard: 2 freie Einsätze; ab dem 3. Einsatz festgespielt nach DSB-TO).
     - Status-Kategorisierung:
       - `GRÜN`: 0 bis `schwelle - 2` Einsätze (völlig unbedenklich).
       - `GELB` (Warnung): `schwelle - 1` Einsätze („Achtung: Letzter freier Einsatz in dieser Mannschaft!“).
       - `ROT` (Festspiel-Hinweis): Ab `schwelle` Einsätzen („Achtung: Müller ist bei Einsatz in der 1. Mannschaft dort festgespielt!“).
- **Keine N+1-Abfragen**: Alle Einsätze und Roster-Einträge werden über `select_related` und vorberechnete Aggregationen (`annotate` / `in_bulk`) geladen.

### Verworfene Alternativen
- *Strikter Ausschluss festgespielter Spieler*: In der Vereinspraxis entscheidet der Kapitän in Notlagen bewusst, einen Spieler festzuspielen, um ein kampfloses Brett zu vermeiden. Das System muss warnen, darf die Aufstellung aber nicht bevormunden (mit Audit-Protokollierung).

---

## 4. First-Come-First-Serve Concurrency & Transaktionssicherheit

### Kontext & Anforderung
Mehrere Ersatzkandidaten erhalten zeitgleich eine Anfrage. Wer zuerst klickt, erhält den Platz. Konkurrierende Zugriffe im Millisekundenbereich dürfen zu keinen doppelten Belegungen führen (FR-008, US 4, Edge Cases).

### Entscheidung
- **Transaktionssichere Vergabe**:
  ```python
  with transaction.atomic():
      sub_request = SubRequest.objects.select_for_update().get(pk=request_id)
      if sub_request.status != SubRequest.Status.OFFEN:
          # Bereits vergeben!
          return False, sub_request.akzeptiert_von
      sub_request.status = SubRequest.Status.BESETZT
      sub_request.akzeptiert_von = candidate.member
      sub_request.akzeptiert_am = timezone.now()
      sub_request.save(update_fields=["status", "akzeptiert_von", "akzeptiert_am"])
      
      # Automatische Aktualisierung des Aufstellungseintrags
      lineup_entry = sub_request.lineup_entry
      lineup_entry.member = candidate.member
      lineup_entry.save(update_fields=["member"])
  ```
- **Benutzererlebnis**:
  - Erster Klick: Sofortige Erfolgsseite („Du bist dabei an Brett 4!“).
  - Folgende Klicks: Freundliche Informationsseite („Vielen Dank für deine Hilfsbereitschaft! Der Platz wurde bereits von [Vorname] besetzt.“).

### Verworfene Alternativen
- *Optimistic Locking mit Versionsnummer*: Führt bei zeitgleichen Klicks zu Fehlermeldungen („Konflikt aufgetreten“), die für Smartphone-Nutzer verwirrend sind. Pessimistisches `select_for_update` auf Zeilenebene löst das deterministisch und geräuschlos.

---

## 5. DSGVO-konforme WhatsApp-Integration & E-Mail-Versand

### Kontext & Anforderung
Magic-Links müssen per E-Mail und WhatsApp zugestellt werden können (FR-004), ohne DSGVO-Vorgaben (N1.1) zu verletzen.

### Entscheidung
- **E-Mail (Automatisch)**:
  - Automatisierter SMTP-Versand über den Vereinstreffpunkt/Mailserver.
  - HTML- und Textfassung mit klarem Button / Link: `[Bin dabei]` / `[Kann nicht]` / `[Fahrgemeinschaft]`.
- **WhatsApp (Click-to-Chat)**:
  - Mannschaftsführer hat im Spieltags-Cockpit bei jedem Spieler und für die Sammel-Ersatzanfrage eine Schaltfläche `[Per WhatsApp senden]`.
  - Link-Format: `https://wa.me/?text=<url-encoded-nachricht>` oder `https://wa.me/<telefon>?text=...`.
  - **Datenschutz-Vorteil**: Null Server-Kommunikation mit Meta. Keine API-Kosten. Die Nachricht wird vom privaten WhatsApp-Client des Mannschaftsführers versendet, der ohnehin die Telefonnummern seiner Spieler hat.

### Verworfene Alternativen
- *Meta Business Cloud API / Twilio*: Verursacht monatliche Schnittstellenkosten, verlangt einen Meta Business Manager und überträgt Telefonnummern an US-Server (Verstoß gegen DSGVO N1.1 und AGENTS.md).

---

## 6. Automatisierter 10-Tage-Trigger

### Kontext & Anforderung
10 Tage vor dem Spieltag müssen Abfragen automatisch initiiert werden (FR-002, US 1).

### Entscheidung
- **Django Management Command `manage.py process_match_queries`**:
  - Ermittelt alle anstehenden Ligaspiele mit `datum - localdate() == 10 days` (sowie nachholende Abfragen).
  - Erzeugt idempotent die `MatchAvailabilityQuery` und die zugehörigen `PlayerAvailability`-Datensätze für alle Stammspieler des Teams.
  - Versendet E-Mails an alle Stammspieler mit gültiger E-Mail-Adresse.
  - Kann per Docker-Cronjob (z. B. täglich um 08:00 Uhr) oder manuell durch den Administrator/Kapitän über die UI (`[Abfrage jetzt starten]`) getriggert werden.

### Verworfene Alternativen
- *Celery Beat*: Benötigt Redis/RabbitMQ als Worker-Infrastruktur. Für einen kleinen Schachverein mit wenigen Spielen pro Monat unnötige Betriebs- und Wartungskomplexität.

---

## 7. Fahrgemeinschaften-Logistik

### Kontext & Anforderung
Erfassung von Fahrbedarf und freien Plätzen bei Auswärtsspielen (FR-009, US 5).

### Entscheidung
- **Felder an `PlayerAvailability`**:
  - `fahr_status`: `keine_angabe`, `brauche_mitfahrt`, `biete_mitfahrt`, `selbst_anreise`.
  - `freie_plaetze`: Positive Zahl (Standard: 0 bzw. 3 bei Biete Mitfahrt).
  - `treffpunkt_wunsch`: Kurzer Freitext (z. B. „S-Bahnhof“).
- **Aggregierte Darstellung im Dashboard**:
  - Ampel/Kachel: Benötigte Plätze vs. angebotene freie Plätze.
  - Namensliste der Fahrer mit Platzanzahl und Kontaktdaten für den Mannschaftsführer.
