# PRD: Schachvereins-Software

**Status:** Freigegeben v1.6 (Universelle Zugänglichkeit, Barrierefreiheit WCAG 2.1 AA/AAA, Design-Exzellenz) — Änderungen siehe §9
**Datum:** 2026-10-04

---

## 1. Ziel & Zielgruppe

**Was bauen wir?** Eine selbst gehostete Web-Software für einen Schachverein (< 200 Mitglieder), die die Vereinsverwaltung zentral abbildet: Mitglieder, Beiträge, Turniere, Spielbetrieb, Kommunikation und Buchhaltung — mit überragendem, zeitlosem Design und universeller Zugänglichkeit für alle Generationen.

**Für wen?** Schachvereine zeichnen sich durch eine besonders heterogene Mitgliedschaft aus (Schüler/Jugendliche ab 6 Jahren, aktive Turnierspieler, ehrenamtliche Funktionäre und Seniorinnen/Senioren bis 80+ Jahre). Die Software ist so gestaltet, dass sie für alle Nutzergruppen ohne technische Hürden intuitiv und barrierefrei bedienbar ist.

| Persona | Rolle | Hauptbedürfnis |
|---|---|---|
| Vorstand (Kassenwart, Schriftführer, 1. Vorsitzender) | Admin | Volle Übersicht, DSGVO-konforme Verwaltung, minimaler manueller Aufwand |
| Mannschaftskapitän | Mitarbeiter | Schnelle Aufstellung am Spieltag, unkomplizierte Ergebniserfassung (auch mobil am Brett) |
| Mitglied (Jugendliche bis Senioren) | Leser/Bearbeiter eigener Daten | Glasklarer Beitragsstand, einfache 1-Klick-Turnieranmeldung, eigene Daten barrierefrei einsehen |
| Öffentlichkeit & Gastspieler | Gast | Öffentliche Termine, Turniere, Ergebnisse und Beitrittsinformationen barrierearm zugänglich |

**Erfolg bedeutet:** Der Vorstand kann Mitglieder, Beiträge und Turniere ohne Excel-Dateien und ohne Zusatztools pflegen; alle Daten liegen DSGVO-konform auf eigener Infrastruktur; alle Generationen des Vereins nutzen das System gerne und ohne Barrieren.

---

## 2. Plattform & Rahmenbedingungen

- **Typ:** Web-App, selbst gehostet (Vereinsserver oder kleiner Host beim deutschen Anbieter)
- **Sprache:** Deutsch (UI und Daten)
- **Skalierung:** Single-Tenant, eine Vereinsdatenbank, ≤ 200 Mitglieder, ≤ 20 gleichzeitige Nutzer
- **Harte Anforderung:** DSGVO — Datenhaltung ausschließlich in der EU/DE, Lösch- und Auskunftspflichten abbildbar, Protokollierung von Zugriffen auf Personendaten
- **Interop:** Ergebnisexport/-import in gängigen Formaten (z. B. ChessResults-tauglicher CSV-/Textexport) — kein Zwang zu einem Fremdsystem

### Tech-Stack (bestätigt)

- **Backend:** Django (Python) — Admin-Oberfläche, Auth, CSRF, ORM; der Vorstand braucht kein Framework-Wissen, die meiste Pflege läuft über Djangos fertige Admin-Oberfläche
- **Datenbank:** PostgreSQL
- **Frontend:** Server-seitig gerendert (Django Templates + Tailwind) — keine getrennte SPA nötig
- **Deployment:** Docker Compose (App + DB + Backups) auf vereinseigenem Server, TLS via Reverse Proxy
- **Website:** keine vorhandene — die App ist die öffentliche Präsenz (Startseite mit News/Terminen)

---

## 3. Funktionale Anforderungen

Priorisierung: **M** = Muss (v1), **S** = Sollte (v1.1), **K** = Kann (später)

### 3.1 Mitgliederverwaltung (M)

- M1.1 Stammprofil: Name, Geburtsdatum, Anschrift, E-Mail, Telefon, Eintritts-/Austrittsdatum
- M1.2 Rollen & Berechtigungen: Admin (Vorstand), Kapitän, Mitglied, Gast
- M1.3 Mitgliederstatus: aktiv, passiv, ausgetreten (historisiert — kein Löschen, sondern Deaktivieren)
- M1.4 Selbstbedienung: Mitglied sieht eigene Daten und reicht **Änderungswünsche** ein; Admin prüft und gibt frei (kein direktes Editieren)
- M1.5 Listen: Filter/Suche, CSV-Export (kein Altbestand vorhanden → kein Import nötig)
- M1.6 Sonstige Personen: Förderer/ehemalige Mitglieder als passive Einträge

