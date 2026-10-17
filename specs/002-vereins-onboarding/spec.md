# Feature Specification: Onboarding für einen neuen Schachverein

**Feature Branch**: `002-vereins-onboarding`

**Created**: 2026-10-16

**Status**: Specified

**Input**: User description: "onboarding für einen neuen Schachverein"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Geführter Erstkonfigurations-Assistent (Setup-Wizard) (Priority: P1)

Wenn ein Administrator oder Vereinsvorsitzender eine neue Vereinsinstanz in Betrieb nimmt oder die Ersteinrichtung startet, führt ihn ein mehrstufiger, leicht verständlicher Einrichtungs-Assistent durch alle essenziellen Grundeinstellungen. Der Assistent fragt schrittweise die Vereinsidentität (Vereinsname, Kürzel, Verbandszugehörigkeit, Spiellokal, Spielabend- und Jugendtrainingszeiten), die Beitragsstruktur (Vorauswahl typischer Beitragssätze für Erwachsene, Jugendliche, Ermäßigte) sowie die SEPA-Gläubiger- und Vereinskontodaten ab. Nach Durchlaufen der Schritte ist der Verein sofort mit einem vollständigen, konsistenten Profil einsatzbereit.

**Why this priority**: Ohne eine einfache, geführte Ersteinrichtung scheitert die Einführung neuer Software bei ehrenamtlich geführten Vereinen an Komplexität und unübersichtlichen Einstellungsmenüs. Ein klar strukturierter Wizard nimmt Berührungsängste und stellt die Datenqualität von Tag 1 an sicher.

**Independent Test**: Ein Administrator startet den Assistenten auf einer leeren Instanz, füllt die Masken der Schritte 1 bis 3 aus und schließt den Assistenten ab. Das System speichert die Daten im Vereinsprofil, richtet die Beitragskategorien ein und zeigt das Dashboard mit den echten Vereinsdaten an.

**Acceptance Scenarios**:

1. **Given** eine frische Installation ohne hinterlegte Vereinsstammdaten, **When** sich ein Administrator anmeldet, **Then** wird er mit einer freundlichen Begrüßung direkt in den Onboarding-Assistenten geleitet.
2. **Given** der Administrator befindet sich in Schritt 1 (Vereinsdaten), **When** er Name, Kürzel, Spiellokal und Trainingszeiten eingibt und auf „Weiter“ klickt, **Then** werden die Eingaben validiert und Schritt 2 (Beitragswesen) geöffnet.
3. **Given** der Administrator befindet sich in Schritt 2 (Beiträge), **When** er Standard-Kategorien (z. B. Vollzahler, Ermäßigt, Jugend) auswählt oder eigene Beträge ergänzt, **Then** werden diese Beitragskategorien und Jahresbeträge für das laufende Jahr vorbereitet.
4. **Given** der Administrator schließt den letzten Schritt ab, **When** er auf „Einrichtung abschließen“ klickt, **Then** wird das Vereinsprofil finalisiert, die Daten stehen sofort im gesamten System (öffentliche Seite, Dashboard, Beitragsmodul) zur Verfügung und der Assistent wird als abgeschlossen markiert.

---

### User Story 2 - Schnelle Mitglieder- und Bestandsdatenübernahme (Priority: P1)

Ein neuer Verein verfügt in der Regel über bestehende Mitgliederlisten (Excel/CSV) und/oder eine offizielle Vereinsmeldung beim Schachverband (DSB). Im Onboarding-Schritt „Datenübernahme“ kann der Administrator flexibel zwischen zwei gleichwertigen Wegen wählen (Hybrid-Modell): Entweder über einen geführten CSV-Import mit automatischer Spaltenerkennung und Dry-Run-Validierung oder über den automatischen Direktabruf aller gemeldeten Spieler und DWZ-Werte über die DSB-ZPS-Vereinsnummer. Das System prüft die Daten vor dem endgültigen Speichern und weist verständlich auf Dubletten oder fehlende Pflichtangaben hin.

**Why this priority**: Das manuelle Abtippen von 50 bis 150 Mitgliedern ist die größte Hürde für einen Wechsel zur neuen Software. Ein fehlerfreier, transparenter Import innerhalb weniger Minuten ist der entscheidende Erfolgsfaktor für das Vereins-Onboarding.

