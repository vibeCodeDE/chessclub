# Funktionsübersicht der Schachvereins-Software

Diese Seite bietet eine lückenlose, strukturierte Aufstellung aller funktionalen Module, Workflows und Sicherheitsmechanismen der Schachvereins-Software.

---

## 1. Übersicht & Architektur

Die Anwendung ist eine modulare, servergerenderte Django-5-Webapplikation für Schachvereine. Sie vereint die **öffentliche Vereinspräsenz**, die **interne Mitglieder- und Spielbetriebsverwaltung** sowie die **Vereinsbuchhaltung** unter strenger Einhaltung der DSGVO (keine Drittanbieter-CDNs, keine externen Tracker, verschlüsselte Speicherung sensibler Finanzdaten).

### Rollenkonzept & Berechtigungsmatrix

| Funktion | Vorstand (Admin) | Mannschaftskapitän | Mitglied | Gast / Öffentlichkeit |
|---|:---:|:---:|:---:|:---:|
| **Öffentliche Seiten & News lesen** | Ja | Ja | Ja | Ja |
| **Turnieranmeldung** | Ja | Ja | Ja | Ja (bis Anmeldeschluss) |
| **Eigenes Profil & Beitragsstand einsehen** | Ja | Ja | Ja | Nein |
| **Änderungswunsch für Stammdaten einreichen** | Ja | Ja | Ja | Nein |
| **Persönliche Spieleinsätze einsehen** | Ja | Ja | Ja | Nein |
| **DSGVO-Selbstauskunft (PDF/JSON)** | Alle | Nein | Nur eigene Person | Nein |
| **Aufstellung & Einzelergebnisse erfassen** | Alle Teams | Eigene Mannschaft | Nein | Nein |
| **Mitgliederliste & Volltextsuche** | Ja | Nein | Nein | Nein |
| **Stammdaten & Änderungswünsche freigeben** | Ja | Nein | Nein | Nein |
| **Beitragsläufe, Zahlungen & Mahnwesen** | Ja | Nein | Nein | Nein |
| **Kassenbuch & Jahresabschluss** | Ja | Nein | Nein | Nein |
| **Turniere verwalten & Runden paaren** | Ja | Nein | Nein | Nein |
| **Gruppen-E-Mails & Ankündigungen verwalten**| Ja | Nein | Nein | Nein |
| **Audit-Log & DSGVO-Verzeichnis (VVT)** | Ja | Nein | Nein | Nein |

---

## 2. Öffentliche Vereinspräsenz (Website)

Die öffentliche Seite repräsentiert den Verein nach außen, funktioniert ohne Login und ist responsiv für alle Geräteklassen (ab 360 px Breite) optimiert.

* **Startseite (`/`)**:
  * Hero-Bereich mit dynamischen Vereinsdaten (Gründungsjahr, Treffpunkt, Trainingszeiten).
  * Schnellstatistiken (Mitglieder, Mannschaften, nächste Events).
  * Die neuesten Ankündigungen und anstehende Termine.
* **Vereinsseite (`/verein/`)**:
  * Vereinsphilosophie & Selbstverständnis.
  * Spielabend- und Jugendtrainingszeiten.
  * Spielstätte & Anfahrtsinformationen.
  * Kommender Ligaspielplan aller Mannschaften.
* **Mitglied werden (`/mitglied-werden/`)**:
  * Übersicht aller Beitragskategorien und Jahresbeiträge.
  * Informationen zum Schnuppertraining und Aufnahmeantrag.
* **Öffentlicher Turnierkalender (`/turniere/` & `/turniere/<id>/`)**:
  * Übersicht aller offenen und vergangenen Vereinsturniere.
  * Detailansicht mit Turniermodus, Bedenkzeit, Zeitplan und Teilnehmerliste.
  * Online-Anmeldung für Vereinsmitglieder und externe Gäste bis zum Anmeldeschluss.
* **Nachrichtenarchiv (`/aktuelles/` & `/aktuelles/<id>/`)**:
  * Vollständiges Archiv aller freigegebenen Vereinsnachrichten mit Kategoriefilter.
* **Produkt-Landingpage (`/produkt/`)**:
  * Präsentationsseite für andere Schachvereine mit Tarifübersicht und Kontaktfunktion.
* **Rechtliches (`/impressum/`, `/datenschutz/`)**:
  * DSGVO-konforme Datenschutzerklärung und Impressumsangaben.

---

## 3. Authentifizierung & Sicherheit (`core`)

* **Authentifizierung & Sitzungsverwaltung**:
  * Benutzeranmeldung (`/anmelden/`) und sichere Abmeldung (`/abmelden/`).
  * Passwort-Reset per Token-Mail (`/passwort/aendern/`).
* **Zwei-Faktor-Authentifizierung (2FA / TOTP)**:
  * Obligatorisch für die Vorstandsgruppe im Produktivbetrieb (`/anmelden/zwei-faktor/neu/`).
  * Kompatibel mit gängigen Authenticator-Apps (z. B. Aegis, 2FAS, Google Authenticator).
