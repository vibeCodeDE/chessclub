"""Inhalte der Produkt-Landingpage (/produkt/).

Alles, was sich für den Verkauf ändert (Preise, Funktionsliste, FAQ), steht hier
an einer Stelle – das Template enthält nur Darstellung.

Die Preise sind **festgelegt**, nicht mehr Entwurf. Grundlage und Kalkulation:
ADR-014 (docs/decisions/ADR-014-preisgestaltung.md). Wer Preise, Laufzeit oder
die Einrichtungsregel ändert, ändert zuerst das ADR.
"""

# Endpreise gemäß § 19 UStG (Kleinunternehmerregelung): keine Umsatzsteuer im Preis.
# Standard ist die Jahreszahlung; monatliche Zahlung kostet 20 % Aufschlag (gerundet).
PREISHINWEIS = (
    "Alle Preise sind Endpreise – es wird keine Umsatzsteuer berechnet "
    "(Kleinunternehmerregelung gemäß § 19 UStG). Die Preise gelten bei "
    "Jahreszahlung für eine Vertragslaufzeit von zwölf Monaten; bei monatlicher "
    "Zahlung gilt ein Aufschlag von 20 %."
)

PREISSTUFEN = [
    {
        "name": "Start",
        "fuer": "Kleine Vereine bis 60 Mitglieder",
        "preis": "19",
        "jahr": "228",
        "preis_monatlich": "23",
        "einrichtung": "99 € einmalig",
        "hervorgehoben": False,
        "punkte": [
            "Mitglieder, Beiträge, Kassenbuch",
            "Turniere mit öffentlicher Anmeldung",
            "Öffentliche Vereinsseite mit News und Terminen",
            "Eigene Instanz, Hosting in der EU, tägliche Backups",
            "Support per E-Mail",
        ],
    },
    {
        "name": "Verein",
        "fuer": "Bis 150 Mitglieder, mit Spielbetrieb",
        "preis": "35",
        "jahr": "420",
        "preis_monatlich": "42",
        "einrichtung": "inklusive",
        "hervorgehoben": True,
        "punkte": [
            "Alles aus „Start“",
            "Mannschaften, Aufstellungen, Ligatabellen",
            "Rundbriefe per E-Mail an Gruppen",
            "Zwei-Faktor-Anmeldung für den Vorstand",
            "Datenübernahme aus Excel oder CSV inklusive",
            "Vorstandsübergabe: eine Stunde Einweisung für die Nachfolge",
        ],
    },
    {
        "name": "Verband",
        "fuer": "Große Vereine mit 151 bis 400 Mitgliedern",
        "preis": "69",
        "jahr": "828",
        "preis_monatlich": "82",
        "einrichtung": "inklusive",
        "hervorgehoben": False,
        "punkte": [
            "Alles aus „Verein“",
            "Bis zu 400 Mitglieder",
            "Eigene Domain (portal.ihrverein.de)",
            "Persönliche Einweisung für den Vorstand",
            "Bevorzugter Support und zweites Vorstandskonto",
        ],
    },
]

FUNKTIONEN = [
    {
        "icon": "users",
        "titel": "Mitgliederverwaltung",
        "text": "Stammdaten, Status und Rollen an einem Ort. Mitglieder reichen Änderungen selbst ein, der Vorstand gibt sie frei.",
    },
    {
        "icon": "wallet",
        "titel": "Beiträge und Mahnwesen",
        "text": "Beitragssätze, Jahresläufe, SEPA-Mandate, Zahlungsstatus und Mahnstufen. Der Einzug selbst bleibt bei Ihrer Bank.",
    },
    {
        "icon": "trophy",
        "titel": "Turniere",
        "text": "Anmeldung, Auslosung, Ergebniserfassung und Tabellen. Mit Druckansicht und CSV-Export für ChessResults.",
    },
    {
        "icon": "flag",
        "titel": "Spielbetrieb",
        "text": "Mannschaften, Ligaspiele, Aufstellungen und Tabellen. Kapitäne melden und erfassen direkt selbst.",
    },
    {
        "icon": "megaphone",
        "titel": "Website und Rundbriefe",
        "text": "Die App liefert die öffentliche Vereinsseite mit News und Terminen gleich mit. Rundbriefe gehen an Gruppen, nicht an Einzeladressen.",
    },
    {
        "icon": "book",
        "titel": "Kassenbuch",
        "text": "Einnahmen und Ausgaben mit Jahresabschluss für die Kassenprüfung, auch als Export.",
    },
]

