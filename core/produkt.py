"""Inhalte der Produkt-Landingpage (/produkt/).

Alles, was sich für den Verkauf ändert (Preise, Funktionsliste, FAQ), steht hier
an einer Stelle – das Template enthält nur Darstellung.

ENTWURF: Die Preise sind Platzhalter und vor dem Livegang festzulegen.
"""

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