* **Progressive Web App (PWA)**:
  * Service Worker (`/sw.js`) und Web-App-Manifest für Homescreen-Installation auf iOS & Android.
  * Offline-Fallback (`/offline/`) bei Verbindungsverlust.
* **Zentrales Dashboard (`/dashboard/`)**:
  * Rollenindividuelle Startseite nach dem Login.
  * Warnanzeigen bei offenen Beiträgen, anstehenden Spielen und Genehmigungsanträgen.
* **Globale Suche (`/suche/`)**:
  * Übergreifende Suchfunktion über Mitglieder, Turniere, Mannschaften und Ankündigungen.

---

## 4. Mitgliederverwaltung (`members`)

* **Mitglieder-Stammdaten**:
  * Vollständige Profilverwaltung: Vor- und Nachname, Geburtsdatum, Anschrift, E-Mail, Telefon, Eintritts-/Austrittsdatum, DWZ.
  * Statusverwaltung: *Aktiv*, *Passiv*, *Ausgetreten* (historisiert ohne physisches Löschen).
* **Mitgliederlisten & Export (`/mitglieder/`)**:
  * Listenansicht mit Filterung nach Status und Gruppen.
  * CSV-Export der Mitgliederdaten für administrative Zwecke.
* **Mitglieder-Selbstbedienung (`/profil/`)**:
  * Einsicht der eigenen Stammdaten, Mannschaftszugehörigkeiten und des Beitragsstatus.
* **Änderungswunsch-Workflow (`/mitglieder/wuensche/`)**:
  * Mitglieder können Adress- oder Kontaktdatenänderungen einreichen.
  * Vorstand prüft, genehmigt oder lehnt die Änderung mit einem Klick ab (Vier-Augen-Prinzip).
* **Austritts-Workflow**:
  * Erfassung des Austrittsdatums mit Statuswechsel auf *Ausgetreten*.

---

## 5. Beitragsverwaltung & Finanzen (`dues`)

* **Beitragskategorien (`/beitraege/kategorien/`)**:
  * Konfigurierbare Beitragssätze (z. B. Vollzahler, Jugendliche, Familien, Passive, Ermäßigte).
* **Automatisierter Beitragslauf (`/beitraege/lauf/`)**:
  * Erzeugung aller Beitragsforderungen für das Geschäftsjahr für alle aktiven Mitglieder mit einem Klick.
* **SEPA-Mandatsverwaltung (`/beitraege/mandate/`)**:
  * Verwaltung von Mandatsreferenz, Ausstellungsdatum und Gültigkeitsstatus.
  * AES-verschlüsselte IBAN-Speicherung in der Datenbank (Schlüsselhaltung über Umgebungsvariablen).
  * Manuelle bankseitige Abwicklung (keine unsichere direkte Bank-API-Verbindung).
* **Zahlungserfassung (`/beitraege/posten/<id>/zahlung/`)**:
  * Buchung von Zahlungseingängen (Überweisung, SEPA-Lastschrift, Barzahlung).
  * Unterstützung von Teilzahlungen und Überzahlungen.
* **Revisionssichere Stornierung**:
  * Kein Löschen von Zahlungsdaten – Korrekturen erfolgen per Gegenbuchung mit Audit-Spur.
* **Mahnwesen (`/beitraege/mahnwesen/`)**:
  * Automatische Liste aller säumigen Mitglieder mit offenen Beträgen.
  * Generierung druckfertiger PDF-Mahnbriefe inklusive Verzugsinformationen.
* **Kassenbericht (`/beitraege/kassenbericht/`)**:
  * Aggregierte Jahresübersicht der Soll- und Ist-Beiträge mit CSV-Export.
* **Mitglieder-Einsicht (`/mein-beitragskonto/`)**:
  * Mitglieder sehen jederzeit ihre eigenen Buchungen, Zahlungen und offenen Beträge.

---

## 6. Spielbetrieb & Mannschaften (`teams`)

* **Mannschaftsverwaltung (`/mannschaften/`)**:
  * Anlegen und Verwalten von Mannschaften (1. Mannschaft, 2. Mannschaft, Jugend etc.) mit Liga und Spielklasse.
* **Spieltage & Spielplan (`/spiele/`)**:
  * Verwaltung von Spielterminen, Heim-/Auswärtsspielen, gegnerischen Vereinen und Spiellokalen.
* **Aufstellungs-Management (`/spiele/<id>/aufstellung/`)**:
  * Mannschaftsführer stellen ihre Bretter auf (inkl. Fristenüberwachung und Ersatzspieler-Kennzeichnung).
* **Ergebniserfassung**:
  * Brettweise Erfassung der Partieresultate (1:0, 0,5:0,5, 0:1, kampflos) mit automatischer Berechnung des Mannschaftsendstands (Brettpunkte und Mannschaftspunkte).