DATENSCHUTZ_PUNKTE = [
    "Hosting und Datenhaltung in der EU (DSGVO-konform), keine Tracker, keine externen CDNs",
    "Datenauskunft pro Mitglied als PDF und JSON auf Knopfdruck",
    "Audit-Protokoll für Zugriffe auf Personendaten",
    "Ausgetretene Mitglieder werden nach Fristablauf anonymisiert",
    "Zwei-Faktor-Anmeldung für den Vorstand",
    "Verzeichnis der Verarbeitungstätigkeiten als CSV",
]

SCHRITTE = [
    ("Kennenlernen", "Sie sehen die Software in einer Demo mit Beispieldaten. Kostenlos und unverbindlich, etwa 30 Minuten."),
    ("Testen", "Sie bekommen eine eigene Instanz mit Ihren Vereinsdaten und arbeiten 30 Tage damit. Keine Zahlungsdaten, keine Kündigungsfrist."),
    ("Einrichten", "Wir setzen Beitragssätze und Zugänge auf und übernehmen Ihre Mitgliederliste – in „Verein“ und „Verband“ ohne Aufpreis."),
    ("Loslegen", "Der Vorstand arbeitet von Tag eins im System. Die Mitglieder bekommen ihren Zugang per E-Mail."),
]

FAQ = [
    (
        "Was kostet die Software?",
        "19, 35 oder 69 Euro im Monat, je nach Vereinsgröße. Das sind Endpreise; Umsatzsteuer fällt nicht an "
        "(Kleinunternehmerregelung gemäß § 19 UStG). Die Preise gelten bei Jahreszahlung, etwa 228 Euro für die "
        "Stufe „Start“ im ersten Jahr. Wer monatlich zahlen möchte, zahlt 20 % Aufschlag. Hinzu kommt einmalig "
        "die Einrichtung: 99 Euro in der Stufe „Start“, in den beiden größeren Stufen ist sie inklusive.",
    ),
    (
        "Können wir die Software vorher ausprobieren?",
        "Ja. Sie bekommen 30 Tage lang eine eigene Instanz mit Demo-Daten, ohne Zahlungsdaten und ohne "
        "Verpflichtung. Danach entscheiden Sie – oder wir löschen die Instanz.",
    ),
    (
        "Wie lange läuft der Vertrag?",
        "Zwölf Monate. Er verlängert sich um weitere zwölf Monate, wenn niemand kündigt; die Kündigungsfrist "
        "beträgt einen Monat vor Ablauf. Der Preis gilt für die gesamte Laufzeit und wird für Bestandskunden "
        "mindestens 24 Monate nicht erhöht.",
    ),
    (
        "Wie bezahlen wir?",
        "Per Rechnung, entweder als SEPA-Basislastschrift oder per Überweisung. Standard ist die jährliche "
        "Zahlung, weil das zum Haushaltsjahr eines Vereins passt. Eine Kreditkarte brauchen Sie nicht.",
    ),
    (
        "Was passiert mit unseren Daten, wenn wir kündigen?",
        "Sie exportieren Ihre Daten jederzeit als CSV – auch während der Laufzeit. Nach Vertragsende bleibt die "
        "Instanz vier Wochen zum Export erreichbar, danach löschen wir sie samt Backups.",
    ),
    (
        "Wie kommen unsere vorhandenen Daten hinein?",
        "Beim Einrichten übernehmen wir Ihre Mitgliederliste, zum Beispiel aus Excel oder CSV. In den Tarifen "
        "„Verein“ und „Verband“ ist das inklusive, in „Start“ kostet es einmalig 99 Euro.",
    ),
    (
        "Unser Verein wächst über die Stufengrenze hinaus. Und jetzt?",
        "Die Grenzen sind Planungsgrenzen, keine harte Sperre. Wir sprechen vor dem nächsten Vertragsjahr über "
        "den Wechsel in die passende Stufe; eine Nachzahlung für die laufende Laufzeit gibt es nicht.",
    ),
    (
        "Gibt es Rabatte für mehrere Vereine?",
        "Ja. Ab drei Instanzen eines Trägers – Spielgemeinschaft, Bezirk, Landesverband – geben wir 10 %, ab fünf "
        "15 %. Außerdem schreiben wir werbenden und geworbenen Vereinen jeweils einen Monat gut.",
    ),
    (
        "Wo liegen unsere Daten?",
        "Jeder Verein bekommt eine eigene Instanz mit eigener Datenbank bei einem Cloud-Anbieter mit Serverstandort "
        "in der Europäischen Union (z. B. Scalingo, ISO 27001). Keine US-Cloud, keine Datenübermittlung in Drittstaaten. "
        "Die Daten verschiedener Vereine werden nicht gemischt.",
    ),
    (
        "Brauchen wir einen Auftragsverarbeitungsvertrag?",
        "Ja, und wir stellen ihn bereit. Er gehört zu jedem Vertrag dazu.",
    ),
    (
        "Zieht die Software die Beiträge automatisch ein?",
        "Nein. Sie verwaltet Mandate, Forderungen und Zahlungsstatus. Der Lastschrifteinzug läuft weiter über die "
        "Bank des Vereins. So behalten Sie die volle Kontrolle.",
    ),
    (
        "Funktioniert das auf dem Smartphone?",
        "Ja. Die Oberfläche ist für kleine Bildschirme gebaut und lässt sich wie eine App auf dem Homescreen "
        "installieren.",
    ),
]