### 3.2 Beitragsverwaltung (M/S)

- M2.1 Beitragssätze konfigurierbar (z. B. Erwachsene, Jugendliche, Familien, ermäßigt)
- M2.2 Jährliche Beitragsläufe: automatische Rechnungsstellung für alle aktiven Mitglieder
- M2.3 SEPA-Mandate: Mandat je Mitglied verwalten (Referenz, Datum, Status); Einzug erfolgt **bankseitig manuell** durch den Verein — die Software erfasst nur Mandat + Zahlungsstatus, **kein** automatisierter Einzug über Banking-API
- M2.4 Zahlungserfassung: Überweisung, SEPA-Einzug und Barzahlung manuell buchen (Zahlungsart je Buchung)
- M2.5 Mahnwesen: automatische offene-Beitrags-Übersicht, Mahnbrief als PDF
- M2.6 Kassenbuch-Sicht (Beiträge): Zahlungen je Mitglied, Jahresübersicht für den Kassenbericht — reine Lese-Sicht auf die Beitragsdaten, siehe Abgrenzung in §3.6
- S2.7 SEPA-XML-Export: Erzeugung und Download einer standardisierten SEPA-Lastschriftdatei (pain.008.001.02) für offene Beitragsposten mit aktivem SEPA-Mandat zur manuellen Abgabe im Online-Banking (keine Bank-API, siehe [ADR-017](decisions/ADR-017-sepa-xml-export-pain-008.md))

### 3.3 Turniere & Ergebnisse (M/S)

- M3.1 Turnier anlegen: Datum, Ort, Format (Schweizer/Reihenfolge/Rapid/Blitz), Anmeldeschluss
- M3.2 Anmeldung: öffentlich oder für Mitglieder, Startgeld-Status
- M3.3 Ergebniserfassung: Rundeneingabe, automatische Zwischenwertung (Schweizer System)
- S3.4 Paarungen: automatische Paarung nach Schweizer System (z. B. Bibliothek/Matcher)
- S3.5 Export: Ergebnisliste drucken + Export für ChessResults-Import
- K3.6 DSB-Schnittstelle & Meldeformate (DWZ-Sync, nuLiga-Export, TRF16, siehe [ADR-016](decisions/ADR-016-dsb-schnittstellen-architektur.md))

### 3.4 Spielbetrieb / Mannschaften (M/S)

- M4.1 Mannschaften anlegen (1. Mannschaft, 2. Mannschaft, Jugend)
- M4.2 Ligaspiele: Termine, Gegner, Heim/Auswärts
- M4.3 Aufstellung: Kapitän trägt Aufstellung ein, Fristenverwaltung
- M4.4 Ergebnisse je Liga-Match (Einzelbretter → Mannschaftsergebnis)
- S4.5 automatische Tabellenberechnung je Liga
- S4.6 iCal-Feed der Ligaspiele (abonnierbar im Handykalender, ohne Login nur mit geheimem Token-Link; keine Aufstellungs- oder Personendaten)

### 3.5 Kommunikation (M/S)

- M5.1 Ankündigungen/News im Portal (mit Archiv)
- M5.2 E-Mail-Versand an Mitglieder-/Gruppenverteilung (opt-in-Status je Person)
- S5.3 Newsletter-Routine (quartalsweise), Versandprotokoll
- K5.4 SMS/E-Mail-Erinnerungen an Turniertermine

### 3.6 Buchhaltung (S)

- S6.1 Einnahmen/Ausgaben-Kassenbuch mit Kategorien
- S6.2 Beleg-/Bezeichnungsfelder pro Buchung, Jahresabschlussansicht (CSV-Export für Steuerberater)
- K6.3 Anbindung an DATEV-Export
- **Abgrenzung:** keine vollständige Buchhaltungssoftware — Finanzamt-Export reicht als Schnittstelle
- **Abgrenzung zu M2.6:** M2.6 ist eine reine Lese-Sicht auf **Beitragszahlungen** (v1). S6.1/S6.2 ist das eigenständige **Kassenbuch für alle Einnahmen/Ausgaben** des Vereins (v1.1). Die beiden Bücher werden nicht zusammengeführt; S6.1/S6.2 referenziert M2.6-Zahlungen höchstens als Lese-Quelle.

