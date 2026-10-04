"""Realistische Demo-Daten für Vorführung, Abnahme und Entwicklung.

Aufruf:
    python manage.py seed_demo            # legt Daten an (idempotent)
    python manage.py seed_demo --reset    # löscht Demo-Daten und legt sie neu an

Alle Namen, Adressen und Kontakte sind erfunden (Beispielort „Musterstadt“).
Passwort aller Demo-Konten: ``schach2026``
"""

import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cashbook.models import CashEntry
from comms.models import MailLog, NewsPost
from core.models import AuditLog
from dues.models import (
    DunningLetter,
    FeeAmount,
    FeeCategory,
    MembershipFee,
    Payment,
    SepaMandate,
)
from members.models import ChangeRequest, Member
from teams.models import LeagueMatch, LineupEntry, Team
from tournaments.models import Pairing, Participant, Tournament, TournamentRound
from tournaments.pairing import generate_round

PASSWORT = "schach2026"

VORNAMEN = [
    "Anna", "Andreas", "Bettina", "Bernd", "Carola", "Christian", "Daniel", "Diana",
    "Elena", "Emil", "Felix", "Franziska", "Greta", "Günther", "Hanna", "Heiko",
    "Iris", "Jan", "Jasmin", "Jonas", "Katrin", "Klaus", "Lara", "Lukas",
    "Marlene", "Martin", "Nadine", "Nico", "Oliver", "Petra", "Rainer", "Rosa",
    "Sabine", "Samuel", "Tanja", "Thomas", "Ulrike", "Uwe", "Verena", "Volker",
    "Wiebke", "Wolfgang", "Yvonne", "Zoe", "Jonah", "Leonie", "Moritz", "Nele",
]
NACHNAMEN = [
    "Albrecht", "Bauer", "Becker", "Bergmann", "Böhm", "Brandt", "Fischer", "Frank",
    "Graf", "Groß", "Hartmann", "Heinrich", "Hoffmann", "Keller", "Klein", "Köhler",
    "Krause", "Krüger", "Lang", "Lehmann", "Maier", "Meier", "Meyer", "Müller",
    "Neumann", "Peters", "Richter", "Roth", "Schäfer", "Schmid", "Schmidt", "Schneider",
    "Schröder", "Schulz", "Schwarz", "Seidel", "Simon", "Stein", "Thomas", "Vogel",
    "Wagner", "Weber", "Werner", "Winter", "Wolf", "Zimmer",
]
STRASSEN = [
    "Lindenweg", "Bahnhofstraße", "Am Schlosspark", "Rosenstraße", "Gartenweg",
    "Kirchgasse", "Talstraße", "Ringstraße", "Ahornweg", "Marktplatz",
]
ORTE = [("37073", "Musterstadt"), ("37075", "Musterstadt"), ("37081", "Göttingen-Nord"), ("37154", "Nordheim")]

JAHR = date.today().year
VORJAHR = JAHR - 1

KATEGORIEN = [
    ("Erwachsene", "Vollmitglied ab 19 Jahren", "90.00"),
    ("Jugendliche", "Mitglied bis 18 Jahre", "45.00"),
    ("Familie", "Eltern und Kinder im Haushalt", "130.00"),
    ("Ermäßigt", "Schüler:innen, Studierende, Geringverdienende", "60.00"),
    ("Fördermitglied", "Passive Förderung ohne Spielbetrieb", "30.00"),
]

