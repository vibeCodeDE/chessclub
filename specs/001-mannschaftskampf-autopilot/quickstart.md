# Quickstart & Verification Guide: Mannschaftskampf-Autopilot

**Feature**: `001-mannschaftskampf-autopilot` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

---

## Voraussetzungen & Testumgebung

- Docker Compose Umgebung läuft oder lokale PostgreSQL-/SQLite-Testumgebung.
- Mindestens 1 Verein mit mindestens 2 Mannschaften (z. B. „1. Mannschaft“ und „2. Mannschaft“) und Mitgliedern (über `manage.py seed_demo` vorhanden).

---

## Validierungsszenario 1: Meldelisten-Import (CSV / Excel)

### Ziel
Nachweis, dass offizielle Rang- und Meldelisten eingelesen, validiert und mit bestehenden Mitgliedern verknüpft werden (FR-001).

### Ablauf
1. Erstelle eine Test-CSV `meldeliste_test.csv`:
   ```csv
   mannschaft,rang,brett,nachname,vorname
   1. Mannschaft,1,1,Mustermann,Max
   1. Mannschaft,2,2,Schmidt,Bernd
   1. Mannschaft,3,3,Müller,Anton
   1. Mannschaft,4,4,Weber,Michael
   1. Mannschaft,5,5,Wagner,Thomas
   1. Mannschaft,6,6,Becker,Lisa
   1. Mannschaft,7,7,Schulz,Clara
   1. Mannschaft,8,8,Sommer,Klaus
   2. Mannschaft,1,1,Meier,Julian
   2. Mannschaft,2,2,Graf,Maximilian
   ```
2. Login als Vorstand/Admin im Browser und Aufruf von `/spielbetrieb/meldeliste/import/`.
3. Datei hochladen mit aktiviertem `Dry-Run`:
   - **Erwartetes Ergebnis**: Vorschau zeigt 10 zugeordnete Spieler, 0 Fehler.
4. Import verbindlich ausführen (`Dry-Run` deaktiviert):
   - **Erwartetes Ergebnis**: Statusmeldung „Meldeliste mit 10 Spielern erfolgreich importiert.“ Die Roster-Tabelle zeigt die Stammbretter 1 bis 8 der 1. Mannschaft.

---

## Validierungsszenario 2: 10-Tage-Verfügbarkeitsabfrage & Magic Link

### Ziel
Nachweis, dass Magic-Links ohne Login generiert werden und Spieler per 1-Klick Zu-/Absage einreichen können (FR-002, FR-003, SC-005).

### Ablauf
1. Lege ein Ligaspiel an, das 10 Tage in der Zukunft liegt:
   ```bash
   docker compose exec app python manage.py process_match_queries
   ```
2. **Erwartetes Ergebnis**: Eine `MatchAvailabilityQuery` und 8 `PlayerAvailability`-Einträge mit generierten Tokens werden angelegt. E-Mails an Stammspieler werden verschickt.
3. Kopiere den Magic-Link für Brett 4 (`/spielbetrieb/rueckmeldung/<token>/`) und öffne ihn in einem privaten/inkognito Browserfenster (ohne Login):
   - **Erwartetes Ergebnis**: Formular öffnet sich ohne Passwortabfrage.
4. Klicke auf `[Kann nicht]`:
   - **Erwartetes Ergebnis**: Rückmeldung wird als „abgesagt“ erfasst. Das Mannschaftsführer-Cockpit zeigt Brett 4 sofort rot als vakant/abgesagt.

---

## Validierungsszenario 3: Ersatzspieler-Ermittlung & Festspiel-Warnung

### Ziel
Nachweis, dass regelkonforme Ersatzspieler aus unteren Mannschaften vorgeschlagen werden und die Festspielwarnung korrekt greift (FR-005, FR-006).

### Ablauf
1. Als Mannschaftsführer das betroffene Spiel im Spielbetriebs-Dashboard öffnen.
2. Bei Brett 4 auf `[Ersatz suchen]` klicken:
   - **Erwartetes Ergebnis**: Das System schlägt automatisch die Spieler der 2. Mannschaft in der Rangreihenfolge vor.
3. Für einen Testspieler (z. B. Bernd Schmidt), der bereits 2 Einsätze in höheren Mannschaften hat:
   - **Erwartetes Ergebnis**: Eine deutliche, gelb/rote Festspielwarnung erscheint: *„Achtung: Wenn Schmidt heute in der 1. spielt, ist er dort festgespielt!“*.
4. Der Mannschaftsführer kann einzelne Kandidaten per Checkbox abwählen und klickt auf `[Ersatzanfrage senden]`.
   - **Erwartetes Ergebnis**: Anfrage wird erzeugt. WhatsApp Click-to-Chat-Link (`wa.me`) und E-Mails werden generiert.

---

## Validierungsszenario 4: First-Come-First-Serve Zusage (Transaktionssicherheit)

### Ziel
Nachweis, dass der erste Klick den Platz sichert und nachfolgende Klicks konfliktfrei abgewiesen werden (FR-008, SC-004).

### Ablauf
1. Öffne den Ersatz-Magic-Link von Kandidat 1 in Browserfenster A.
2. Öffne den Ersatz-Magic-Link von Kandidat 2 in Browserfenster B.
3. In Fenster A auf `[Ich springe ein!]` klicken:
   - **Erwartetes Ergebnis**: Bestätigung: *„Du bist an Brett 4 aufgestellt!“*. In der Spielaufstellung ist Kandidat 1 als Brett 4 eingetragen.
4. Direkt danach in Fenster B auf `[Ich springe ein!]` klicken:
   - **Erwartetes Ergebnis**: Freundliche Meldung: *„Vielen Dank für deine Bereitschaft! Der Platz wurde bereits von [Vorname von Kandidat 1] besetzt.“*. Keine Fehlerseite, keine inkonsistente Doppelbelegung.

---

## Validierungsszenario 5: Fahrgemeinschaften bei Auswärtsspielen

### Ziel
Nachweis, dass Fahrbedarfe und Plätze bei Auswärtsspielen aggregiert werden (FR-009, US 5).

### Ablauf
1. Bei einem Auswärtsspiel antwortet Spieler A über seinen Magic Link: *„Bin dabei“* + *„Fahre selbst (3 freie Plätze)“*.
2. Spieler B antwortet: *„Bin dabei“* + *„Brauche Mitfahrgelegenheit“*.
3. Im Mannschaftsführer-Cockpit die Spielansicht öffnen:
   - **Erwartetes Ergebnis**: Ampel zeigt grün: *„Fahrgemeinschaften: 3 Plätze für 1 Suchenden (Puffer: +2 Plätze)“*. Spieler A ist als Fahrer mit Telefonnummer gelistet.

---

## Automatisierte Tests ausführen

```bash
docker compose exec app pytest teams/tests/test_autopilot.py -v
```

Alle Unittests, Rollentests (§3.8 Matrix), Negativtests (abgelaufenes Token, Doppelbesetzung, unberechtigter Zugriff) und Service-Tests müssen fehlerfrei durchlaufen.
