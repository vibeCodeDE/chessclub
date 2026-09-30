"""Inhalte der Produkt-Landingpage (/produkt/).

Alles, was sich für den Verkauf ändert (Preise, Funktionsliste, FAQ) und alle
Abschnittstexte (Hero, Kennzahlen, Nutzen, Rollen, Demo-Vorschau) stehen hier an
einer Stelle – das Template enthält nur Darstellung (PRD S10.2).

ENTWURF: Die Preise sind Platzhalter und vor dem Livegang festzulegen.
"""

HERO = {
    "eyebrow": "Für Schachvereine in Deutschland",
    "titel": "Vereinsverwaltung, die Ihr Vorstand gerne benutzt.",
    "text": (
        "Mitglieder, Beiträge, Turniere, Mannschaften und Kassenbuch in einer Software. "
        "Ohne Excel-Listen, ohne Zettelwirtschaft und mit Datenhaltung in Deutschland."
    ),
    "checks": ["Monatlich kündbar", "Einrichtung inklusive", "DSGVO-konform"],
}

KENNZAHLEN = [
    ("6 Bereiche", "in einer Anwendung"),
    ("100 % Deutschland", "Hosting und Datenhaltung"),
    ("0 Tracker", "keine externen Dienste"),
    ("Mobil", "auch als App installierbar"),
]

PROBLEM = {
    "titel": "Vereinsarbeit ist Ehrenamt. Sie sollte sich nicht nach Buchhaltung anfühlen.",
    "text": (
        "In vielen Vereinen liegen Mitgliederliste, Beitragsübersicht und Turnierergebnisse "
        "in drei verschiedenen Dateien, manchmal bei drei verschiedenen Personen. Jeder "
        "Wechsel im Vorstand wird dann zum Risiko."
    ),
    "vorher": [
        "Adressen in Excel, Zahlungen im Kopf der Kassenwartin",
        "Turnierergebnisse per Hand in Tabellen getippt und per Mail verschickt",
        "Datenschutz-Anfragen, bei denen niemand weiß, wo welche Daten liegen",
    ],
    "mit_uns": "Eine Software, klare Rollen, alles nachvollziehbar protokolliert",
}

ROLLEN = [
    (
        "Vorstand",
        "Volle Übersicht über Mitglieder, Beiträge, Kasse und Turniere. Änderungswünsche von Mitgliedern prüfen und freigeben.",
    ),
    (
        "Mannschaftsführer",
        "Aufstellungen melden, Ergebnisse erfassen und Termine im Blick behalten, ohne Zugriff auf Finanzdaten.",
    ),
    (
        "Mitglieder",
        "Eigenes Profil, Beitragskonto und Turnieranmeldung. Änderungen der Stammdaten lassen sich direkt beantragen.",
    ),
]

# Vorschau-Panel im Hero: ein rein gestalterisches Mock (keine echten Zahlen).
DEMO = {
    "label": "Vorschau",
    "titel": "Dashboard",
    "kacheln": [
        ("Aktive Mitglieder", "87"),
        ("Offene Beiträge", "1.240 €"),
        ("Turnieranmeldungen", "24"),
    ],
    "zeilen": [
        ("Vereinsmeisterschaft", "Sa, 18.10. · Schweizer System"),
        ("SC Musterstadt I gegen SV Nachbarort", "So, 26.10. · 10:00 Uhr"),
        ("3 Mahnungen vorbereitet", "Zur Prüfung durch den Kassenwart"),
    ],
}

PREIS_HINWEIS = "Die Preise sind Platzhalter und werden vor dem Livegang festgelegt."

# Überschriften und Einleitungen der Abschnitte (Kicker = Zeile über der Überschrift).
ABSCHNITTE = {
    "nutzen_kicker": "Warum",
    "funktionen_kicker": "Funktionen",
    "funktionen_titel": "Alles, was ein Schachverein braucht",
    "funktionen_aside": "Gebaut für Vereine bis etwa 200 Mitglieder. Jede Rolle sieht nur das, was sie braucht.",
    "rollen_kicker": "Für alle im Verein",
    "rollen_titel": "Jeder bekommt seinen Bereich",
    "datenschutz_kicker": "Datenschutz",
    "datenschutz_titel": "Mitgliederdaten gehören in gute Hände",
    "datenschutz_text": "Vereine verarbeiten personenbezogene Daten, auch von Kindern und Jugendlichen. Die Software ist deshalb von Anfang an auf die DSGVO ausgelegt.",
    "ablauf_kicker": "So starten Sie",
    "ablauf_titel": "In drei Schritten einsatzbereit",
    "preise_kicker": "Preise",
    "preise_titel": "Einfach und fair für Vereinskassen",
    "preise_aside": "Monatliche Zahlung, keine Mindestlaufzeit. Preise zzgl. gesetzlicher Umsatzsteuer.",
    "faq_kicker": "Häufige Fragen",
    "faq_titel": "Gut zu wissen",
    "faq_aside": "Ihre Frage ist nicht dabei? Schreiben Sie uns einfach – wir antworten in der Regel innerhalb eines Werktags.",
}