NEWS = [
    ("Vereinsmeisterschaft: spannendes Finale in der letzten Runde",
     "Vereinsleben",
     "Am vergangenen Wochenende wurde unsere Vereinsmeisterschaft entschieden. Nach sieben Runden "
     "Schweizer System lagen die ersten drei Bretter nur einen halben Punkt auseinander.\n\n"
     "Am Ende setzte sich unsere Nummer zwei im Endspiel mit einem Bauernvorteil durch. Herzlichen "
     "Glückwunsch! Die vollständige Tabelle hängt im Vereinsheim aus und ist in der Vereinsverwaltung "
     "einsehbar.\n\nEin Dank an alle Helfenden am Brett, in der Küche und beim Aufbau."),
    ("Neue Trainingszeiten ab dem nächsten Monat",
     "Jugend",
     "Damit unsere Jugendlichen früher zu Hause sind, beginnt das Jugendtraining künftig bereits um "
     "17:30 Uhr. Das Erwachsenentraining bleibt bei 19:00 Uhr.\n\n"
     "Eltern können die Kinder gerne zum Schnuppern vorbeibringen – die ersten drei Einheiten sind "
     "kostenlos. Bretter und Figuren stellen wir."),
    ("Mannschaften starten in die neue Saison",
     "Spielbetrieb",
     "Unsere erste Mannschaft geht mit einem deutlich verjüngten Kader in die Bezirksliga. Die zweite "
     "Mannschaft spielt in der Kreisklasse, die Jugendmannschaft in der Kreisliga Jugend.\n\n"
     "Alle Begegnungen findet ihr im Spielplan. Fahrgemeinschaften zu Auswärtsspielen werden wieder "
     "über die Mannschaftsführer organisiert."),
    ("Rapidturnier am Vereinsabend – Anmeldung läuft",
     "Turnier",
     "Unser offenes Rapidturnier findet wieder an einem Donnerstagabend statt. Gespielt werden fünf "
     "Runden mit 15 Minuten Bedenkzeit.\n\n"
     "Die Anmeldung ist online über die Turnierseite möglich – Gäste sind ausdrücklich willkommen. "
     "Das Startgeld beträgt 5 Euro, Jugendliche spielen kostenlos."),
    ("Einladung zur Mitgliederversammlung",
     "Verein",
     "Liebe Mitglieder,\n\nhiermit laden wir herzlich zur ordentlichen Mitgliederversammlung ins "
     "Vereinsheim ein. Auf der Tagesordnung stehen der Kassenbericht, die Entlastung des Vorstands, "
     "die Beitragsordnung sowie die Planung des Jubiläums.\n\n"
     "Anträge zur Tagesordnung bitte zwei Wochen vorher schriftlich bei der Vorstandschaft einreichen."),
    ("Weihnachtsblitzturnier mit Glühwein und Kuchen",
     "Turnier",
     "Traditionell beenden wir das Jahr mit unserem Blitzturnier in gemütlicher Runde. Gespielt wird "
     "mit 5 Minuten Bedenkzeit, gesetzt wird auf weihnachtliche Dekoration am Brett.\n\n"
     "Für Kinder gibt es eine eigene Wertungsgruppe. Anschließend gibt es Kaffee, Kuchen und "
     "Glühwein im Vereinsheim."),
    ("Spielbericht: knapper Auswärtssieg für die Zweite",
     "Spielbetrieb",
     "Mit 4,5 : 3,5 setzte sich unsere zweite Mannschaft beim Tabellennachbarn durch. Den "
     "entscheidenden halben Punkt holte unser Nachwuchsspieler am achten Brett.\n\n"
     "Der Mannschaftsführer lobte die ruhige Spielweise in der Eröffnung und das gute Zusammenspiel "
     "im Mannschaftsraum."),
    ("Turnierkalender für die neue Saison steht (Entwurf)",
     "Turnier",
     "Der Turnierkalender für die kommende Saison ist fast fertig. Termine für Vereinsmeisterschaft, "
     "Rapidturnier und Jugendpokal stehen; die Ausschreibungen folgen.",
     False),
    ("Neue Vereinsbretter sind da (Entwurf)",
     "Material",
     "Sechs neue Turnierbretter mit Figuren sind eingetroffen und werden beim nächsten Vereinsabend "
     "ausgepackt. Die alten Bretter wandern in die Jugendkiste.",
     False),
]