**Independent Test**: Der Administrator lädt im Onboarding eine bestehende Vereinsmitgliederliste als CSV hoch. Das System zeigt eine tabellarische Vorschau mit Zuordnungsprüfung an, meldet gefundene Unstimmigkeiten zur Korrektur und übernimmt nach Bestätigung alle validen Mitglieder mit Beitrags- und Mandatsdaten.

**Acceptance Scenarios**:

1. **Given** der Schritt „Mitglieder importieren“ im Onboarding, **When** der Admin eine CSV-Datei mit Mitgliedsdaten hochlädt, **Then** analysiert das System Kodierung, Trennzeichen und Spaltenköpfe und zeigt ein interaktives Zuordnungs- und Validierungsergebnis (Dry-Run).
2. **Given** eine CSV-Datei enthält fehlerhafte Zeilen (z. B. ungültiges Geburtsdatum), **When** der Vorab-Check läuft, **Then** werden die betroffenen Zeilen hervorgehoben und konkrete Korrekturhinweise gegeben, ohne dass fehlerhafte Datensätze importiert werden.
3. **Given** eine geprüfte und fehlerfreie Liste, **When** der Admin auf „Mitglieder jetzt importieren“ klickt, **Then** werden die Datensätze atomar angelegt, zugehörige SEPA-Mandate verschlüsselt gespeichert und der Fortschritt im Onboarding protokolliert.

---

### User Story 3 - Interaktive „Erste Schritte“-Checkliste im Dashboard (Priority: P2)

Nach Durchlaufen des Basis-Assistenten wird dem Vorstand auf der Dashboard-Startseite ein übersichtliches „Erste Schritte“-Widget angezeigt. Die Checkliste visualisiert den Einrichtungsfortschritt (z. B. „4 von 6 Schritten erledigt“) und führt den Vorstand gezielt zu den nächsten praxisrelevanten Aktionen: z. B. Mannschaften für den Ligabetrieb anlegen, Vorstandskollegen einladen oder den ersten Probelauf für Beiträge starten. Jeder Eintrag besitzt eine 1-Klick-Verlinkung direkt zur passenden Maske. Ist das Onboarding komplett, kann die Checkliste dauerhaft minimiert oder ausgeblendet werden.

**Why this priority**: Nach der Ersteinrichtung stehen Vorstände oft vor der Frage: „Was muss ich jetzt als Nächstes tun?“. Die Checkliste bietet Orientierung über die ersten Wochen hinweg und stellt sicher, dass keine wichtigen organisatorischen Schritte vergessen werden.

**Independent Test**: Ein Administrator sieht nach dem Ersteinrichtungs-Wizard das Checklist-Widget mit offenen Aufgaben. Durch Erledigen einer Aufgabe (z. B. Anlegen einer Mannschaft) wechselt der Status des Punktes automatisch auf erledigt und der Fortschrittsbalken wächst.

**Acceptance Scenarios**:

1. **Given** ein neu eingerichteter Verein mit offenen Aufgaben, **When** der Vorstand das Dashboard aufruft, **Then** wird die „Erste Schritte“-Checkliste gut sichtbar am Seitenanfang mit dem aktuellen Erledigungsgrad angezeigt.
2. **Given** der Punkt „Erste Mannschaft anlegen“ ist noch offen, **When** der Admin auf den Link der Aufgabe klickt, **Then** gelangt er direkt in die Maske zur Mannschaftsanlage.
3. **Given** eine Mannschaft wurde erfolgreich gespeichert, **When** der Admin zum Dashboard zurückkehrt, **Then** ist der Punkt mit einem grünen Haken markiert und der Fortschrittszähler aktualisiert.
4. **Given** alle empfohlenen Schritte sind abgeschlossen, **When** der Vorstand auf „Checkliste abschließen / ausblenden“ klickt, **Then** verschwindet das Widget und macht Platz für die reguläre Betriebsansicht.

---

### User Story 4 - Sanfter Übergang von Testbetrieb zu Produktivdaten (Priority: P2)