CTA = {
    "titel": "Bereit, die Vereinsverwaltung zu vereinfachen?",
    "text": "Wir zeigen Ihnen die Software mit Beispieldaten, kostenlos und unverbindlich.",
}

PREISSTUFEN = [
    {
        "name": "Start",
        "fuer": "Kleine Vereine bis 50 Mitglieder",
        "preis": "29",
        "hervorgehoben": False,
        "punkte": [
            "Mitglieder, Beiträge, Kassenbuch",
            "Turniere und öffentliche Vereinsseite",
            "Eigene Instanz, Hosting in Deutschland",
            "Tägliche Backups",
            "Support per E-Mail",
        ],
    },
    {
        "name": "Verein",
        "fuer": "Bis 120 Mitglieder, mit Spielbetrieb",
        "preis": "49",
        "hervorgehoben": True,
        "punkte": [
            "Alles aus „Start“",
            "Mannschaften, Aufstellungen, Ligatabellen",
            "Rundbriefe per E-Mail an Gruppen",
            "Zwei-Faktor-Anmeldung für den Vorstand",
            "Einrichtung und Datenübernahme inklusive",
        ],
    },
    {
        "name": "Verband",
        "fuer": "Große Vereine ab 120 Mitglieder",
        "preis": "89",
        "hervorgehoben": False,
        "punkte": [
            "Alles aus „Verein“",
            "Bis zu 300 Mitglieder",
            "Eigene Domain (portal.ihrverein.de)",
            "Persönliche Einweisung für den Vorstand",
            "Bevorzugter Support",
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
    "Datenhaltung ausschließlich in Deutschland, keine Tracker, keine externen CDNs",
    "Datenauskunft pro Mitglied als PDF und JSON auf Knopfdruck",
    "Audit-Protokoll für Zugriffe auf Personendaten",
    "Ausgetretene Mitglieder werden nach Fristablauf anonymisiert",
    "Zwei-Faktor-Anmeldung für den Vorstand",
    "Verzeichnis der Verarbeitungstätigkeiten als CSV",
]

SCHRITTE = [
    ("Kennenlernen", "Sie sehen die Software in einer Demo mit Beispieldaten. Kostenlos und unverbindlich, etwa 30 Minuten."),
    ("Einrichten", "Wir legen Ihre eigene Instanz an, setzen Beitragssätze und Zugänge auf und übernehmen Ihre Mitgliederliste."),
    ("Loslegen", "Der Vorstand arbeitet von Tag eins im System. Die Mitglieder bekommen ihren Zugang per E-Mail."),
]

FAQ = [
    (
        "Wo liegen unsere Daten?",
        "Jeder Verein bekommt eine eigene Instanz mit eigener Datenbank bei einem Hoster in Deutschland. Die Daten verschiedener Vereine werden nicht gemischt.",
    ),
    (
        "Brauchen wir einen Auftragsverarbeitungsvertrag?",
        "Ja, und wir stellen ihn bereit. Er gehört zu jedem Vertrag dazu.",
    ),
    (
        "Wie kommen unsere vorhandenen Daten hinein?",
        "Beim Einrichten übernehmen wir Ihre Mitgliederliste, zum Beispiel aus Excel oder CSV. Das ist in den Tarifen „Verein“ und „Verband“ enthalten.",
    ),
    (
        "Zieht die Software die Beiträge automatisch ein?",
        "Nein. Sie verwaltet Mandate, Forderungen und Zahlungsstatus. Der Lastschrifteinzug läuft weiter über die Bank des Vereins. So behalten Sie die volle Kontrolle.",
    ),
    (
        "Können wir kündigen?",
        "Ja. Die Laufzeit ist monatlich, und Ihre Daten können Sie jederzeit als CSV exportieren.",
    ),
    (
        "Funktioniert das auf dem Smartphone?",
        "Ja. Die Oberfläche ist für kleine Bildschirme gebaut und lässt sich wie eine App auf dem Homescreen installieren.",
    ),
]