### 3.7 Gemeinsame Anforderungen

- M7.1 Dashboard: offene Beiträge, anstehende Termine, letzte Anmeldungen
- M7.2 Rollenbasierte Navigation (Menüs je Rolle)
- M7.3 Audit-Log: wer hat Personendaten wann geändert (DSGVO-Nachweis)
- S7.4 Modul-Toggles im Admin-Panel: Superadmin / Vorstand kann optionale Satellitenmodule (Spielbetrieb, Turniere, Kassenbuch, Kommunikation) im Django Admin an- und ausschalten (ADR-019)

### 3.8 Berechtigungsmatrix (M)

Verbindliche Zuordnung für T2 (Navigation), T3/T12 (Mitgliederdetail), T17 (Aufstellung), T19 (Turnieranmeldung/Gastdaten) und **alle** Export-/Übersichtstasks (T9c, T10, T11b, T15, T22, T23, T30); jede Zeile erhält einen Negativtest.

| Funktion | Admin (Vorstand) | Kapitän | Mitglied | Gast |
|---|---|---|---|---|
| Mitgliederliste (alle) | ja | nein | nein | nein |
| Mitgliederdetail (alle) | ja | eigene Mannschaft (ab T17) | nur eigene Person (via `/profil/`, M1.4 — **kein** Zugriff auf die Admin-Detailseite) | nein |
| Stammdaten bearbeiten | ja | nein | nur via Änderungswunsch | nein |
| Änderungswunsch freigeben | ja | nein | nein | nein |
| Mannschaften/Ligaspiele verwalten | ja | nein | nein | nein |
| Aufstellung + Einzelergebnisse | ja | eigene Mannschaft | nein | nein |
| Turnier verwalten | ja | nein | nein | nein |
| Turnieranmeldung | ja | ja | ja | ja (bis Anmeldeschluss, mit Name + E-Mail) |
| Gastdaten aus Turnieranmeldung einsehen / löschen | ja | nein | nein | nein (Gast hat keinen Login; Korrektur/Löschung über die Turnierverwaltung) |
| Beiträge / Zahlungen / Mahnungen / SEPA-Export | ja | nein | nur eigener Beitragsstand | nein |
| Kassenbuch | ja | nein | nein | nein |
| News verwalten | ja | nein | nein | nein |
| News lesen (Startseite + Archiv) | ja | ja | ja | ja |
| E-Mail an Gruppe | ja | nein | nein | nein |
| Auskunfts-Export (DSGVO) | ja | nein | nur eigene Person | nein |
| Audit-/Zugriffslog einsehen | ja | nein | nein | nein |
| Modul-Toggles verwalten (ADR-019) | ja | nein | nein | nein |

---

### 3.9 Öffentliche Vereinsseite (S)

- S9.1 Öffentliche Startseite mit Vereinszahlen, den nächsten Terminen und aktuellen Ankündigungen (nur Veröffentlichtes, M5.1)
- S9.2 Vereinsseite mit Selbstverständnis, Trainings-/Klubzeiten, Treffpunkt und dem kommenden Ligaspielplan
- S9.3 Einheitliche Designsprache für alle öffentlichen Seiten einschließlich Fehlerseite und Anmeldeeinstieg; eigenes Stylesheet, das den internen Bereich (Dashboard/Verwaltung) nicht berührt
- S9.4 Archiv der Ankündigungen mit Kategoriefilter sowie Turnierkalender mit Anmeldestatus und vergangenen Turnieren

---

## 4. Nicht-funktionale Anforderungen

### 4.1 DSGVO (harte Anforderung)