Wenn ein neuer Verein die Software zunächst mit Beispieldaten (Demo-Daten) getestet hat, um Funktionen wie den Turniermodus oder Mannschaftskämpfe auszuprobieren, ermöglicht das Onboarding einen geführten Übergang zum scharfen Produktivbetrieb. Der Administrator kann die Beispieldaten sicher und rückstandsfrei entfernen, ohne versehentlich bereits manuell gepflegte Vereinsstammdaten oder echte Administrator-Zugänge zu löschen.

**Why this priority**: Viele Vereine evaluieren die Software anhand von Demo-Daten. Der Wechsel von „Testen“ auf „Produktivstart“ muss absolut fehlersicher sein, damit keine Beispieldaten im echten Ligabetrieb oder Kassenbuch verbleiben.

**Independent Test**: Auf einer Instanz mit aktiven Demo-Daten startet der Admin die Aktion „In den Produktivbetrieb wechseln“. Das System listet transparent auf, welche Beispieldaten gelöscht werden, verlangt eine explizite Bestätigung und hinterlässt eine saubere, produktionsbereite Datenbank mit den konfigurierten Vereinsstammdaten.

**Acceptance Scenarios**:

1. **Given** eine Instanz mit geladenen Demo-Daten, **When** der Admin den Einrichtungsassistenten oder das Onboarding-Dashboard öffnet, **Then** weist ein Status-Banner darauf hin, dass derzeit Demo-Daten aktiv sind, inklusive Schaltfläche „Demo-Daten für Produktivstart bereinigen“.
2. **Given** der Admin klickt auf Bereinigung, **When** er den Sicherheitsdialog bestätigt, **Then** werden alle generierten Testmitglieder, Testpartien und Testbuchungen gelöscht; das Vereinsprofil und der Administrator-Account bleiben vollständig erhalten.
3. **Given** es wurden bereits echte Mitglieder manuell angelegt, **When** eine Bereinigung versucht wird, **Then** verhindert das System die Ausführung und schützt die echten Daten vor Verlust.

---

### User Story 5 - Einladung von Funktionären & Vorstandskollegen (Priority: P3)

Der Hauptadministrator kann im Rahmen des Onboardings weitere Vorstandsmitglieder (z. B. Kassenwart, Schriftführer) sowie Mannschaftsführer und Jugendleiter per E-Mail-Einladung an Bord holen. Das System generiert hierfür einen personalisierten, zeitlich befristeten Einladungslink mit sicherem kryptografischem Token, über den die eingeladenen Funktionäre ihr Passwort eigenständig festlegen. Jeder Nutzer erhält automatisch die passende Berechtigungsgruppe gemäß der PRD-Berechtigungsmatrix (§3.8).

**Why this priority**: Vereinsarbeit ist Teamarbeit. Ein Verein kann erst dann reibungslos arbeiten, wenn Kassenwart, Mannschaftsführer und Vorstand ihre jeweiligen Aufgabenbereiche eigenständig im System wahrnehmen können.

**Independent Test**: Der Administrator gibt Name, E-Mail-Adresse und Rolle (z. B. Kassenwart) für einen Kollegen ein. Das System erzeugt den Zugang/die Einladung; die eingeladene Person kann sich anmelden und sieht exakt die für ihre Rolle freigegebenen Bereiche.

**Acceptance Scenarios**:

1. **Given** der Schritt „Funktionäre einladen“, **When** der Administrator Vorname, Nachname, E-Mail und Rolle („Kassenwart“) eingibt und abschickt, **Then** wird der Einladungsprozess gestartet und der Status auf „Eingeladen“ gesetzt.
2. **Given** ein eingeladener Funktionär ruft seinen Einladungslink auf, **When** er sein persönliches Passwort vergibt, **Then** wird sein Benutzerkonto aktiviert und er wird direkt in sein rollenspezifisches Dashboard geleitet.
3. **Given** ein eingeladener Kassenwart meldet sich an, **When** er das System nutzt, **Then** hat er Zugriff auf Kassenbuch und Beiträge, aber keine Superadmin-Rechte.

---

### Edge Cases