class Command(BaseCommand):
    help = "Legt realistische Demo-Daten für die Vereinsverwaltung an."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Vorhandene Daten vorher löschen.")

    def handle(self, *args, **options):
        random.seed(42)
        if options["reset"]:
            self._reset()
        elif Member.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    "Es sind bereits Mitglieder vorhanden – es wird nichts angelegt. "
                    "Mit --reset werden die Demo-Daten neu erzeugt."
                )
            )
            return

        with transaction.atomic():
            self._gruppen_und_konten()
            kategorien = self._kategorien()
            mitglieder = self._mitglieder(kategorien)
            self._mandate(mitglieder)
            self._beitraege(mitglieder)
            teams = self._mannschaften(mitglieder)
            self._ligaspiele(teams, mitglieder)
            self._turniere(mitglieder)
            self._news()
            self._kasse()
            self._aenderungswuensche(mitglieder)
            self._mail_protokoll()
            AuditLog.objects.create(
                aktion="Demo-Daten geladen",
                text="seed_demo: Beispieldaten für Vorführung und Tests erzeugt.",
            )

        self.stdout.write(self.style.SUCCESS("Demo-Daten erfolgreich geladen."))
        self.stdout.write(
            "Logins: vorstand / kassenwart / kapitaen / mitglied – Passwort jeweils: schach2026"
        )

    # ------------------------------------------------------------------ Reset
    def _reset(self):
        Pairing.objects.all().delete()
        TournamentRound.objects.all().delete()
        Participant.objects.all().delete()
        Tournament.objects.all().delete()
        LineupEntry.objects.all().delete()
        LeagueMatch.objects.all().delete()
        Team.objects.all().delete()
        DunningLetter.objects.all().delete()
        Payment.objects.all().delete()
        MembershipFee.objects.all().delete()
        SepaMandate.objects.all().delete()
        FeeCategory.objects.all().delete()
        MailLog.objects.all().delete()
        NewsPost.objects.all().delete()
        CashEntry.objects.all().delete()
        ChangeRequest.objects.all().delete()
        Member.objects.all().delete()
        AuditLog.objects.all().delete()
        User.objects.filter(username__in=["vorstand", "kassenwart", "kapitaen", "mitglied"]).delete()
        self.stdout.write("Bestehende Daten gelöscht.")

    # ---------------------------------------------------------------- Konten
    def _gruppen_und_konten(self):
        for name in ("admin", "kapitaen", "mitglied"):
            Group.objects.get_or_create(name=name)

        for username, gruppe, vorname, nachname, email, staff in [
            ("vorstand", "admin", "Andreas", "Bauer", "vorstand@koenigsspringer-musterstadt.de", True),
            ("kassenwart", "admin", "Petra", "Lehmann", "kasse@koenigsspringer-musterstadt.de", True),
            ("kapitaen", "kapitaen", "Michael", "Schmidt", "kapitaen@koenigsspringer-musterstadt.de", False),
            ("mitglied", "mitglied", "Lena", "Fischer", "lena.fischer@example.org", False),
        ]:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": vorname,
                    "last_name": nachname,
                    "email": email,
                    "is_staff": staff,
                    "is_superuser": staff,
                },
            )
            user.set_password(PASSWORT)
            user.save()
            user.groups.set([Group.objects.get(name=gruppe)])

    # ------------------------------------------------------------ Kategorien
    def _kategorien(self):
        kategorien = {}
        for name, beschreibung, betrag in KATEGORIEN:
            kategorie, _ = FeeCategory.objects.get_or_create(
                name=name, defaults={"beschreibung": beschreibung}
            )
            for jahr in (2025, 2026, 2027):
                FeeAmount.objects.get_or_create(
                    kategorie=kategorie, jahr=jahr, defaults={"betrag": Decimal(betrag)}
                )
            kategorien[name] = kategorie
        return kategorien

    # -------------------------------------------------------------- Mitglieder
    def _mitglieder(self, kategorien):
        konto_mitglieder = {
            "vorstand": ("Andreas", "Bauer"),
            "kassenwart": ("Petra", "Lehmann"),
            "kapitaen": ("Michael", "Schmidt"),
            "mitglied": ("Lena", "Fischer"),
        }
        # Konten zuerst, damit sie feste Mitglieder bekommen.
        mitglieder = []
        for username, (vorname, nachname) in konto_mitglieder.items():
            mitglieder.append(
                self._mitglied_anlegen(
                    vorname, nachname, kategorien["Erwachsene"], user=User.objects.get(username=username)
                )
            )

        weitere = []
        for index in range(44):
            vorname = VORNAMEN[index % len(VORNAMEN)]
            nachname = NACHNAMEN[(index * 7) % len(NACHNAMEN)]
            if index < 14:
                kategorie = kategorien["Jugendliche"]
            elif index % 9 == 0:
                kategorie = kategorien["Familie"]
            elif index % 7 == 0:
                kategorie = kategorien["Ermäßigt"]
            elif index % 11 == 0:
                kategorie = kategorien["Fördermitglied"]
            else:
                kategorie = kategorien["Erwachsene"]

            if index >= 40:  # drei Ausgetretene
                weitere.append(
                    self._mitglied_anlegen(
                        vorname, nachname, kategorie,
                        status=Member.Status.AUSGETRETEN,
                        austritt=date.today() - timedelta(days=420 + index),
                        basis=index,
                    )
                )
            elif index >= 36:  # passive Mitglieder
                weitere.append(
                    self._mitglied_anlegen(vorname, nachname, kategorie, status=Member.Status.PASSIV, basis=index)
                )
            else:
                weitere.append(self._mitglied_anlegen(vorname, nachname, kategorie, basis=index))

        mitglieder.extend(weitere)
        return mitglieder

    def _mitglied_anlegen(self, vorname, nachname, kategorie, *, status=None, austritt=None, basis=None, user=None):
        basis = random.randint(0, 400) if basis is None else basis
        strasse = f"{STRASSEN[basis % len(STRASSEN)]} {random.randint(1, 120)}"
        plz, ort = ORTE[basis % len(ORTE)]
        geburtsjahr = 2016 - (basis % 45)
        eintritt = date.today() - timedelta(days=random.randint(200, 5200))
        email = f"{vorname.lower().replace('ä', 'ae')}.{nachname.lower().replace('ä', 'ae')}@{'example.org'}"
        if basis % 5 == 0:
            email = ""  # ohne Adresse – zeigt Leerzustände und Opt-in-Logik
        mitglied = Member.objects.create(
            user=user,
            vorname=vorname,
            nachname=nachname,
            geburtsdatum=date(geburtsjahr, (basis % 12) + 1, (basis % 27) + 1),
            strasse=strasse,
            plz=plz,
            ort=ort,
            email=email,
            telefon=f"0551 {random.randint(1000000, 9999999)}" if basis % 4 else "",
            eintrittsdatum=eintritt,
            status=status or Member.Status.AKTIV,
            austrittsdatum=austritt,
            beitragskategorie=kategorie,
            email_opt_in=bool(email) and basis % 6 != 0,
        )
        return mitglied

    # --------------------------------------------------------------- Mandate
    def _mandate(self, mitglieder):
        aktiv = [m for m in mitglieder if m.status == Member.Status.AKTIV]
        for index, mitglied in enumerate(aktiv):
            if index % 3 == 2:
                continue  # bewusst Lücken: „Ohne Mandat“-Liste bleibt realistisch
            SepaMandate.objects.update_or_create(
                member=mitglied,
                defaults={
                    "referenz": f"SCKS-{VORJAHR}-{index + 1:03d}",
                    "iban": f"DE{20 + index % 70:02d}370400440532{index:04d}",
                    "kontoinhaber": f"{mitglied.vorname} {mitglied.nachname}",
                    "erteilt_am": mitglied.eintrittsdatum,
                    "status": SepaMandate.Status.AKTIV,
                },
            )

    # ------------------------------------------------------------- Beiträge
    def _beitraege(self, mitglieder):
        if MembershipFee.objects.exists():
            self.stdout.write("Beitragsposten vorhanden – überspringe Beitragsläufe.")
            return
        vorstand = User.objects.get(username="kassenwart")
        zahlbar = [m for m in mitglieder if m.status != Member.Status.AUSGETRETEN and m.beitragskategorie]

        for jahr, quote in ((VORJAHR, 0.94), (JAHR, 0.62)):
            for index, mitglied in enumerate(zahlbar):
                betrag = mitglied.beitragskategorie.betrag
                faellig = date(jahr, 1, 31)
                fee = MembershipFee.objects.create(
                    member=mitglied,
                    jahr=jahr,
                    kategorie_name=mitglied.beitragskategorie.name,
                    betrag=betrag,
                    faellig_am=faellig,
                )
                wuerfel = random.random()
                if jahr == VORJAHR:
                    if wuerfel <= quote or index % 17 == 0:
                        self._zahlung(fee, betrag, jahr, "sepa" if index % 3 == 2 else "ueberweisung", vorstand)
                    elif wuerfel <= quote + 0.04:
                        self._zahlung(fee, (betrag / 2).quantize(Decimal("0.01")), jahr, "bar", vorstand)
                    else:
                        self._mahnung(fee, 1, vorstand)
                        self._mahnung(fee, 2, vorstand)
                else:
                    if wuerfel <= 0.5:
                        self._zahlung(fee, betrag, jahr, "sepa", vorstand)
                    elif wuerfel <= quote:
                        self._zahlung(fee, (betrag * Decimal("0.5")).quantize(Decimal("0.01")), jahr, "ueberweisung", vorstand)
                    elif wuerfel <= 0.78:
                        self._mahnung(fee, 1, vorstand)
                    elif wuerfel <= 0.86:
                        self._mahnung(fee, 1, vorstand)
                        self._mahnung(fee, 2, vorstand)

    def _zahlung(self, fee, betrag, jahr, art, benutzer):
        Payment.objects.create(
            fee=fee,
            betrag=betrag,
            datum=date(jahr, random.randint(1, 8), random.randint(1, 28)),
            art=art,
            notiz="Demo-Zahlung",
            erfasst_von=benutzer,
        )
        fee.status_aktualisieren()

    def _mahnung(self, fee, stufe, benutzer):
        DunningLetter.objects.create(
            fee=fee,
            stufe=stufe,
            datum=date(fee.jahr, 3 if stufe == 1 else 5, 15),
            gebuehr=Decimal("5.00") if stufe == 2 else Decimal("0.00"),
            notiz="Zahlungserinnerung" if stufe == 1 else "Letzte Mahnung vor Vollstreckung",
            erstellt_von=benutzer,
        )
        fee.mahnstufe = stufe
        fee.letzte_mahnung_am = date(fee.jahr, 3 if stufe == 1 else 5, 15)
        fee.save(update_fields=["mahnstufe", "letzte_mahnung_am"])

    # ----------------------------------------------------------- Mannschaften
    def _mannschaften(self, mitglieder):
        kapitaen = Member.objects.filter(user__username="kapitaen").first()
        teams = [
            Team.objects.create(
                name="1. Mannschaft", liga="Bezirksliga", altersklasse=Team.Altersklasse.ERWACHSENE,
                brettanzahl=8, kapitaen=kapitaen, aktiv=True,
            ),
            Team.objects.create(
                name="2. Mannschaft", liga="Kreisklasse", altersklasse=Team.Altersklasse.ERWACHSENE,
                brettanzahl=6, aktiv=True,
            ),
            Team.objects.create(
                name="Jugend U16", liga="Kreisliga Jugend", altersklasse=Team.Altersklasse.JUGEND,
                brettanzahl=4, aktiv=True,
            ),
            Team.objects.create(
                name="Senioren", liga="Seniorenrunde", altersklasse=Team.Altersklasse.SENIOREN,
                brettanzahl=4, aktiv=False,
            ),
        ]
        return teams

    def _ligaspiele(self, teams, mitglieder):
        spieler = [m for m in mitglieder if m.status == Member.Status.AKTIV]
        gegner = [
            "SV Eichenfeld", "Schachfreunde Nordheim", "TSV Musterstadt", "SK Königsruhe",
            "SC Turmbau", "Brettbrecher Göttingen", "SC Rochade Süd", "VfL Springerbach",
        ]
        for team_index, team in enumerate(teams[:3]):
            kader = spieler[team_index * 8 : team_index * 8 + team.brettanzahl]
            for spiel_index in range(8):
                vergangen = spiel_index < 4
                datum = date.today() + timedelta(days=(spiel_index - 3) * 14)
                match = LeagueMatch.objects.create(
                    team=team,
                    datum=datum,
                    uhrzeit=time(14, 0) if spiel_index % 2 == 0 else time(18, 30),
                    gegner=gegner[(team_index + spiel_index) % len(gegner)],
                    heimspiel=spiel_index % 2 == 0,
                    ort="" if spiel_index % 2 == 0 else "Vereinsheim Auswärts",
                    runde=f"{spiel_index + 1}. Runde" if team_index == 0 else str(spiel_index + 1),
                    brettanzahl=team.brettanzahl,
                )
                if vergangen:
                    for brett in range(1, team.brettanzahl + 1):
                        LineupEntry.objects.create(
                            match=match,
                            brett=brett,
                            member=kader[(brett - 1) % len(kader)] if kader else None,
                            gegner_name=f"Gegner {brett}",
                            ergebnis=random.choices(
                                ["1", "0.5", "0", ""], weights=[45, 20, 30, 5]
                            )[0],
                        )
                    match.status = LeagueMatch.Status.GESPIELT
                elif spiel_index == 4:
                    for brett in range(1, team.brettanzahl + 1):
                        LineupEntry.objects.create(
                            match=match,
                            brett=brett,
                            member=kader[(brett - 1) % len(kader)] if kader else None,
                        )
                    match.status = LeagueMatch.Status.AUFGESTELLT
                match.save()
                if match.status == LeagueMatch.Status.GESPIELT:
                    match.status_aktualisieren()

    # --------------------------------------------------------------- Turniere
    def _turniere(self, mitglieder):
        vorstand = User.objects.get(username="vorstand")
        vereinsmeisterschaft = Tournament.objects.create(
            name=f"Vereinsmeisterschaft {VORJAHR}",
            datum=date(VORJAHR, 11, 8),
            anmeldeschluss=date(VORJAHR, 10, 25),
            ort="Vereinsheim Musterstadt",
            format=Tournament.Format.SCHWEIZER,
            runden_anzahl=5,
            startgeld=Decimal("7.50"),
            beschreibung=(
                "Offene Vereinsmeisterschaft im Schweizer System über fünf Runden. "
                "Gespielt werden 90 Minuten für 40 Züge plus 30 Minuten Restbedenkzeit."
            ),
            oeffentlich=True,
            status=Tournament.Status.BEENDET,
        )
        spieler = [m for m in mitglieder if m.status == Member.Status.AKTIV][:12]
        for index, mitglied in enumerate(spieler):
            Participant.objects.create(
                tournament=vereinsmeisterschaft,
                member=mitglied,
                name=f"{mitglied.vorname} {mitglied.nachname}",
                verein="SC Königsspringer",
                twz=2050 - index * 45,
                geburtsjahr=mitglied.geburtsdatum.year if mitglied.geburtsdatum else None,
                email=mitglied.email,
                startgeld_bezahlt=index % 5 != 0,
            )
        for _ in range(5):
            runde, fehler = generate_round(vereinsmeisterschaft)
            if fehler or runde is None:
                break
            for paarung in runde.paarungen.all():
                if paarung.ergebnis == Pairing.Ergebnis.BYE:
                    continue
                paarung.ergebnis = random.choice(
                    [Pairing.Ergebnis.WEISS, Pairing.Ergebnis.SCHWARZ, Pairing.Ergebnis.REMIS]
                )
                paarung.save(update_fields=["ergebnis"])
            vereinsmeisterschaft.status = Tournament.Status.LAUFEND
            vereinsmeisterschaft.save(update_fields=["status"])
        vereinsmeisterschaft.status = Tournament.Status.BEENDET
        vereinsmeisterschaft.save(update_fields=["status"])

        rapid = Tournament.objects.create(
            name="Rapidturnier am Vereinsabend",
            datum=date.today() + timedelta(days=21),
            anmeldeschluss=date.today() + timedelta(days=19),
            ort="Vereinsheim Musterstadt",
            format=Tournament.Format.RAPID,
            runden_anzahl=5,
            startgeld=Decimal("5.00"),
            beschreibung=(
                "Offenes Rapidturnier über fünf Runden, 15 Minuten Bedenkzeit pro Partie und Spieler:in. "
                "Gäste sind herzlich willkommen, Jugendliche spielen ohne Startgeld."
            ),
            oeffentlich=True,
            status=Tournament.Status.ANMELDUNG,
        )
        for index, mitglied in enumerate(spieler[:6]):
            Participant.objects.create(
                tournament=rapid,
                member=mitglied,
                name=f"{mitglied.vorname} {mitglied.nachname}",
                verein="SC Königsspringer",
                twz=1980 - index * 40,
                startgeld_bezahlt=index < 3,
            )
        for index, gast in enumerate(["Gastanmeldung Eichenfeld", "Jugendspieler Nordheim"]):
            Participant.objects.create(
                tournament=rapid,
                name=gast,
                verein="SV Eichenfeld" if index == 0 else "SF Nordheim",
                twz=1650 - index * 50,
                email="gaeste@example.org",
                notiz="Anmeldung über die öffentliche Turnierseite",
            )

        jugend = Tournament.objects.create(
            name=f"Jugendpokal {JAHR + 1}",
            datum=date(JAHR + 1, 3, 14),
            anmeldeschluss=date(JAHR + 1, 2, 28),
            ort="Vereinsheim Musterstadt",
            format=Tournament.Format.RUNDEN,
            runden_anzahl=7,
            startgeld=Decimal("0.00"),
            beschreibung="Jugendpokal mit sieben Runden im Rundensystem. Ausschreibung folgt.",
            oeffentlich=False,
            status=Tournament.Status.ENTWURF,
        )
        NewsPost.objects.create(
            titel=f"Vereinsmeisterschaft {VORJAHR}: alle Partien gespielt",
            text=(
                "Die Vereinsmeisterschaft ist beendet. Die vollständige Tabelle und alle Paarungen "
                "finden sich in der Turnierverwaltung; der Wanderpokal wird bei der "
                "Mitgliederversammlung übergeben."
            ),
            kategorie="Turnier",
            autor=vorstand,
            veroeffentlicht=True,
            veroeffentlicht_am=timezone.now() - timedelta(days=120),
        )
        self.vereinsmeister = vereinsmeisterschaft
        self.jugendpokal = jugend

    # ------------------------------------------------------------------- News
    def _news(self):
        if NewsPost.objects.filter(titel__startswith="Demo").exists():
            return
        autor = User.objects.get(username="vorstand")
        for index, eintrag in enumerate(NEWS):
            titel, kategorie, text = eintrag[0], eintrag[1], eintrag[2]
            veroeffentlicht = eintrag[3] if len(eintrag) > 3 else True
            if NewsPost.objects.filter(titel=titel).exists():
                continue
            post = NewsPost(
                titel=titel,
                text=text,
                kategorie=kategorie,
                autor=autor,
                veroeffentlicht=veroeffentlicht,
            )
            post.save()
            if veroeffentlicht:
                post.veroeffentlicht_am = timezone.now() - timedelta(days=index * 9 + 2)
                post.save(update_fields=["veroeffentlicht_am"])

    # ------------------------------------------------------------------ Kasse
    def _kasse(self):
        if CashEntry.objects.exists():
            return
        kassenwart = User.objects.get(username="kassenwart")
        buchungen = [
            (CashEntry.Art.EINNAHME, CashEntry.Kategorie.BEITRAEGE, "1840.00", f"{VORJAHR}-03-04", "Beitragseingänge Sammelüberweisung", "K-2025-01"),
            (CashEntry.Art.AUSGABE, CashEntry.Kategorie.RAUMKOSTEN, "480.00", f"{VORJAHR}-04-01", "Miete Vereinsheim Q2", "R-2025-04"),
            (CashEntry.Art.AUSGABE, CashEntry.Kategorie.VERBANDSABGABEN, "312.00", f"{VORJAHR}-05-12", "Verbandsabgaben (3 Mannschaften)", "V-2025-05"),
            (CashEntry.Art.AUSGABE, CashEntry.Kategorie.TURNIERKOSTEN, "268.40", f"{VORJAHR}-06-20", "Sachpreise Vereinsmeisterschaft", "T-2025-06"),
            (CashEntry.Art.EINNAHME, CashEntry.Kategorie.SPONSORING, "250.00", f"{VORJAHR}-09-02", "Spende Autohaus Krämer", "S-2025-09"),
            (CashEntry.Art.EINNAHME, CashEntry.Kategorie.BEITRAEGE, "2130.00", f"{JAHR}-03-06", "Beitragseingänge Sammelüberweisung", "K-2026-01"),
            (CashEntry.Art.EINNAHME, CashEntry.Kategorie.STARTGELD, "85.00", f"{JAHR}-04-18", "Startgelder Vereinsmeisterschaft", "SG-2026-01"),
            (CashEntry.Art.AUSGABE, CashEntry.Kategorie.RAUMKOSTEN, "520.00", f"{JAHR}-05-02", "Miete Vereinsheim Q2 (angepasst)", "R-2026-05"),
            (CashEntry.Art.AUSGABE, CashEntry.Kategorie.MATERIAL, "189.90", f"{JAHR}-06-11", "Sechs Turnierbretter mit Figuren", "M-2026-06"),
            (CashEntry.Art.AUSGABE, CashEntry.Kategorie.MATERIAL, "142.60", f"{JAHR}-06-25", "Trainingsmaterial Jugendgruppe", "M-2026-06b"),
            (CashEntry.Art.EINNAHME, CashEntry.Kategorie.SONSTIGES, "64.50", f"{JAHR}-07-09", "Getränkeausgleich Vereinsabend", "SO-2026-07"),
            (CashEntry.Art.AUSGABE, CashEntry.Kategorie.EHRUNGEN, "75.00", f"{JAHR}-07-15", "Pokalgravur Wanderpokal", "E-2026-07"),
        ]
        for art, kategorie, betrag, datum, beschreibung, belegnummer in buchungen:
            CashEntry.objects.create(
                art=art,
                kategorie=kategorie,
                betrag=Decimal(betrag),
                datum=date.fromisoformat(datum),
                beschreibung=beschreibung,
                belegnummer=belegnummer,
                erfasst_von=kassenwart,
            )

    # ------------------------------------------------------- Änderungswünsche
    def _aenderungswuensche(self, mitglieder):
        if ChangeRequest.objects.exists():
            return
        vorstand = User.objects.get(username="vorstand")
        mitglied_mit_konto = Member.objects.get(user__username="mitglied")
        kandidaten = [mitglied_mit_konto] + [m for m in mitglieder if m.user is None][:4]
        wuensche = [
            ("telefon", "0176 2345678", ChangeRequest.Status.EINGEREICHT, "", None),
            ("strasse", "Neue Straße 14", ChangeRequest.Status.EINGEREICHT, "", None),
            ("email", "neue.adresse@example.org", ChangeRequest.Status.FREIGEGEBEN, "Übernommen, bitte im Vereinsverteiler prüfen.", 12),
            ("ort", "Göttingen", ChangeRequest.Status.ABGELEHNT, "Bitte PLZ und Ort gemeinsam ändern.", 20),
        ]
        for index, (feld, wert, status, kommentar, tage) in enumerate(wuensche):
            mitglied = kandidaten[index % len(kandidaten)]
            wunsch = ChangeRequest(
                member=mitglied,
                feld=feld,
                wunschwert=wert,
                status=status,
                eingereicht_von=mitglied.user or vorstand,
                kommentar=kommentar,
            )
            wunsch.save()
            if status != ChangeRequest.Status.EINGEREICHT:
                wunsch.entschieden_von = vorstand
                wunsch.entschieden_am = timezone.now() - timedelta(days=tage or 5)
                wunsch.save(update_fields=["entschieden_von", "entschieden_am"])

    # ----------------------------------------------------------- Mailprotokoll
    def _mail_protokoll(self):
        if MailLog.objects.exists():
            return
        vorstand = User.objects.get(username="vorstand")
        MailLog.objects.create(
            betreff="Vereinsabend und Training nach den Sommerferien",
            text=(
                "Liebe Schachfreundinnen und Schachfreunde,\n\n"
                "ab Donnerstag geht das Training wieder wie gewohnt um 19:00 Uhr los. "
                "Gäste sind willkommen – einfach vorbeikommen.\n\n"
                "Mit freundschaftlichen Grüßen\nEure Vorstandschaft"
            ),
            zielgruppe=MailLog.Zielgruppe.AKTIV,
            anzahl_empfaenger=32,
            anzahl_uebersprungen=4,
            status=MailLog.Status.GESENDET,
            erstellt_von=vorstand,
        )