- N1.1 Datenhaltung nur in EU/DE; keine Drittanbieter-Tracker, kein externes CDN
- N1.2 Auskunftsanfragen: personenbezogene Daten eines Mitglieds als PDF exportierbar
- N1.3 Löschpflicht: nach Austritt automatische Anonymisierung nach konfigurierbarer Frist (Default 36 Monate); dabei Kontaktdaten + Stammdaten löschen/anonymisieren, Finanzhistorie (Beiträge, Zahlungen) anonymisiert erhalten (nur noch Mitglied-ID). Aufbewahrung der anonymisierten Finanzhistorie: **8 Jahre** nach § 147 AO; die GoBD verweist für die ordnungsgemäße Aufbewahrung darauf, ist aber nicht selbst die Fristquelle. Fristen vor Go-Live mit Steuerberater bestätigen
- N1.4 Verzeichnis von Verarbeitungstätigkeiten: Maschinenlesbare Exportfunktion der Datenkategorien
- N1.5 Protokollierung von Logins, Änderungen **und** Zugriffen auf Personendaten (mindestens 12 Monate). „Zugriff" = Aufruf einer Mitglieder-Detailansicht und Ausführung des Auskunfts-Exports; Listenansichten werden nicht einzeln protokolliert
- N1.6 Verschlüsselte Übertragung (TLS), verschlüsselte Passwörter (bcrypt/argon2), 2FA für Admins (S), Brute-Force-Schutz für Logins (django-axes, ADR-015)
- N1.7 Gastdaten aus öffentlichen Turnieranmeldungen (Name + E-Mail) gelten als Personendaten Dritter: sichtbar nur in der Turnierverwaltung, **nicht** in Mitgliederlisten/-suchen, mit Zweckbindung (nur Teilnehmerliste dieses Turniers) und dokumentierter Löschfrist nach Turnierende. Einwilligung: Hinweis auf der Anmeldeseite (Art. 6 Abs. 1 lit. b DSGVO — Durchführung des Turniers)

### 4.2 Sonstige NFR

- N2.1 **Verfügbarkeit:** 99 % im Vereinsalltag; nächtliches automatisches Backup (pg_dump, komprimiert + **verschlüsselt** z. B. GPG/age — Schlüssel getrennt vom DB-Host gelagert, nicht im Repo), Wiederherstellungstest inkl. Entschlüsselung dokumentiert
- N2.2 **Performance:** Seitenladen < 1 s im LAN/DSL; Suchergebnisse < 500 ms; N+1-Query-Prüfung in der Entwicklung via django-debug-toolbar (ADR-015)
- N2.3 **Bedienbarkeit & Barrierefreiheit (Universal Access):** Tablet-tauglich (Aufstellung am Spieltag); volle Barrierefreiheit nach **WCAG 2.1 Stufe AA** (Ziel AAA bei Textkontrasten ≥ 7:1); vollständige Tastaturbedienbarkeit mit sichtbaren Focus-Ringen (`:focus-visible`); semantische HTML5-Struktur mit ARIA-Landmarks; Screenreader-freundliche Formular-Labels und Fehlermeldungen; altersgerechte Typografie (Schriftgröße ≥ 16 px, Zeilenabstand 1.5, Zoom bis 200 % ohne Überlappung); Touch-Ziele ≥ 44 × 44 px (WCAG 2.5.5) für fehlerfreie Bedienung am Smartphone und durch ältere Mitglieder
- N2.4 **Wartbarkeit:** Updatepfad per `docker compose pull`; Datenmigrationen versioniert
- N2.5 **Beobachtbarkeit:** strukturierte Logs, Fehlerbenachrichtigung an Admin-E-Mail
- N2.6 **Mobil & Responsiv:** Alle Kernflächen funktionieren nahtlos ab 360 px bis 4K (Responsive, Mobile-First-Layout); Navigation als leicht bedienbares Burger-Menü; Tabellen horizontal scrollbar statt zerbrochen
- N2.7 **Installierbarkeit (PWA):** App lässt sich auf Homescreen/Startmenü installieren (Web-App-Manifest + Service Worker), öffnet sich in eigenem Fenster ohne Browser-Chrome, Icons für iOS/Android; Basis-Offline-Anzeige der Startseite/letzten News
- N2.8 **Monitoring (S):** Erreichbarkeit der App und ausbleibendes Backup werden überwacht und per E-Mail gemeldet (z. B. Uptime Kuma, ADR-009); keine Personendaten in den Meldungen

**Nachweis-NFRs:** N2.2–N2.5 sind erst mit v1 erfüllt, wenn sie gemessen bzw. geprüft sind — siehe Plan-Task T25b (Messung + WCAG-Audit) und T24 (Updatepfad, EU-Hoststandort).

---

## 5. Nicht im Scope (v1)

