# Feature Specification: Mannschaftskampf-Autopilot

**Feature Branch**: `001-mannschaftskampf-autopilot`

**Created**: 2026-10-16 (Updated: 2026-10-17)

**Status**: Specified

**Input**: User description: "Modul A: Der Mannschaftskampf-Autopilot (Größter Schmerzpunkt!) Jeden Sonntagmorgen stehen Mannschaftsführer vor dem gleichen Horror: Ein Stammspieler sagt um 22 Uhr am Vorabend krankheitsbedingt ab. Jetzt beginnt das hektische Telefonieren durch die 2., 3. und 4. Mannschaft, unter Beachtung komplizierter Turnierordnungen (Wer darf wie oft hochspielen, ohne sich festzuspielen? Wer fährt mit wem im Auto?). Dein Feature: Du importierst einmalig die gemeldeten Mannschaftslisten des Vereins. 10 Tage vor dem Spieltag verschickt das System automatisch Magic-Links per WhatsApp/E-Mail an die Stammspieler (kein Login nötig! Nur Klick auf: [Bin dabei] / [Kann nicht] / [Brauche Mitfahrgelegenheit]). Sagt Brett 4 ab, schlägt das System dem Mannschaftsführer sofort die regelkonformen Ersatzspieler aus den unteren Mannschaften vor (inkl. Warnung: „Achtung: Wenn Müller heute in der 1. spielt, ist er dort festgespielt!“). Mit einem Klick geht die Anfrage an die Ersatzkandidaten raus. Wer zuerst klickt, bekommt den Platz. /speckit-specify"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatische Verfügbarkeitsabfrage vor dem Spieltag (Priority: P1)

Zehn Tage vor einem angesetzten Mannschaftskampf initiiert das System eine Verfügbarkeitsabfrage an alle gemeldeten Stammspieler der jeweiligen Mannschaft. Die Spieler erhalten eine Nachricht mit einem personalisierten, zugangssicheren Ein-Klick-Link (Magic Link), über den sie ohne Login und ohne Passwort direkt ihre Rückmeldung abgeben können: „Bin dabei“, „Kann nicht“ oder „Brauche Mitfahrgelegenheit“ (optional mit Angabe von Plätzen bei eigener Anreise). Der Mannschaftsführer sieht im Mannschafts-Dashboard in Echtzeit, wer bestätigt hat, wer ausfällt und wer noch nicht geantwortet hat.

**Why this priority**: Das Kernproblem ist fehlende Planungssicherheit. Rechtzeitige und hürdenfreie Rückmeldungen ohne Login-Barrieren verhindern Last-Minute-Krisen und geben Mannschaftsführern Tage vor dem Spieltag Übersicht über den Aufstellungskader.

**Independent Test**: Kann isoliert getestet werden, indem für ein Testspiel die automatische Abfrage ausgelöst wird, Spieler über den Magic Link ihre Zu- oder Absage einreichen und das Dashboard den aktuellen Rückmeldestatus korrekt widerspiegelt.

**Acceptance Scenarios**:

1. **Given** ein aktives Ligaspiel liegt 10 Tage in der Zukunft und 8 Stammspieler sind gemeldet, **When** der Abfragezeitpunkt erreicht ist, **Then** wird für jeden Stammspieler ein eindeutiger Magic Link erzeugt und die Benachrichtigung versendet.
2. **Given** ein Spieler öffnet seinen Magic Link, **When** er auf „Bin dabei“ klickt, **Then** wird seine Zusage sofort erfasst, die Bestätigungsseite zeigt den Status grün an und der Mannschaftsführer sieht den Spieler als bestätigt.
3. **Given** ein Spieler öffnet seinen Magic Link, **When** er auf „Kann nicht“ klickt, **Then** wird der Status auf „abgesagt“ geändert und das System markiert das betreffende Brett als unbesetzt.
4. **Given** ein Spieler klickt erneut auf seinen Link, **When** er seine Antwort vor dem Meldeschluss ändern möchte (z. B. von „Bin dabei“ auf „Kann nicht“), **Then** wird der Status aktualisiert und der Mannschaftsführer benachrichtigt.

