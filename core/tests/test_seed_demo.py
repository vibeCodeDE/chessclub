"""Der Demo-Datensatz muss laufen und wiederholbar sein."""

from django.core.management import call_command
from django.test import TestCase

from cashbook.models import CashEntry
from comms.models import NewsPost
from dues.models import FeeCategory, MembershipFee, Payment, SepaMandate
from members.models import Member
from teams.models import LeagueMatch, LineupEntry, Team
from tournaments.models import Pairing, Tournament


class SeedDemoTests(TestCase):
    def test_seed_legt_realistische_daten_an(self):
        call_command("seed_demo", verbosity=0)

        self.assertGreaterEqual(Member.objects.count(), 45)
        self.assertTrue(Member.objects.filter(status=Member.Status.AUSGETRETEN).exists())
        self.assertTrue(Member.objects.filter(status=Member.Status.PASSIV).exists())
        self.assertTrue(Member.objects.filter(beitragskategorie__isnull=False).exists())

        self.assertGreaterEqual(FeeCategory.objects.count(), 4)
        self.assertGreaterEqual(MembershipFee.objects.count(), 40)
        self.assertTrue(Payment.objects.exists())
        self.assertTrue(SepaMandate.objects.exists())
        self.assertTrue(
            MembershipFee.objects.filter(mahnstufe__gt=0).exists(),
            "Es sollten Mahnungen im Demo-Datensatz enthalten sein.",
        )

        self.assertGreaterEqual(Team.objects.count(), 3)
        self.assertTrue(LeagueMatch.objects.filter(status=LeagueMatch.Status.GESPIELT).exists())
        self.assertTrue(LineupEntry.objects.filter(ergebnis__gt="").exists())

        self.assertTrue(Tournament.objects.filter(status=Tournament.Status.BEENDET).exists())
        self.assertTrue(Tournament.objects.filter(status=Tournament.Status.ANMELDUNG).exists())
        self.assertTrue(Pairing.objects.exists())

        self.assertTrue(NewsPost.objects.filter(veroeffentlicht=True).count() >= 5)
        self.assertTrue(NewsPost.objects.filter(veroeffentlicht=False).exists())
        self.assertTrue(CashEntry.objects.exists())

    def test_login_konten_mit_passwort(self):
        call_command("seed_demo", verbosity=0)
        self.client.logout()
        self.assertTrue(self.client.login(username="vorstand", password="schach2026"))
        self.client.logout()
        self.assertTrue(self.client.login(username="mitglied", password="schach2026"))

    def test_seed_ist_wiederholbar(self):
        call_command("seed_demo", verbosity=0)
        mitglieder = Member.objects.count()
        posten = MembershipFee.objects.count()
        zahlungen = Payment.objects.count()

        call_command("seed_demo", verbosity=0)

        self.assertEqual(Member.objects.count(), mitglieder)
        self.assertEqual(MembershipFee.objects.count(), posten)
        self.assertEqual(Payment.objects.count(), zahlungen)

    def test_reset_raeumt_auf(self):
        call_command("seed_demo", verbosity=0)
        vorher = (Member.objects.count(), MembershipFee.objects.count(), NewsPost.objects.count())
        call_command("seed_demo", "--reset", verbosity=0)
        self.assertEqual(
            (Member.objects.count(), MembershipFee.objects.count(), NewsPost.objects.count()), vorher,
            "--reset muss denselben Datenbestand erzeugen, nicht doppeln",
        )
        self.assertEqual(Member.objects.filter(status=Member.Status.AUSGETRETEN).count(), 4)
        self.assertTrue(Member.objects.filter(status=Member.Status.PASSIV).exists())

    def test_ohne_reset_wird_nicht_gedoppelt(self):
        call_command("seed_demo", verbosity=0)
        mitglieder = Member.objects.count()
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Member.objects.count(), mitglieder)
