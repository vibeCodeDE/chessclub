"""Tests für den persönlichen Kalender-Feed eines Mitglieds (Hebel F4)."""

from datetime import date, time

from django.contrib.auth.models import Group, User
from django.core.signing import TimestampSigner
from django.test import TestCase

from members.models import Member
from members.views import get_personal_calendar_token
from teams.models import LeagueMatch, LineupEntry, Team
from tournaments.models import Tournament


class PersonalCalendarFeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user("schachfan", password="x")
        group, _ = Group.objects.get_or_create(name="mitglied")
        user.groups.add(group)

        cls.member = Member.objects.create(
            user=user,
            vorname="Felix",
            nachname="Freispringer",
            eintrittsdatum=date(2022, 1, 1),
            dwz=1780,
        )

        team = Team.objects.create(name="1. Mannschaft", liga="Bezirksliga", brettanzahl=4)
        match = LeagueMatch.objects.create(
            team=team,
            datum=date(2026, 12, 6),
            uhrzeit=time(10, 0),
            gegner="SK Springer",
            heimspiel=True,
            ort="Vereinsheim",
            runde="Runde 4",
        )
        LineupEntry.objects.create(
            match=match,
            brett=2,
            member=cls.member,
            gegner_name="Dr. Bauer",
        )

        cls.turnier = Tournament.objects.create(
            name="Nikolaus-Blitz 2026",
            datum=date(2026, 12, 5),
            ort="Klubraum",
            runden_anzahl=7,
            status=Tournament.Status.ANMELDUNG,
            oeffentlich=True,
        )

    def test_personal_calendar_feed_gueltiger_token(self):
        token = get_personal_calendar_token(self.member)
        url = f"/mitglieder/kalender/{token}.ics"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/calendar; charset=utf-8")
        content = response.content.decode("utf-8")
        self.assertIn("BEGIN:VCALENDAR", content)
        self.assertIn("Freispringer", content)
        self.assertIn("SK Springer", content)
        self.assertIn("Brett 2", content)
        self.assertIn("Nikolaus-Blitz 2026", content)

    def test_personal_calendar_feed_ungueltiger_token_liefert_404(self):
        url = "/mitglieder/kalender/ungueltiger-token-123.ics"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_personal_calendar_feed_manipulierter_token_liefert_404(self):
        signer = TimestampSigner(salt="wrong-salt")
        fake_token = signer.sign("99999")
        url = f"/mitglieder/kalender/{fake_token}.ics"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