---

### User Story 2 - Import der offiziellen Mannschaftsmeldelisten (Priority: P2)

Zu Beginn der Saison importiert der Verein die offizielle Rang- und Meldeliste (Stammspieler und Ersatzreihenfolge je Mannschaft, z. B. 1. bis 4. Mannschaft mit Rangziffern und Brettzuordnung) einmalig in das System. Das System ordnet Vereinsmitglieder anhand ihres Namens oder ihrer Mitgliedsnummer zu und legt die mannschaftsbezogene Rangordnung fest.

**Why this priority**: Bildet das regulatorische Fundament. Ohne die hinterlegte Stamm- und Ersatzreihenfolge können weder automatische Stammspielerabfragen noch regelkonforme Ersatzvorschläge ermittelt werden.

**Independent Test**: Ein Administrator oder Mannschaftsführer lädt eine strukturierte Meldeliste hoch; das System prüft Dubletten, ordnet die Mitglieder den Mannschaften und Stammbrettern zu und zeigt die geprüfte Mannschaftsaufstellung an.

**Acceptance Scenarios**:

1. **Given** eine gültige CSV-/Tabellen-Meldeliste mit Zuordnung von Mannschaft, Rangnummer, Stammbrett und Mitglied, **When** der Import durchgeführt wird, **Then** werden die Stammspieler und die Rangfolge fehlerfrei den Mannschaften zugeordnet.
2. **Given** eine Importdatei enthält nicht zuordenbare Mitgliedsnamen, **When** die Datei validiert wird, **Then** weist das System vor dem Speichern auf Unstimmigkeiten hin und erlaubt die manuelle Korrektur.

---

### User Story 3 - Regelkonforme Ersatzspieler-Ermittlung & Festspiel-Warnung (Priority: P1)

Sobald ein Stammspieler absagt (oder der Mannschaftsführer einen Ausfall manuell einträgt), analysiert das System in Echtzeit die Spielerpools der unteren Mannschaften. Es ermittelt automatisch alle regelkonformen Ersatzspieler unter Berücksichtigung der bisherigen Einsätze in höheren Mannschaften. Steht ein Ersatzkandidat kurz vor dem Festspielen oder würde sich durch den Einsatz festspielen, blendet das System einen unübersehbaren Warnhinweis ein (z. B. „Achtung: Wenn Müller heute in der 1. Mannschaft spielt, ist er dort festgespielt!“).

**Why this priority**: Verhindert fatale Aufstellungsfehler, Punktabzüge am grünen Tisch und den ungewollten Verlust von Spielberechtigungen für untere Mannschaften. Nimmt dem Mannschaftsführer das manuelle Wälzen der Turnierordnung ab.

**Independent Test**: Für einen Spieler mit 2 Einsätzen in einer höheren Mannschaft wird bei einer Absage auf Brett 4 geprüft, ob er im Vorschlag mit der entsprechenden Warnung markiert wird, während unberechtigte oder zeitgleich spielende Spieler ausgeschlossen oder markiert werden.

**Acceptance Scenarios**:

1. **Given** Brett 4 der 1. Mannschaft sagt ab, **When** der Mannschaftsführer die Ersatzkandidaten aufruft, **Then** werden geeignete Spieler aus der 2., 3. und 4. Mannschaft in der durch die Rangordnung vorgegebenen Reihenfolge vorgeschlagen.
2. **Given** Spieler Müller hat bereits die maximale Anzahl an Einsätzen ohne Festspielen erreicht, **When** er als Ersatzkandidat angezeigt wird, **Then** wird eine deutliche Festspiel-Warnung mit Angabe der bisherigen Einsätze angezeigt.
3. **Given** eine untere Mannschaft hat am selben Tag zeitgleich einen eigenen Mannschaftskampf, **When** Ersatzspieler ermittelt werden, **Then** weist das System auf die Terminkollision der Mannschaft hin.

---

