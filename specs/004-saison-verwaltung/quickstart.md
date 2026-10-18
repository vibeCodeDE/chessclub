# Quickstart & Validierungsanleitung: Saisonverwaltung

**Feature**: `004-saison-verwaltung` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

---

## 1. Voraussetzungen

- Aktive Docker-Umgebung (`docker compose up -d`) oder lokale Entwicklungsumgebung mit Python 3.12 und PostgreSQL.
- Testdatenbank vorhanden; Testlauf ausgeführt über `docker compose exec app pytest`.

---

## 2. Automatisierte Validierungsszenarien

### Szenario 1: Automatische Testsuite ausführen
Beweist, dass alle Unit-, Service- und Integrationstests inkl. Rollentests und Negativtests fehlerfrei durchlaufen.

```bash
docker compose exec app pytest teams/tests/test_season.py -v
```

**Erwartetes Ergebnis**:
- 100 % grün.
- Negativtests bestätigen:
  - Zugriff verweigert (HTTP 403) für Gast, Mitglied und Kapitän auf `/saison/` und Verwaltungsaktionen.
  - ValidationError beim Versuch, ein Spieldatum außerhalb des Saisonfensters zu speichern.
  - Blockade (ProtectedError / ValidationError) beim Löschen einer Saison mit zugewiesenen Teams.
  - PermissionDenied beim Versuch, Spielberichte einer archivierten Saison zu ändern.
- `assertNumQueries`-Prüfungen bestätigen: Keine N+1-Abfragen beim Laden der Saisonübersicht und der gefilterten Mannschaftslisten.

---

## 3. Manuelle End-to-End-Validierung (Vorstandssicht)

### Schritt 1: Saisonverwaltung aufrufen
1. Als Administrator/Vorstand anmelden.
2. Im Menü auf **Saisonverwaltung** (`/saison/`) navigieren.
3. **Prüfung**: Die aktuelle Saison (z. B. `2025/2026`) wird mit grünem Badge `Aktuell` angezeigt. Die Anzahl der Mannschaften und Spiele stimmt.

### Schritt 2: Neue Folgesaison anlegen
1. Auf Schaltfläche **„Neue Saison anlegen“** (`/saison/neu/`) klicken.
2. Das System schlägt vorausgefüllt `2026/2027` mit Start `01.08.2026` und Ende `31.07.2027` vor.
3. Formular speichern.
4. **Prüfung**: Die Saison `2026/2027` erscheint in der Übersicht mit Status `In Vorbereitung`.

### Schritt 3: Geführten Saisonwechsel (Rollover) durchführen
1. Bei der neuen Saison `2026/2027` auf **„Mannschaften übernehmen“** (`/saison/<id>/uebernahme/`) klicken.
2. Die Teams der Vorsaison werden tabellarisch aufgelistet.
3. 1. und 2. Mannschaft auswählen, bei der 1. Mannschaft die Liga auf „Verbandsliga“ ändern.
4. Auf **„Ausgewählte Mannschaften übernehmen“** klicken.
5. **Prüfung**:
   - Die Mannschaften existieren nun in Saison `2026/2027`.
   - Die Teams der alten Saison `2025/2026` bleiben mit ihren historischen Spielen und Bilanzen unverändert erhalten.

### Schritt 4: Aktive Saison umschalten
1. In der Saisonliste bei `2026/2027` auf **„Als aktive Hauptsaison festlegen“** klicken.
2. **Prüfung**:
   - `2026/2027` ist nun als aktive Hauptsaison markiert.
   - Der Bereich „Spielbetrieb“ (`/spielbetrieb/`) zeigt nun standardmäßig die neu angelegten Teams der Saison `2026/2027`.
   - Im `AuditLog` (`/admin/core/auditlog/`) ist die Aktivierung nachweisbar protokolliert.

### Schritt 5: Archivierung & Schreibschutz testen
1. Bei der alten Saison `2025/2026` auf **„Saison abschließen“** klicken.
2. Status wechselt auf `Archiviert`.
3. Zurück im Spielbetrieb den Saisonfilter auf `2025/2026` stellen.
4. Ein altes Spiel aufrufen: Bearbeitungs- und Aufstellungsbuttons sind gesperrt, gelbes Banner „Diese Saison ist archiviert und schreibgeschützt.“ wird angezeigt.

---

## 4. Barrierefreiheits- & Responsivitätsprüfung

- Browser-Fenster auf 360 px (mobiles Smartphone) verkleinern:
  - Formulare, Tabellen und Auswahllisten brechen sauber um; kein horizontaler Overflow (`overflow-x: auto` für Datentabellen).
- Reines Bedienen per Tastatur (Tab, Enter, Pfeiltasten):
  - Jeder interaktive Button und das Saison-Dropdown besitzen sichtbare `:focus-visible`-Ringe.