- **Abbruch mitten im Onboarding-Assistenten**: Schließt der Administrator den Browser während des Wizards, bleiben alle bis zum aktuellen Einzelschritt gespeicherten Angaben erhalten; beim nächsten Aufruf setzt der Assistent an der zuletzt offenen Station an.
- **Fehlende Internetverbindung bei externem Abgleich**: Schlägt ein Verbands- oder ZPS-Abruf fehl, wird der Administrator nicht blockiert, sondern kann die Stammdaten jederzeit manuell eingeben oder überspringen.
- **Bereits vorhandene Altdaten**: Versucht ein Administrator das Onboarding auf einer Instanz zu starten, auf der bereits Produktivdaten existieren, verlangt das System eine zusätzliche Sicherheitsbestätigung, um ein Überschreiben vorhandener Vereinsdaten auszuschließen.
- **Sehr kleine Vereine ohne SEPA/Lastschrift**: Ein Verein, der Beiträge ausschließlich per Barzahlung oder Überweisung abwickelt, kann die Eingabe von SEPA-Gläubiger-ID und IBAN überspringen, ohne dass das System fehlerhaft blockiert.
- **Zugriffssteuerung während des Onboardings**: Normale Vereinsmitglieder oder Gäste, die die Vereinsseite aufrufen, während das Onboarding noch läuft, sehen eine saubere Platzhalter- oder Basisseite; der Einrichtungsbereich ist strikt auf die Administrator-Rolle beschränkt (`@role_required(ADMIN_GROUP)`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Das System MUSS einen mehrstufigen Einrichtungs-Assistenten (Wizard) bereitstellen, der die Kernkonfiguration eines neuen Vereins (Profil & Stammdaten, Beitragswesen, Modulauswahl) in einer geführten Schrittfolge abbildet.
- **FR-002**: Das System MUSS während des Onboardings die Eingabe und Validierung zentraler Vereinsdaten ermöglichen: Vereinsname, Kurzname/Kürzel, Verbandskennung, Gründungsjahr, Adresse/Spiellokal, Spielabend- und Jugendtrainingszeiten sowie offizielle Kontaktadresse.
- **FR-003**: Das System MUSS Vorlagen für gängige Beitragskategorien (z. B. Erwachsene, Ermäßigte, Jugendliche, Passive) anbieten, die mit einem Klick übernommen und im Betrag angepasst werden können.
- **FR-004**: Das System MUSS neue Administratoren bei noch unvollständigen Vereinsstammdaten nach der Erstanmeldung automatisch per Erst-Redirect in den Onboarding-Assistenten (`/onboarding/`) leiten. Der Administrator kann den Wizard jederzeit pausieren, zwischenspeichern und über das Dashboard oder den Menüpunkt wieder aufrufen.
- **FR-005**: Das System MUSS im Onboarding-Schritt für Mitgliederdaten zwei gleichwertige Übernahmewege anbieten (Hybrid-Auswahl): (a) den automatischen Direktabruf aller spielberechtigten Mitglieder mit aktuellen DWZ-Zahlen über die ZPS-Vereinskennung aus dem DSB-Portal, sowie (b) den dateibasierten CSV-Import mit automatischer Spaltenerkennung, Plausibilitätsprüfung (Dry-Run) und verschlüsselter SEPA-Mandatsanlage.
- **FR-006**: Das System MUSS nach Abschluss des Basis-Wizards ein interaktives „Erste Schritte“-Fortschritts-Widget auf dem Vorstandsdashboard einblenden, das offene Meilensteine (Mitgliederbestand, Mannschaften, Funktionäre, Probelauf) anzeigt und direkt verlinkt.
- **FR-007**: Das Dashboard-Fortschritts-Widget MUSS sich automatisch aktualisieren, sobald verknüpfte Entitäten (z. B. erste Mannschaft angelegt, Mindestanzahl an Mitgliedern importiert) im System erzeugt werden, und MUSS vom Administrator manuell ausgeblendet werden können.
- **FR-008**: Das System MUSS erkennen, wenn die Instanz aktuell mit Demo-Daten betrieben wird, und im Onboarding eine sichere Bereinigungsfunktion zur Verfügung stellen, die Testdaten rückstandsfrei entfernt, ohne echte Stammdaten oder Admin-Accounts zu gefährden.
- **FR-009**: Das System MUSS im Rahmen des Onboardings die Einladung von Funktionären (Vorstandsmitglieder, Mannschaftskapitäne) über sichere Einladungs-Links per E-Mail unterstützen, über die eingeladene Personen ihr persönliches Passwort eigenständig vergeben und automatisch der korrekten Berechtigungsgruppe gemäß PRD §3.8 zugewiesen werden.
- **FR-010**: Alle im Rahmen des Onboardings durchgeführten Stammdatenänderungen, Importe und Einladungen MÜSSEN manipulationssicher mit Zeitstempel und ausführendem Benutzer im zentralen AuditLog protokolliert werden.
- **FR-011**: Sämtliche Onboarding-Masken MÜSSEN die Vorgaben von WCAG 2.1 AA einhalten (keine reinen Farbcodierungen, vollständige Tastaturbedienbarkeit, fehlerfreie Darstellung auf 360 px mobilen Bildschirmen und 1280 px Desktop-Displays ohne horizontalen Overflow).

### Key Entities *(include if feature involves data)*

- **Vereinsprofil (ClubProfile)**: Speichert die Stammdaten des Vereins (Name, Kürzel, Spiellokal, Trainingszeiten, SEPA-Gläubiger-ID, Bankverbindung) als Datenbank-Singleton mit Fallback auf die Konfiguration.
- **Onboarding-Status (OnboardingState / OnboardingProgress)**: Nachweis über den aktuellen Fortschritt der Inbetriebnahme (aktiver Schritt, Liste erledigter Meilensteine, Zeitpunkt des Abschlusses, Sichtbarkeits-Flag des Dashboard-Widgets).
- **Einrichtungsschritt (OnboardingStep)**: Definiert die modularen Meilensteine (z. B. `profile_completed`, `fees_configured`, `members_imported`, `teams_created`, `staff_invited`).
- **Funktionärseinladung (StaffInvitation)**: Temporäre Einladung für Vorstandsmitglieder oder Kapitäne mit kryptografischem Einladungs-Token, Ablaufdatum, Ziel-E-Mail und zugeordneter Rolle.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ein ehrenamtlicher Vereinsvorsitzender kann die vollständige Ersteinrichtung eines Vereins (Stammdaten, Beitragssätze, Basiskonfiguration) im Assistenten in unter 10 Minuten erfolgreich abschließen.
- **SC-002**: Mindestens 90 % der neuen Vereinsadministratoren bewältigen den Onboarding-Prozess beim ersten Versuch ohne Rückfragen oder technischen Support.
- **SC-003**: Die Übernahme einer typischen Vereinsmitgliederliste (50 bis 150 Datensätze) erfolgt im Onboarding inklusive Vorab-Prüfung in unter 3 Minuten.
- **SC-004**: Bei der Bereinigung von Demo-Daten für den Produktivstart verbleiben 0 Testdatensätze in der Datenbank, während 100 % der konfigurierten Vereinsprofileinstellungen und Administratorzugänge intakt bleiben.
- **SC-005**: 100 % der Eingabemasken des Onboardings sind auf mobilen Endgeräten (ab 360 px Breite) ohne horizontalen Bildlauf und vollständig per Tastatur bedienbar.

## Assumptions

- **A-001**: Der einrichtende Administrator verfügt über grundlegende Daten des Vereins (Vereinsname, Anschrift des Spiellokals, vereinsinterne Beitragshöhen sowie ggf. Gläubiger-ID und IBAN, falls Lastschriften genutzt werden).
- **A-002**: Für den E-Mail-Versand (z. B. Einladungen von Funktionären) steht ein konfigurierter SMTP-Dienst zur Verfügung; in lokalen Entwicklungs- und Testumgebungen wird das Django-Console-Backend genutzt.
- **A-003**: Ein Verein betreibt die Software im Single-Tenant-Modus auf eigener Infrastruktur oder dediziertem Serverhost; das Onboarding richtet die lokale Datenbank der Organisation ein.
- **A-004**: Bei Importen aus Alt-Systemen liegen die Mitgliederdaten in strukturierter digitaler Form (CSV-, TSV- oder Excel-kompatibel) vor.
- **A-005**: Datenschutzvorgaben (DSGVO) verbieten die Weitergabe von Bestandsdaten an externe Dienste; alle Import- und Validierungsschritte finden ausschließlich lokal auf dem Server statt.