ROLLEN_SCHMERZPUNKTE = [
    {
        "id": "vorstand",
        "titel": "1. Vorsitzender & Vorstand",
        "kurztitel": "Vorstand",
        "icon": "shield",
        "slogan": "Volle Kontrolle über den Verein – ohne Haftungsrisiken und Übergabe-Chaos.",
        "ersparnis": "Kein Datenverlust beim Vorstandswechsel, 100 % DSGVO-sicher",
        "schmerzpunkte": [
            {
                "titel": "Chaotische Vorstandsübergabe",
                "problem": "Daten auf privaten Festplatten, Passwörter auf Zetteln, Vereinswissen geht beim Wechsel verloren.",
                "loesung": "Zentrale Vereinsplattform: Neuer Vorstand übernimmt alle Daten mit einem einzigen Klick und vollständiger Historie.",
                "detail": "Revisionssichere Übergabe, keine Excel-Dateien per privater E-Mail.",
            },
            {
                "titel": "Haftungs- & DSGVO-Risiken",
                "problem": "DSGVO-Auskunftsersuchen von Mitgliedern sind ein Albtraum, Daten liegen an fünf verschiedenen Orten.",
                "loesung": "Datenauskunft nach Art. 15 DSGVO auf Knopfdruck als PDF und JSON, lückenloses Audit-Protokoll aller Datenzugriffe.",
                "detail": "Hosting in der EU, 0 Tracker, 0 externe CDNs.",
            },
            {
                "titel": "Fehlende Gesamtübersicht",
                "problem": "Wer ist aktiv? Welche Beiträge fehlen? Wie laufen die Mannschaften? Keine aktuellen Zahlen parat.",
                "loesung": "Kompaktes Vorstand-Dashboard mit Mitgliederzahlen, offenen Forderungen und Spielbetrieb in Echtzeit.",
                "detail": "Alle Berichte sofort druckbar für die Jahreshauptversammlung.",
            },
        ],
        "vorschau": {
            "typ": "dashboard",
            "fenster_titel": "Vorstand – Zentrale Übersicht & DSGVO",
            "status_badge": "Live-Übersicht",
            "metriken": [
                {"label": "Mitglieder aktiv", "wert": "87", "status": "ok"},
                {"label": "Offene Beiträge", "wert": "1.240 €", "status": "warn"},
                {"label": "Audit-Einträge (30 Tage)", "wert": "14", "status": "info"},
            ],
            "zeilen": [
                {"icon": "shield", "label": "Art. 15 DSGVO Datenauskunft", "status": "Bereit als PDF", "badge": "1-Klick"},
                {"icon": "lock", "label": "Audit: Beitragsänderung protokolliert", "status": "Heute, 14:20 Uhr", "badge": "Protokoll"},
                {"icon": "check", "label": "Vorstandsübergabe-Status", "status": "Alle Mandate & Rollen synchron", "badge": "Sicher"},
            ],
            "aktionen": [
                {"id": "uebersicht", "label": "Dashboard", "aktiv": True},
                {"id": "audit", "label": "Audit-Log", "aktiv": False},
                {"id": "dsgvo", "label": "DSGVO-Export", "aktiv": False},
            ],
            "sub_ansichten": [
                {
                    "id": "uebersicht",
                    "label": "Dashboard",
                    "zeilen": [
                        {"icon": "users", "label": "Aktive Vereinsmitglieder", "status": "87 gemeldet (72 Vollzahler, 15 Jugend)", "badge": "Synchron"},
                        {"icon": "wallet", "label": "Offene Beitragsforderungen", "status": "1.240 € (3 Rücklastschriften zu klären)", "badge": "3 Mahnungen"},
                        {"icon": "trophy", "label": "Vereinsmeisterschaft 2026", "status": "Runde 3 von 5 im Schweizer System aktiv", "badge": "In Prüfung"},
                    ],
                },
                {
                    "id": "audit",
                    "label": "Audit-Log",
                    "zeilen": [
                        {"icon": "lock", "label": "Beitragsänderung: M. Mustermann", "status": "Heute, 14:20 Uhr · Geändert von Admin", "badge": "Protokoll"},
                        {"icon": "user", "label": "Neues Mitglied aufgenommen", "status": "Gestern, 18:05 Uhr · Status: Aktiv", "badge": "Aufnahme"},
                        {"icon": "shield", "label": "Art. 15 Datenauskunft exportiert", "status": "12.10.2026, 09:15 Uhr · PDF-Generierung", "badge": "DSGVO"},
                    ],
                },
                {
                    "id": "dsgvo",
                    "label": "DSGVO-Export",
                    "zeilen": [
                        {"icon": "download", "label": "Datenauskunft nach Art. 15 DSGVO", "status": "Vollständiges Mitgliederprofil mit Mandaten", "badge": "PDF-Export"},
                        {"icon": "table", "label": "Verarbeitungsverzeichnis (VVT)", "status": "Standardkonforme CSV für den Datenschutzbeauftragten", "badge": "CSV-Export"},
                        {"icon": "shield", "label": "Revisionssicheres Berechtigungskonzept", "status": "3 Gruppen gemäß PRD-Matrix §3.8 aktiv", "badge": "Geprüft"},
                    ],
                },
            ],
        },
    },
    {
        "id": "kassenwart",
        "titel": "Kassenwart & Finanzen",
        "kurztitel": "Kassenwart",
        "icon": "wallet",
        "slogan": "Beitragseinzug in 15 Minuten statt 15 Stunden nervenaufreibender Excel-Schlachten.",
        "ersparnis": "~15 Stunden Zeitersparnis pro Beitragseinzug",
        "schmerzpunkte": [
            {
                "titel": "Komplizierter Beitragseinzug",
                "problem": "Unterschiedliche Sätze (Jugend, Ermäßigt, Vollzahler), manuelle SEPA-Listen, fehleranfälliges Abtippen.",
                "loesung": "Automatischer Beitragslauf nach Satzung, 1-Klick-Download standardkonformer SEPA-XML-Dateien (pain.008) für Ihre Bank.",
                "detail": "Verschlüsselte IBAN-Speicherung, Idempotenz verhindert Doppeleinzüge.",
            },
            {
                "titel": "Säumige Zahler & Mahnchaos",
                "problem": "Wer hat noch nicht gezahlt? Mahnungen werden aufgeschoben, weil das Heraussuchen zu lange dauert.",
                "loesung": "Automatische Mahnstufen mit druckbaren, formellen Mahnbriefen auf Knopfdruck.",
                "detail": "Klare Nachvollziehbarkeit: Mahnstufe 1 bis 3 mit Fristen und Gebühren.",
            },
            {
                "titel": "Stress bei der Kassenprüfung",
                "problem": "Kassenprüfer finden Unstimmigkeiten zwischen Belegen, Kontoauszügen und Mitgliederstand.",
                "loesung": "Revisionssicheres Kassenbuch: Einnahmen und Ausgaben mit Kassenabschluss und CSV-/PDF-Export.",
                "detail": "Korrekturen erfolgen nur per Gegenbuchung – absolut prüfungssicher.",
            },
        ],
        "vorschau": {
            "typ": "sepa",
            "fenster_titel": "Kassenwesen – SEPA-Einzug & Mahnwesen",
            "status_badge": "SEPA pain.008 bereit",
            "metriken": [
                {"label": "Beitragslauf 2026", "wert": "5.420 €", "status": "ok"},
                {"label": "Offene Posten", "wert": "3 Mitglieder", "status": "warn"},
                {"label": "SEPA-Mandate aktiv", "wert": "84 / 87", "status": "info"},
            ],
            "zeilen": [
                {"icon": "download", "label": "SEPA-XML Export (pain.008)", "status": "84 Lastschriften generiert", "badge": "Bankbereit"},
                {"icon": "alert", "label": "Mahnung Stufe 1: Max Mustermann", "status": "Fällig seit 14 Tagen (60 €)", "badge": "Mahnung"},
                {"icon": "book", "label": "Kassenabschluss laufendes Quartal", "status": "Saldo: +3.850,00 € ausgeglichen", "badge": "Geprüft"},
            ],
            "aktionen": [
                {"id": "lauf", "label": "SEPA-Lauf", "aktiv": True},
                {"id": "mahnungen", "label": "Mahnungen", "aktiv": False},
                {"id": "kasse", "label": "Kassenbuch", "aktiv": False},
            ],
            "sub_ansichten": [
                {
                    "id": "lauf",
                    "label": "SEPA-Lauf",
                    "zeilen": [
                        {"icon": "download", "label": "SEPA-XML Export (pain.008)", "status": "84 Lastschriften generiert", "badge": "Bankbereit"},
                        {"icon": "lock", "label": "IBAN-Verschlüsselung (AES-256)", "status": "Alle Kontoverbindungen revisionssicher geschützt", "badge": "Sicher"},
                        {"icon": "check", "label": "Idempotenz-Garantie", "status": "Doppelter Einzug technisch ausgeschlossen", "badge": "Valide"},
                    ],
                },
                {
                    "id": "mahnungen",
                    "label": "Mahnungen",
                    "zeilen": [
                        {"icon": "alert", "label": "Mahnung Stufe 1: Max Mustermann", "status": "Fällig seit 14 Tagen (60 €) · Brief erzeugt", "badge": "Mahnung 1"},
                        {"icon": "alert", "label": "Mahnung Stufe 2: Thomas Becker", "status": "Fällig seit 35 Tagen (75 €) · Frist: 7 Tage", "badge": "Mahnung 2"},
                        {"icon": "print", "label": "Druckfertiger Mahnbrief", "status": "Satzungsgemäße Gebühren & Fristen", "badge": "Drucken"},
                    ],
                },
                {
                    "id": "kasse",
                    "label": "Kassenbuch",
                    "zeilen": [
                        {"icon": "book", "label": "Kassenabschluss laufendes Quartal", "status": "Saldo: +3.850,00 € ausgeglichen", "badge": "Geprüft"},
                        {"icon": "refresh", "label": "Storno per Gegenbuchung", "status": "Kein Löschen – lückenlose Kassenprüfspur", "badge": "GoBD"},
                        {"icon": "download", "label": "Jahresbericht für Prüfer", "status": "Vollständiger PDF- & CSV-Export", "badge": "Export"},
                    ],
                },
            ],
        },
    },
    {
        "id": "spielleiter",
        "titel": "Turnierleiter & Spielleiter",
        "kurztitel": "Spielleiter",
        "icon": "trophy",
        "slogan": "Turniere professionell ausrichten – ohne Auslosungsstress am Vereinsabend.",
        "ersparnis": "45 Minuten Hektik pro Spielabend eingespart",
        "schmerzpunkte": [
            {
                "titel": "Zettelwirtschaft & Paarungschaos",
                "problem": "Handschriftliche Turnierkarten, wer hatte Weiß gegen wen? Streit um Farbverteilung und Paarungen.",
                "loesung": "Integrierter Paarungs-Algorithmus nach Schweizer System und Rundenturnier mit automatischer Farbfolge.",
                "detail": "Sofort druckbare Runden- und Paarungszettel für das Brett.",
            },
            {
                "titel": "Mühsame Online-Anmeldung",
                "problem": "Anmeldungen kommen per WhatsApp, Mail und Zuruf. Niemand weiß, wer pünktlich anwesend ist.",
                "loesung": "Öffentliche Turnieranmeldeseite mit Live-Teilnehmerliste, DWZ-Angabe und 1-Klick-Anwesenheitskontrolle.",
                "detail": "Vollständig in die Vereinswebsite integriert, kein externes Tool nötig.",
            },
            {
                "titel": "Ergebnismeldung & Tabellen",
                "problem": "Ergebnisse müssen für die Website mühsam abgetippt werden, Tabellen sind tagelang veraltet.",
                "loesung": "Ergebnisse direkt am Spielabend im Smartphone eingeben: Tabelle und Rangliste aktualisieren sich in Echtzeit.",
                "detail": "CSV-Export für ChessResults oder Verbandsberichterstattung inklusive.",
            },
        ],
        "vorschau": {
            "typ": "turnier",
            "fenster_titel": "Turnierleiter – Vereinsmeisterschaft (Schweizer System)",
            "status_badge": "Runde 3 läuft",
            "metriken": [
                {"label": "Teilnehmer", "wert": "24 Spieler", "status": "ok"},
                {"label": "Modus", "wert": "5 Runden CH", "status": "info"},
                {"label": "Partien beendet", "wert": "9 / 12", "status": "ok"},
            ],
            "zeilen": [
                {"icon": "swords", "label": "Brett 1: FM Schmidt (2150) – Müller (1980)", "status": "1 - 0 gemeldet", "badge": "Ergebnis"},
                {"icon": "swords", "label": "Brett 2: Weber (1890) – Becker (1920)", "status": "½ - ½ gemeldet", "badge": "Remis"},
                {"icon": "refresh", "label": "Runde 4 Auslosung", "status": "Bereit nach Runde 3", "badge": "Autopilot"},
            ],
            "aktionen": [
                {"id": "paarung", "label": "Paarungen", "aktiv": True},
                {"id": "tabelle", "label": "Rangliste", "aktiv": False},
                {"id": "druck", "label": "Druckzettel", "aktiv": False},
            ],
            "sub_ansichten": [
                {
                    "id": "paarung",
                    "label": "Paarungen",
                    "zeilen": [
                        {"icon": "swords", "label": "Brett 1: FM Schmidt (2150) – Müller (1980)", "status": "1 - 0 gemeldet", "badge": "Ergebnis"},
                        {"icon": "swords", "label": "Brett 2: Weber (1890) – Becker (1920)", "status": "½ - ½ gemeldet", "badge": "Remis"},
                        {"icon": "refresh", "label": "Runde 4 Auslosung", "status": "Bereit nach Runde 3 (Autopilot)", "badge": "Schweizer System"},
                    ],
                },
                {
                    "id": "tabelle",
                    "label": "Rangliste",
                    "zeilen": [
                        {"icon": "trophy", "label": "1. FM Schmidt (3.0 Pkt. · Buchholz 6.5)", "status": "3 Siege · DWZ-Leistung 2240", "badge": "Spitzenreiter"},
                        {"icon": "trophy", "label": "2. Becker (2.5 Pkt. · Buchholz 6.0)", "status": "2 Siege, 1 Remis", "badge": "Verfolger"},
                        {"icon": "trophy", "label": "3. Weber (2.5 Pkt. · Buchholz 5.5)", "status": "2 Siege, 1 Remis", "badge": "Treppchen"},
                    ],
                },
                {
                    "id": "druck",
                    "label": "Druckzettel",
                    "zeilen": [
                        {"icon": "print", "label": "A4-Rundenaushang für Schaukasten", "status": "Paarungen, Bretter und Farbfolge", "badge": "Druckbereit"},
                        {"icon": "card", "label": "Tischkarten mit Spieler-DWZ", "status": "A4-Bogen für alle Bretter", "badge": "Tischkarten"},
                        {"icon": "download", "label": "ChessResults & TRF-Export", "status": "Standardformat für DSB/FIDE-Auswertung", "badge": "Export"},
                    ],
                },
            ],
        },
    },
    {
        "id": "kapitaen",
        "titel": "Mannschaftsführer & Kapitäne",
        "kurztitel": "Mannschaft",
        "icon": "flag",
        "slogan": "Sonntagmorgen entspannt am Brett sitzen – mit geprüfter und vollständiger Aufstellung.",
        "ersparnis": "Keine Regelverstöße bei Ersatzstellung, Spielbericht in 2 Min.",
        "schmerzpunkte": [
            {
                "titel": "Kurzfristige Absagen & Ersatzsuche",
                "problem": "Unübersichtliche WhatsApp-Gruppen, Zusagen gehen unter, am Samstagabend fehlt immer noch Brett 6.",
                "loesung": "Digitale Rückmeldeliste: Spieler melden mit einem Klick Zu- oder Absage. Kapitäne sehen sofort offene Bretter.",
                "detail": "iCal-Kalenderfeed: Alle Spieltermine direkt im Handy-Kalender der Spieler.",
            },
            {
                "titel": "Verstoß gegen Aufstellungsregeln",
                "problem": "Verwechslung der Ranglistenreihenfolge oder unzulässige Ersatzgestellung führt zum kampflosen Punktverlust.",
                "loesung": "Automatische Ranglisten- und Stammspielerprüfung: Das System warnt sofort bei falschen Brettbesetzungen.",
                "detail": "Rechtskonform nach Turnierordnung des Verbandes.",
            },
            {
                "titel": "Handschriftlicher Spielberichtsbogen",
                "problem": "Kritzelige Spielberichtszettel am Spieltag, Ausrechnen der Brettpunkte, Ergebnisdienst spät gefüttert.",
                "loesung": "Druckbarer Spielberichtsbogen mit vorausgefüllter Aufstellung und 1-Klick-Ergebniserfassung mobil am Spielort.",
                "detail": "Ligatabelle auf der Vereinshomepage aktualisiert sich automatisch.",
            },
        ],
        "vorschau": {
            "typ": "aufstellung",
            "fenster_titel": "Spielbetrieb – Bezirksliga Mannschaft I",
            "status_badge": "Aufstellung gültig",
            "metriken": [
                {"label": "Kader-Zusagen", "wert": "8 / 8", "status": "ok"},
                {"label": "DWZ-Schnitt", "wert": "1942", "status": "info"},
                {"label": "Nächster Kampf", "wert": "So, 10:00 Uhr", "status": "ok"},
            ],
            "zeilen": [
                {"icon": "check", "label": "Brett 1–4 (Stammspieler)", "status": "Vollständig bestätigt", "badge": "Geprüft"},
                {"icon": "user", "label": "Brett 5: Ersatz aus Mannschaft II", "status": "Regelkonform nach Rangliste", "badge": "Zulässig"},
                {"icon": "print", "label": "Spielberichtsbogen", "status": "Druckfertig mit Aufstellung beider Teams", "badge": "Drucken"},
            ],
            "aktionen": [
                {"id": "kader", "label": "Aufstellung", "aktiv": True},
                {"id": "gegner", "label": "Gegneranalyse", "aktiv": False},
                {"id": "spielbericht", "label": "Spielbericht", "aktiv": False},
            ],
            "sub_ansichten": [
                {
                    "id": "kader",
                    "label": "Aufstellung",
                    "zeilen": [
                        {"icon": "check", "label": "Brett 1–4 (Stammspieler)", "status": "Vollständig bestätigt", "badge": "Geprüft"},
                        {"icon": "user", "label": "Brett 5: Ersatz aus Mannschaft II", "status": "Regelkonform nach Rangliste", "badge": "Zulässig"},
                        {"icon": "shield", "label": "Stammspielerprüfung", "status": "Verbandskonform ohne Risiko von Punktabzug", "badge": "Validiert"},
                    ],
                },
                {
                    "id": "gegner",
                    "label": "Gegneranalyse",
                    "zeilen": [
                        {"icon": "chart", "label": "SC Nachbarort I (DWZ 1918)", "status": "DWZ-Vorteil +24 für unser Team", "badge": "Favorit"},
                        {"icon": "swords", "label": "Farbverteilung Heimspiel", "status": "Weiß an ungeraden Brettern 1, 3, 5, 7", "badge": "Taktik"},
                        {"icon": "eye", "label": "Letzte Aufstellung des Gegners", "status": "3 Stammspieler fehlten zuletzt", "badge": "Scouting"},
                    ],
                },
                {
                    "id": "spielbericht",
                    "label": "Spielbericht",
                    "zeilen": [
                        {"icon": "print", "label": "A4-Spielberichtsbogen", "status": "Druckfertig mit beidseitiger Aufstellung", "badge": "Drucken"},
                        {"icon": "phone", "label": "Mobile Touch-Eingabe am Brett", "status": "Sofortiges Melden von Brettpunkten", "badge": "Touch-UI"},
                        {"icon": "table", "label": "Automatischer Ligastand", "status": "Homepage-Tabelle synchronisiert sich sofort", "badge": "Live-Sync"},
                    ],
                },
            ],
        },
    },
    {
        "id": "mitglieder",
        "titel": "Mitglieder & Eltern",
        "kurztitel": "Mitglieder",
        "icon": "users",
        "slogan": "Transparenz und Selbstservice für Mitglieder – ohne Zettel und Bürokratie.",
        "ersparnis": "100 % mobile Einsicht, Adressänderungen in 30 Sekunden",
        "schmerzpunkte": [
            {
                "titel": "Fehlende Einsicht & Papierformulare",
                "problem": "Mitglieder wissen nicht, welche Daten gespeichert sind; Bankwechsel müssen umständlich per Brief gemeldet werden.",
                "loesung": "Persönliches Mitglieder-Portal: Adress- und Kontodaten selbst einsehen und Änderungen digital beantragen.",
                "detail": "Der Vorstand prüft und gibt Änderungen mit einem Klick frei – volle Kontrolle.",
            },
            {
                "titel": "Verpasste Spielabende & Turniere",
                "problem": "Termine stehen nur am Aushang im Spiellokal oder in unleserlichen PDF-Rundmails.",
                "loesung": "Abonnierbarer Vereinskalender auf dem Smartphone (iCal) und Online-Voranmeldung für Klubturniere.",
                "detail": "Automatische Terminerinnerungen vor Vereinsturnieren und Mannschaftskämpfen.",
            },
            {
                "titel": "Eltern von Jugendspielern im Dunkeln",
                "problem": "Eltern wissen nicht, wann ihr Kind spielt, wer die Aufsicht hat oder ob der Beitrag eingezogen wurde.",
                "loesung": "Klares Profil für Nachwuchsspieler: Eltern sehen Beiträge, Trainingszeiten, Turnierergebnisse und Termine.",
                "detail": "Datenschutzfreundlich ohne Gruppenchats mit privaten Telefonnummern.",
            },
        ],
        "vorschau": {
            "typ": "mitglied",
            "fenster_titel": "Mein Verein – Mitglieder-Self-Service",
            "status_badge": "Aktiv & bezahlt",
            "metriken": [
                {"label": "Mitgliedsstatus", "wert": "Aktiv (Jugend)", "status": "ok"},
                {"label": "Jahresbeitrag 2026", "wert": "40,00 € (Bezahlt)", "status": "ok"},
                {"label": "Nächstes Turnier", "wert": "Jugend-Open (Angemeldet)", "status": "info"},
            ],
            "zeilen": [
                {"icon": "user", "label": "Stammdaten: Neue Adresse gemeldet", "status": "Freigabe durch Vorstand erfolgt", "badge": "Aktuell"},
                {"icon": "calendar", "label": "Kalender-Abo (iCal)", "status": "Mit Smartphone-Kalender synchronisiert", "badge": "Verbunden"},
                {"icon": "trophy", "label": "Turnieranmeldung Vereinsblitz", "status": "Bestätigt – Startplatz 12", "badge": "Angemeldet"},
            ],
            "aktionen": [
                {"id": "profil", "label": "Mein Profil", "aktiv": True},
                {"id": "beitrag", "label": "Beitragskonto", "aktiv": False},
                {"id": "kalender", "label": "Termine", "aktiv": False},
            ],
            "sub_ansichten": [
                {
                    "id": "profil",
                    "label": "Mein Profil",
                    "zeilen": [
                        {"icon": "user", "label": "Stammdaten: Neue Adresse gemeldet", "status": "Freigabe durch Vorstand erfolgt", "badge": "Aktuell"},
                        {"icon": "lock", "label": "SEPA-Mandat & Bankverbindung", "status": "IBAN DE89...4321 verschlüsselt hinterlegt", "badge": "Aktiv"},
                        {"icon": "shield", "label": "Art. 15 DSGVO Datenauskunft", "status": "Jederzeit selbst als PDF herunterladbar", "badge": "Transparent"},
                    ],
                },
                {
                    "id": "beitrag",
                    "label": "Beitragskonto",
                    "zeilen": [
                        {"icon": "wallet", "label": "Jahresbeitrag 2026: 40,00 €", "status": "Vollständig bezahlt per SEPA", "badge": "Bezahlt"},
                        {"icon": "download", "label": "Beitragsquittung herunterladen", "status": "Offizieller Beleg für Krankenkasse/Finanzamt", "badge": "Quittung"},
                        {"icon": "check", "label": "0,00 € offene Posten", "status": "Keine ausstehenden Beiträge vorhanden", "badge": "Ausgeglichen"},
                    ],
                },
                {
                    "id": "kalender",
                    "label": "Termine",
                    "zeilen": [
                        {"icon": "calendar", "label": "Persönlicher iCal-Kalenderfeed", "status": "Automatisch synchron auf dem Smartphone", "badge": "Abonniert"},
                        {"icon": "trophy", "label": "Vereinsblitzmeisterschaft", "status": "Voranmeldung mit 1 Klick erledigt", "badge": "Angemeldet"},
                        {"icon": "clock", "label": "Jugendtraining freitags 17:30 Uhr", "status": "Betreuung durch lizenzierte Vereinstrainer", "badge": "Termin"},
                    ],
                },
            ],
        },
    },
]