* **Ligatabellen (`/ligen/`)**:
  * Automatische Berechnung und Anzeige von Mannschaftstabellen.
* **Kalender-Integration (iCal)**:
  * Abonnierbarer iCal-Feed für Mannschaftsspielpläne mit privatem Token (DSGVO-konform ohne Personendaten).
* **Spieler-Übersicht (`/meine-einsaetze/`)**:
  * Mitglieder sehen alle eigenen Spielansetzungen und Aufstellungen auf einen Blick.

---

## 7. Turniere & Meisterschaften (`tournaments`)

* **Turniererstellung & Formate (`/turniere/verwalten/`)**:
  * Unterstützung von Schweizer System, Rundenturnieren (Jeder-gegen-Jeden) sowie Schnell- und Blitzturnieren.
  * Konfiguration von Rundenanzahl, Bedenkzeit, Startgeld und Anmeldefristen.
* **Teilnehmerverwaltung & Startgelder**:
  * Verwaltung von Vereinsmitgliedern und externen Gastspielern.
  * Buchungsstatus des Startgelds (bezahlt / offen).
* **Paarungssystem**:
  * Automatische Paarung nach Schweizer System (Farbausgleich, Vermeidung von Wiederholungspaarungen).
  * Möglichkeit manueller Paarungen und Freilose.
* **Ergebniserfassung & Feinwertungen**:
  * Erfassung der Rundenresultate mit automatischer Ranglistenaktualisierung.
  * Berechnung von Punkten, Buchholz-Wertung, Buchholz-Summe und Sonneborn-Berger-Wertung.
* **Turnierabschluss & Exporte**:
  * Druckoptimierte Ranglistenansicht.
  * ChessResults-kompatibler CSV-Export zur Weitergabe an Verbände oder Turnierplattformen.

---

## 8. Kommunikation & Öffentlichkeitsarbeit (`comms`)

* **Ankündigungen & News-Workflow (`/ankuendigungen/`)**:
  * Erstellung redaktioneller Beiträge mit Kategorien und Teaser-Bildern.
  * Entwurfsmodus mit expliziter Freigabe und Veröffentlichung für die Startseite.
* **Gruppen-E-Mail-Verteiler (`/ankuendigungen/mail/`)**:
  * Zielgerichteter Mailversand an vordefinierte Gruppen (z. B. Gesamter Verein, Vorstand, Mannschaftsführer, Aktive).
  * Strikte Beachtung des E-Mail-Opt-In-Status jedes Mitglieds.
  * Archivierung der Versandprotokolle.

---

## 9. Vereins-Kassenbuch (`cashbook`)

* **Einnahmen- & Ausgabenbuchung (`/kasse/`)**:
  * Erfassung von Bar- und Bankbewegungen außerhalb der Mitgliedsbeiträge (z. B. Spielmaterial, Fahrtkosten, Startgelder, Raummiete).
  * Belegnummern, Buchungsdatum und Kategorisierung.
* **Laufender Saldo**:
  * Echtzeit-Berechnung des aktuellen Bar- und Gesamtkassenbestands.
* **Jahresabschluss (`/kasse/jahresabschluss/`)**:
  * Strukturierte Jahressalden nach Einnahmen- und Ausgabenkategorien.
  * CSV-Export für den Steuerberater oder die Jahreshauptversammlung / Kassenprüfung.
* **Revisionssicherheit**:
  * Fehlbuchungen werden nach GoBD-Grundsätzen durch Gegenbuchungen / Storno korrigiert.

---

## 10. DSGVO, Compliance & Datensicherheit (`core`)

* **Datenauskunft nach Art. 15 DSGVO (`/mitglieder/<id>/auskunft/`)**:
  * 1-Klick-Generierung einer lückenlosen Selbstauskunft als PDF und maschinenlesbares JSON.
* **Verzeichnis von Verarbeitungstätigkeiten nach Art. 30 DSGVO (`/datenschutz/verzeichnis.csv`)**:
  * Exportierbares Verzeichnis aller im Verein verarbeiteten Datenkategorien und Rechtsgrundlagen.
* **Recht auf Vergessenwerden & Aufbewahrungsfristen**:
  * Automatisierte Anonymisierung von Stammdaten ausgetretener Mitglieder nach Ablauf der Frist.
  * Revisionssichere Beibehaltung anonymisierter Finanzdaten gemäß § 147 AO (8 Jahre Aufbewahrungspflicht).
* **Lückenloses Audit- und Zugriffsprotokoll (`/audit/`)**:
  * Protokollierung aller sicherheitsrelevanten Aktionen: Logins, Stammdatenänderungen und Zugriffe auf personenbezogene Detaildaten.
* **Datensparsamkeit bei Gastdaten**:
  * Daten externer Turnierteilnehmer sind zweckgebunden und werden nicht in Mitgliederlisten geführt.