- Multi-Tenant / mehrere Vereine in einer Instanz
- Native Mobile-Apps im App Store (PWA-Installation genügt — kein Store-Review, kein zweiter Codestand)
- Vollständige Finanzbuchhaltung / DATEV-Buchführung
- Livestream/Streaming, Spielpaarungs-Server für Online-Schach
- Direkte Schreib-Integration in DSB-Mitgliedschaftsportale mangels offener Verbands-API (stattdessen Export & DWZ-Read-Sync, siehe [ADR-016](decisions/ADR-016-dsb-schnittstellen-architektur.md))

---

## 6. Meilensteine

Meilensteine heißen **MS1–MS7**, damit sie nicht mit den Anforderungs-IDs (M1.1 = Muss) und den Größenangaben im Plan verwechselt werden. Was zu v1.1 gehört, ist unten ausdrücklich markiert.

| MS | Inhalt | Abnahme |
|---|---|---|
| MS1 | Auth, Rollen, Mitgliederstammdaten, Änderungswunsch-Workflow | Vorstand legt Mitglieder an, Änderungswunsch-Testlauf |
| MS2 | Beitragsläufe, Zahlungserfassung, Mahnung, Dashboard | Jahresbeitragslauf als Testlauf komplett |
| MS3 | Mannschaften, Aufstellung, Ligaspiele *(Tabelle S4.5: v1.1)* | Beispielspiel erfassen (Aufstellung → Ergebnis); Tabelle erst in v1.1 |
| MS4 | Turniere inkl. Anmeldung, Runden, Handpaarung *(automatische Schweizer Paarung S3.4 und Export S3.5: v1.1)* | Testturnier über 3 Runden handgepaart gespielt |
| MS5 | Kommunikation (News + E-Mail) *(Kassenbuch §3.6: v1.1)* | Testversand an Gruppe; Kassenexport erst in v1.1 |
| MS6 | DSGVO-Härte: Export/Löschfristen/Audit, NFR-Nachweis (Performance/WCAG/Updatepfad), Backups | DSGVO-Checkliste abgehakt, N2.2–N2.4 gemessen |
| MS7 | Mobil: Responsive-Feinschliff + PWA-Installation (iOS/Android) | App auf Homescreen installiert, 360-px-Check bestanden |

**Release-Schnitt (v1 vs. v1.1):** **v1** umfasst alle M-Anforderungen (§3.1–§3.5 ohne S-Teile, §3.7), die gesamte DSGVO §4.1 (N1.1–N1.5, N1.7) und alle NFR §4.2 (N2.1–N2.7). N1.6 (2FA) und N2.8 (Monitoring) sind im PRD als S geführt und gehören zu v1.1. **v1.1** ergänzt alle S-Anforderungen und wird erst nach v1-Abnahme gebaut: S3.4 Paarung, S3.5 Turnierexport, S4.5 Tabellen, S4.6 iCal-Feed, S5.3 Newsletter, §3.6 Kassenbuch, N1.6 2FA, N2.8 Monitoring. K-Anforderungen (K3.6, K5.4, K6.3) sind out of scope.

---

## 7. Erfolgskriterien

- Beitragslauf für 150 Mitglieder in < 10 Minuten erstellt und exportiert
- Keine Excel-Dateien mehr für Mitglieder oder Beiträge als primäre Quelle
- Turnierergebnisse nach letzten Runden in < 2 Minuten erfasst und veröffentlicht
- Startseite und Turnieranmeldung funktionieren reibungslos auf dem Smartphone (getestet ab 360 px) und lassen sich als PWA auf dem Homescreen installieren
- Universelle Zugänglichkeit: Kernflächen (Login, Dashboard, Mitgliederliste, Aufstellung, Turnieranmeldung) erfüllen WCAG 2.1 Stufe AA ohne schwerwiegende Verstöße; alle interaktiven Elemente mit Tastatur erreichbar und visuell fokussiert
- Auskunftsanfrage eines Mitglieds: ein Klick → vollständiges PDF
- Wiederherstellung aus Backup erfolgreich getestet innerhalb von 4 h
- Kassenbericht für den Vorstand ohne Nachbearbeitung erstellbar
- Performance: Kernseiten laden im Vereinsserver-Test in < 1 s
- Update auf eine neue Version per dokumentiertem `docker compose pull`-Ablauf möglich, ohne Datenverlust

---

## 8. Getroffene Entscheidungen (frühere offene Fragen)

