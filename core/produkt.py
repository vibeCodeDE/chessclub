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
            "Eigene Instanz, Hosting in Deutschland, tägliche Backups",
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
    "Datenhaltung ausschließlich in Deutschland, keine Tracker, keine externen CDNs",
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
        "Jeder Verein bekommt eine eigene Instanz mit eigener Datenbank bei einem Hoster in Deutschland. Die "
        "Daten verschiedener Vereine werden nicht gemischt.",
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