### User Story 4 - 1-Klick-Ersatzanfrage (First-Come-First-Serve) (Priority: P2)

Der Mannschaftsführer kann mit einer einzigen Aktion die Ersatzanfrage an die ausgewählten regelkonformen Ersatzkandidaten auslösen. Alle angefragten Ersatzspieler erhalten zeitgleich eine Benachrichtigung mit Magic Link. Wer als Erster auf „Ich springe ein“ klickt, erhält automatisch den Platz in der Aufstellung. Nachfolgende Klicks erhalten die freundliche Meldung, dass der Platz bereits vergeben ist, werden aber auf Wunsch auf eine Nachrückerliste gesetzt.

**Why this priority**: Beseitigt das zeitraubende serielle Nachtelefonieren am Vorabend und besetzt Vakanzen innerhalb von Minuten statt Stunden.

**Independent Test**: An drei Ersatzspieler wird zeitgleich eine Anfrage versendet. Spieler A klickt zuerst und erhält die Platzzusage; Spieler B klickt 5 Sekunden später und erhält die Meldung, dass der Platz bereits besetzt ist.

**Acceptance Scenarios**:

1. **Given** eine offene Vakanz auf Brett 4, **When** der Mannschaftsführer auf „Ersatz anfragen“ klickt, **Then** geht die Anfrage an die berechtigten Ersatzkandidaten heraus.
2. **Given** mehrere Ersatzkandidaten erhalten den Link, **When** der erste Kandidat zusagt, **Then** wird dieser sofort in die Aufstellung eingetragen und der Mannschaftsführer sowie der Spieler erhalten eine Bestätigung.
3. **Given** der Platz wurde vergeben, **When** ein weiterer Kandidat auf den Link klickt, **Then** erscheint die Meldung „Vielen Dank! Der Platz wurde bereits von [Vorname] besetzt.“

---

### User Story 5 - Koordination von Fahrgemeinschaften (Priority: P3)

Bei Auswärtsspielen können Spieler bei der Rückmeldung angeben, ob sie eine Mitfahrgelegenheit benötigen oder selbst mit dem Auto fahren und wie viele freie Plätze sie anbieten. Der Mannschaftsführer sieht eine zusammenfassende Übersicht über Fahrer, freie Plätze und Mitfahrende, um Treffpunkt und Fahrt unkompliziert abzustimmen.

**Why this priority**: Löst das logistische Zusatzproblem bei Auswärtsspielen, vermeidet separate Abstimmungsketten und stellt sicher, dass kein Spieler am Spieltag ohne Anreise dasteht.

**Independent Test**: Drei Spieler geben an, eine Mitfahrgelegenheit zu suchen; zwei Fahrer bieten je 3 Plätze an. Das Dashboard zeigt 6 verfügbare Plätze für 3 Suchende an.

**Acceptance Scenarios**:

1. **Given** ein Auswärtsspiel steht an, **When** ein Spieler zusagt, **Then** kann er wählen: „Fahre selbst (bietet X Plätze)“ oder „Brauche Mitfahrgelegenheit“ oder „Reise eigenständig an“.
2. **Given** mehrere Zusagen liegen vor, **When** der Mannschaftsführer die Fahrgemeinschaftsübersicht öffnet, **Then** sieht er die Abdeckung der benötigten Plätze und die Kontaktdaten der Fahrer.

---

### Edge Cases