Architektur-Entscheidungen sind damit abgeschlossen. **Operativ offene Punkte** (Zugangsdaten, Vereinswerte, Fristen) stehen weiterhin in `tasks/plan.md` → *Open Questions* — das sind keine offenen Designfragen, sondern Eingaben, die vor bestimmten Tasks fehlen.

| # | Frage | Entscheidung |
|---|---|---|
| 1 | Tech-Stack | **Django** bestätigt; Nutzer ist neu mit Django → App soll möglichst über Djangos Admin + einfache Views abgebildet werden, Wartungsdoku im Repo |
| 2 | SEPA-Einzug | **Kein echter automatisierter Einzug** — Software verwaltet Mandate (M2.3) und Zahlungsstatus; der Einzug erfolgt **bankseitig manuell per SEPA-Lastschrift** durch den Verein. Gebucht wird je Zahlung die Zahlungsart (M2.4) |
| 3 | Selbstbedienung | **Änderungswunsch-Workflow**, kein direktes Editieren |
| 4 | Bestehende Website | **Keine** — App liefert auch die öffentliche Startseite |
| 5 | Hosting | **Selbst gehostet** durch den Verein (Docker Compose), Standort EU/DE (N1.1) |
| 6 | Altbestand | **Keiner** — keine CSV-Importfunktion nötig |
| 7 | Turnieranmeldung durch Gäste | **Zulässig** bis Anmeldeschluss; Gastdaten sind Personendaten Dritter und folgen N1.7 |

---

## 9. Änderungsverlauf

| Version | Datum | Änderung |
|---|---|---|
| v1.2 | 2026-09-28 | Review-Feedback: Priorisierung v1/v1.1, DSGVO-Anforderungen geschärft (N1.5, N1.7), Berechtigungsmatrix §3.8, Backup-Verschlüsselung |
| v1.3 | 2026-09-29 | Redaktionell: Meilensteine als MS1–MS7 umbenannt und an den v1/v1.1-Schnitt angepasst; Tippfehler in N1.3 behoben; §3.8-Verweisliste korrigiert (T19 ist kein Export-Task). Keine inhaltliche Anforderungsänderung |
| v1.4 | 2026-09-29 | Ergänzungen aus Stack-Review: neu S4.6 (iCal-Feed, T16b) und N2.8 (Monitoring, T24b), beide v1.1; Technikentscheidungen in ADR-008 (HTMX/Alpine, T10b) und ADR-009 (Caddy/restic/Uptime Kuma, T24). N2.1 bleibt unverändert (restic erfüllt „verschlüsselt“) |
| v1.5 | 2026-09-30 | Neu §3.9 (S9.1–S9.4): öffentliche Vereinsseite in der Designsprache der Referenz-ZIP; Abgrenzung zum internen Design in [ADR-013](decisions/ADR-013-oeffentliche-designsprache.md). Alle vier Anforderungen gehen an T28 |
| v1.6 | 2026-10-04 | Schärfung für universelle Zugänglichkeit, Inklusion für alle Altersklassen (6–80+ Jahre) und Barrierefreiheit (WCAG 2.1 AA/AAA, Touch-Targets ≥ 44px, Textskalierung bis 200 %, Tastaturfokus) in §1, §4.2 (N2.3, N2.6) und §7 |
| v1.7 | 2026-10-05 | Integration von django-axes (Brute-Force-Schutz, N1.6) und django-debug-toolbar (Dev-Profiling & N+1-Prüfung, N2.2) gemäß ADR-015 |
| v1.8 | 2026-10-07 | Spezifikation der DSB-Schnittstellen-Architektur (K3.6) als Drei-Säulen-Modell (DWZ-Read-Sync, nuLiga-Mutations-Export, TRF/DeWIS) in [ADR-016](decisions/ADR-016-dsb-schnittstellen-architektur.md) |
| v1.9 | 2026-10-07 | Umsetzung der DSB-/DWZ-Synchronisation und Drift Detection (ADR-016, K3.6) in Task T29 |
| v2.0 | 2026-10-07 | SEPA-XML-Export (pain.008.001.02, S2.7) für Beitragsläufe gemäß ADR-017 / T9c |
| v2.1 | 2026-10-11 | Modul-Toggles (S7.4) im Django Admin Panel gemäß ADR-019 für Satellitenmodule spezifiziert (T30) |
