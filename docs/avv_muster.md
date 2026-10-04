# Muster: Vereinbarung zur Auftragsverarbeitung (AVV)
**gemäß Art. 28 Datenschutz-Grundverordnung (DSGVO)**

**Zwischen:**

**Verantwortlicher (Kunde / Verein):**  
[Vollständiger Name des Schachvereins e.V.]  
vertreten durch den vertretungsberechtigten Vorstand  
[Anschrift des Vereins]  
– nachfolgend **„Auftraggeber“** genannt –

**und**

**Auftragsverarbeiter (Dienstleister / Anbieter):**  
[Name / Firma des Anbieters / Entwicklers]  
[Anschrift]  
– nachfolgend **„Auftragnehmer“** genannt –

---

## 1. Gegenstand und Dauer des Auftrags
1. Der Auftragnehmer erbringt für den Auftraggeber Hosting, Betrieb, Wartung und Datensicherung der webbasierten Schachvereins-Software.
2. Die Dauer dieser Vereinbarung richtet sich nach der Laufzeit des Hauptvertrages (Pilotvereinbarung bzw. Nutzungsvertrag).

---

## 2. Art und Zweck der Verarbeitung, Art der personenbezogenen Daten und Kategorien betroffener Personen

### 2.1 Art und Zweck der Verarbeitung
Bereitstellung einer geschlossenen Software-Instanz zur Verwaltung der Vereinsmitglieder, Beitragserhebung, Organisation des Mannschafts- und Turnierspielbetriebs, Führung des Kassenbuchs sowie Bereitstellung der öffentlichen Vereinspräsenz.

### 2.2 Kategorien betroffener Personen
* Vereinsmitglieder (aktiv, passiv, Fördermitglieder)
* Ehemalige Vereinsmitglieder
* Gastspieler und Turnierteilnehmer (bei öffentlichen Vereinsturnieren)
* Gesetzliche Vertreter minderjähriger Vereinsmitglieder

### 2.3 Arten der personenbezogenen Daten
* **Stammdaten:** Vor- und Nachname, Geburtsdatum, Anschrift, Telefonnummer, E-Mail-Adresse, Eintritts- und Austrittsdatum, DWZ.
* **Finanz- und Beitragsdaten:** Beitragskategorie, Zahlungsverhalten, Mahnstufen, SEPA-Mandatsreferenz und IBAN (in der Datenbank streng verschlüsselt gespeichert).
* **Spielbetriebs- und Turnierdaten:** Mannschaftszugehörigkeit, Brettaufstellungen, Spielergebnisse, Turnierplatzierungen, DWZ.
* **Kommunikationsdaten:** Opt-in-Status für Rundbriefe, Protokolle des E-Mail-Versands.
* **Nutzungs- und Protokolldaten:** Login-Zeitpunkte, IP-Adressen, Audit-Protokolle von Datenänderungen und Zugriffen auf Mitglieder-Detaildaten.

---

## 3. Pflichten des Auftragnehmers

1. **Weisungsgebundenheit:** Der Auftragnehmer verarbeitet die Daten ausschließlich im Rahmen der Weisungen des Auftraggebers (Art. 28 Abs. 3 lit. a DSGVO).
2. **Vertraulichkeit:** Alle beim Auftragnehmer mit der Datenverarbeitung befassten Personen sind auf das Datengeheimnis verpflichtet worden (Art. 28 Abs. 3 lit. b DSGVO).
3. **Standort der Datenhaltung:** Die Speicherung und Verarbeitung der Daten erfolgt ausschließlich in Rechenzentren innerhalb der Bundesrepublik Deutschland bzw. der Europäischen Union. Eine Übermittlung in Drittstaaten findet nicht statt.
4. **Keine Fremd-Assets & Tracker:** In der Anwendungsarchitektur sind keine Drittanbieter-CDNs, externe Web-Fonts oder Tracking-Dienste eingebunden.
5. **Verschlüsselung:** Sensible Finanzdaten (IBANs) werden auf Datenbankebene verschlüsselt (Fernet-Kryptographie). Passwörter werden mittels robuster Hashes (Argon2 / PBKDF2) gespeichert. Die Datenübertragung im Netz erfolgt ausnahmslos transportverschlüsselt (TLS / HTTPS).
6. **Unterstützung bei Betroffenenrechten:** Der Auftragnehmer stellt Software-Werkzeuge bereit, mit denen der Auftraggeber Auskunftsanfragen (Art. 15 DSGVO) mit einem Klick als PDF- oder JSON-Export erfüllen sowie Austritte und Löschfristen automatisiert verwalten kann.
7. **Löschung nach Vertragsende:** Nach Beendigung des Hauptvertrages werden alle personenbezogenen Daten und Backups innerhalb von 30 Tagen unwiderruflich gelöscht, sofern keine gesetzlichen Aufbewahrungspflichten entgegenstehen.

---

## 4. Technisch-Organisatorische Maßnahmen (TOMs)

Der Auftragnehmer setzt die folgenden technischen und organisatorischen Sicherheitsmaßnahmen gem. Art. 32 DSGVO um:

* **Zutritts- und Zugangskontrolle:**
  * Betrieb in nach ISO/IEC 27001 zertifizierten Hochsicherheitsrechenzentren (Hetzner Online GmbH, Standort Nürnberg/Falkenstein).
  * SSH-Zugang zu Servern ausschließlich über kryptografische Schlüssel (keine Passwort-Authentifizierung).
  * Verpflichtende Zwei-Faktor-Authentifizierung (2FA / TOTP) für Vorstands- und Administrator-Konten der Web-Anwendung.
* **Zugriffskontrolle & Trennung:**
  * Single-Tenant-Architektur: Jeder Verein verfügt über einen isolierten Docker-Container und eine eigene PostgreSQL-Datenbank. Keine Vermischung mit Daten Dritter.
  * Rollenbasierte Zugriffskontrolle (RBAC): Funktionstrennung zwischen Vorstand, Mannschaftskapitän und Mitgliedern.
* **Weitergabekontrolle & Transport:**
  * Erzwungene TLS-Verschlüsselung (HTTPS mit HSTS und modernsten Cipher-Suites via Caddy-Webserver).
  * Nächtliche Datenbank-Backups werden komprimiert und mit AES-256-CBC verschlüsselt abgelegt.
* **Eingabekontrolle & Revisionssicherheit:**
  * Integriertes `AuditLog`: Änderungen an personenbezogenen Daten und Lesezugriffe auf Mitgliederprofile werden mit Zeitstempel und Benutzerkennung protokolliert.
  * Finanzbuchungen sind unveränderlich und können nur per Gegenbuchung (Storno) korrigiert werden.

---

## 5. Unterauftragsverhältnisse (Subunternehmer)

Der Auftraggeber stimmt der Einbindung folgender Unterauftragsverarbeiter für Infrastruktur-Dienstleistungen zu:

| Unternehmen | Anschrift | Zweck | Standort |
|---|---|---|---|
| **Hetzner Online GmbH** | Industriestr. 25, 91710 Gunzenhausen | Bereitstellung Cloud-Server & Rechenzentrum | Deutschland (Nürnberg / Falkenstein) |

Der Auftragnehmer stellt sicher, dass mit dem Unterauftragnehmer Vereinbarungen bestehen, die den Anforderungen von Art. 28 DSGVO entsprechen.

---

[Ort, Datum]

_________________________________________  
**Auftraggeber (Vereinsvorstand)**

_________________________________________  
**Auftragnehmer**