- **Letzte-Sekunde-Absage am Spieltagmorgen**: Was passiert, wenn ein Spieler 2 Stunden vor Kampfbeginn absagt? Der Mannschaftsführer kann die Blitz-Ersatzanfrage auch kurzfristig starten und sieht zusätzlich eine Telefonnummernliste für Direktkontakt.
- **Mehrfache Absagen zeitgleich**: Wenn drei Stammspieler absagen, können Ersatzanfragen für mehrere Bretter gleichzeitig bedient werden; das System vergibt die Plätze in der Reihenfolge des Klick-Eingangs.
- **Gleichzeitiger Klick zweier Ersatzkandidaten**: Bei Millisekunden-Konkurrenz entscheidet ein transaktionsgesicherter Erstzugriff; der zweite Spieler wird konfliktfrei informiert.
- **Versehentlicher Klick**: Ein Spieler klickt versehentlich auf „Kann nicht“; über denselben Magic Link kann er seine Rückmeldung innerhalb des Fristfensters revidieren, solange der Platz nicht bereits an einen Ersatzspieler vergeben wurde.
- **Regeländerung / Ausnahmegenehmigung**: Der Mannschaftsführer kann im begründeten Ausnahmefall trotz Festspiel-Warnung einen Spieler aufstellen (wird im Audit-Log dokumentiert).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Das System MUSS den Import von gemeldeten Mannschafts- und Ranglisten (Mannschaftsnummer, Rangziffer, Stammspieler/Ersatzspieler, Vereinsmitgliedszuordnung) über standardisierte Tabellenformate ermöglichen.
- **FR-002**: Das System MUSS 10 Tage vor jedem angesetzten Ligaspieltermin automatisch Verfügbarkeitsabfragen für alle gemeldeten Stammspieler der jeweiligen Mannschaft generieren.
- **FR-003**: Benachrichtigungen MÜSSEN über sichere, zustandstragende Magic Links verfügen, die dem Spieler ohne Login oder Passwortabfrage die direkte Erfassung von Status ([Bin dabei], [Kann nicht], [Fahrbedarf]) ermöglichen.
- **FR-004**: Das System MUSS Benachrichtigungen automatisiert per E-Mail versenden und dem Mannschaftsführer für jeden Spieler und Ersatzkandidaten vorbereitete, DSGVO-konforme Click-to-Chat-Aktionen (`wa.me` bzw. WhatsApp-Web/App-Aufruf mit vorformuliertem Einladungs- und Magic-Link-Text) bereitstellen, ohne Daten an externe Meta-Gateways zu übermitteln.
- **FR-005**: Das System MUSS bei Absage eines Spielers automatisch regelkonforme Ersatzspieler aus nachrangigen Mannschaften anhand der Rangliste und bisheriger Einsätze ermitteln.
- **FR-006**: Das System MUSS die Anzahl der Einsätze je Spieler in höheren Mannschaften fortlaufend nachhalten und eine deutliche Festspiel-Warnung anzeigen, sobald ein Spieler die Schwelle zum Festspielen erreicht oder mit dem nächsten Einsatz überschreiten würde. Als Standardregel gilt die DSB-Turnierordnung (2 Einsätze in höheren Mannschaften frei, ab dem 3. Einsatz festgespielt); dieser Schwellenwert MUSS auf Liga-/Mannschaftsebene in den Einstellungen flexibel konfigurierbar sein.
- **FR-007**: Das System MUSS dem Mannschaftsführer ermöglichen, eine Ersatzanfrage auszulösen. Das System wählt standardmäßig alle berechtigten Kandidaten der unteren Mannschaften per Checkbox vor; der Mannschaftsführer KANN einzelne Kandidaten vor dem Versand gezielt abwählen. Mit einem einzigen Klick wird die Anfrage an alle ausgewählten Kandidaten ausgelöst (First-Come-First-Serve).
- **FR-008**: Geht eine Ersatzanfrage an mehrere Kandidaten, MUSS das First-Come-First-Serve-Prinzip gelten: Die erste eingehende Zusage erhält den Platz automatisch, nachfolgende Zugriffe werden freundlich abgewiesen.
- **FR-009**: Bei Auswärtsspielen MUSS das System Fahrgemeinschafts-Bedarfe (Fahrer mit Anzahl freier Plätze vs. Mitfahrgesuche) erfassen und im Dashboard aggregiert darstellen.
- **FR-010**: Jede Änderung des Aufstellungsstatus, jede Zusage/Absage und jede Vergabe von Ersatzplätzen MUSS für den Mannschaftsführer in Echtzeit nachvollziehbar sein und im Audit-Log protokolliert werden.
- **FR-011**: Magic Links MÜSSEN kryptografisch zufällig erzeugt werden, zeitlich bis zum Spielbeginn befristet sein und dürfen keine sensiblen Profildaten an Dritte exponieren.

### Key Entities *(include if feature involves data)*

- **Mannschaftsmeldung (TeamRoster / RosterEntry)**: Repräsentiert die offizielle Saisonmeldung einer Mannschaft mit Rangziffer, Brettnummer und Zuordnung zum Vereinsmitglied.
- **Spieltagsabfrage (MatchAvailabilityQuery)**: Verwaltet den Lebenszyklus der Verfügbarkeitsabfrage für ein Ligaspiel (Start 10 Tage vor Spieltermin, Status, Rückmeldefrist).
- **Spieler-Rückmeldung (PlayerAvailability)**: Repräsentiert die Rückmeldung eines Spielers zu einem konkreten Spiel (Zusage, Absage, offen, Fahrstatus: Selbstfahrer mit X Plätzen / Mitfahrgesuch / Eigene Anreise, Zeitstempel des Zugriffs).
- **Magic-Token (AvailabilityToken)**: Einmaliges, kryptografisch sicheres Token, das an die Spieler-Rückmeldung gebunden ist und passwortfreien Zugriff ermöglicht.
- **Ersatzanfrage (SubRequest)**: Dokumentiert eine ausgelöste Ersatzsuche für eine vakante Position mit Zielkandidaten, Klick-Historie, Zeitstempeln und dem erfolgreichen Nachrücker.
- **Einsatzhistorie (PlayerAppearance)**: Nachweis aller Einsätze eines Spielers über verschiedene Mannschaften hinweg zur automatischen Berechnung der Festspielgrenzen.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Mannschaftsführer reduzieren den zeitlichen Aufwand für die Aufstellungsorganisation und Ersatzsuche um mindestens 70 % (von durchschnittlich 90 Minuten Telefonaten auf unter 20 Minuten Gesamtaufwand pro Spieltag).
- **SC-002**: Mindestens 80 % der Stammspieler geben ihre Rückmeldung innerhalb von 48 Stunden nach Erhalt des 10-Tage-Magic-Links ohne Erinnerungsaufwand ab.
- **SC-003**: 100 % der vorgeschlagenen Ersatzspieler entsprechen den hinterlegten Ordnungs- und Ranglistenregeln; Aufstellungsfehler durch unbemerktes Festspielen sinken auf 0 Fälle pro Saison.
- **SC-004**: Eine vakante Position kann im Schnitt innerhalb von unter 30 Minuten nach Auslösen der Ersatzanfrage erfolgreich nachbesetzt werden, sofern berechtigte Kandidaten zusagen.
- **SC-005**: Die Rückmeldung über den Magic Link erfordert auf mobilen Endgeräten maximal 2 Klicks und kann in unter 10 Sekunden abgeschlossen werden.

## Assumptions

- **A-001**: Spieler verfügen über ein internetfähiges Smartphone oder einen Computer mit E-Mail-Zugang bzw. Messaging-Client, um den Magic Link aufzurufen.
- **A-002**: Ein Ligaspiel wird im System mit Datum und Uhrzeit mindestens 14 Tage vor dem Spieltag angelegt, damit der 10-Tage-Trigger regulär greifen kann.
- **A-003**: Die Meldelisten der aktuellen Saison liegen in digitaler Form (CSV oder tabellarisch) vor und werden vor dem ersten Spieltag vom Verein eingepflegt.
- **A-004**: Bei kurzfristigen Absagen (unter 3 Stunden vor Spielbeginn) bleibt dem Mannschaftsführer zusätzlich die telefonische Kontaktaufnahme unbenommen; das System unterstützt dies durch Direktwahl-Schaltflächen.
- **A-005**: Das Datenschutzkonzept des Vereins (DSGVO) verbietet die ungeprüfte Weitergabe von Spielerdaten an Drittanbieter; Kommunikationskanäle müssen den Datenschutzvorgaben der Vereinsrichtlinien entsprechen.
