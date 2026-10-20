"""Tests für den persönlichen Kalender-Feed eines Mitglieds (Hebel F4, DSGVO Token Revocation)."""

from datetime import date, time

from django.contrib.auth.models import Group, User
from django.core.signing import TimestampSigner
from django.test import TestCase
from django.urls import reverse

from core.models import AuditLog
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

        cls.user = user
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
        token = self.member.ical_token
        self.assertTrue(bool(token))
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

    def test_personal_calendar_feed_alter_timestamp_signer_token_liefert_404(self):
        # Alter Signer-Token darf nicht mehr akzeptiert werden (DSGVO Access Revocation)
        signer = TimestampSigner(salt="member-personal-calendar")
        old_token = signer.sign(str(self.member.pk))
        url = f"/mitglieder/kalender/{old_token}.ics"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_personal_calendar_feed_ausgetretenes_mitglied_liefert_404(self):
        token = self.member.ical_token
        self.member.status = Member.Status.AUSGETRETEN
        self.member.austrittsdatum = date(2026, 1, 1)
        self.member.save(update_fields=["status", "austrittsdatum"])

        url = f"/mitglieder/kalender/{token}.ics"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_renew_ical_token_invalidiert_alten_token(self):
        alter_token = self.member.ical_token
        neuer_token = self.member.renew_ical_token()

        self.assertNotEqual(alter_token, neuer_token)
        self.assertEqual(self.member.ical_token, neuer_token)

        # Alter Token muss sofort 404 liefern
        resp_alt = self.client.get(f"/mitglieder/kalender/{alter_token}.ics")
        self.assertEqual(resp_alt.status_code, 404)

        # Neuer Token funktioniert einwandfrei
        resp_neu = self.client.get(f"/mitglieder/kalender/{neuer_token}.ics")
        self.assertEqual(resp_neu.status_code, 200)

    def test_renew_ical_token_view_erfolgreich_mit_auditlog(self):
        self.client.login(username="schachfan", password="x")
        alter_token = self.member.ical_token

        url = reverse("members:renew_personal_calendar_token")
        response = self.client.post(url)

        self.assertRedirects(response, reverse("members:profil"))
        self.member.refresh_from_db()
        self.assertNotEqual(self.member.ical_token, alter_token)

        # AuditLog-Eintrag prüfen
        log_eintrag = AuditLog.objects.filter(
            aktion="Kalender-Token erneuert",
            member=self.member,
        ).latest("zeitpunkt")
        self.assertEqual(log_eintrag.benutzer, self.user)
        self.assertIn("erneuert", log_eintrag.text)
        # Geheimnistoken darf nicht im Klartext im AuditLog stehen
        self.assertNotIn(self.member.ical_token, log_eintrag.text)
        self.assertNotIn(self.member.ical_token, log_eintrag.alt_wert)
        self.assertNotIn(self.member.ical_token, log_eintrag.neu_wert)

    def test_renew_ical_token_view_negativ_get_abgewiesen(self):
        self.client.login(username="schachfan", password="x")
        url = reverse("members:renew_personal_calendar_token")
        response = self.client.get(url)
        # @require_POST liefert 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)

    def test_renew_ical_token_view_negativ_anonym_abgewiesen(self):
        url = reverse("members:renew_personal_calendar_token")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)

    def test_renew_ical_token_view_negativ_user_ohne_member(self):
        User.objects.create_user("keinmitglied", password="x")
        self.client.login(username="keinmitglied", password="x")

        url = reverse("members:renew_personal_calendar_token")
        response = self.client.post(url, follow=True)

        self.assertRedirects(response, reverse("members:profil"))
        self.assertContains(response, "Für dieses Konto ist kein Mitgliedsprofil hinterlegt.")

    def test_profil_ansicht_enthaelt_kalender_url_und_erneuern_formular(self):
        self.client.login(username="schachfan", password="x")
        response = self.client.get(reverse("members:profil"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.member.ical_token)
        self.assertContains(response, reverse("members:renew_personal_calendar_token"))
        self.assertContains(response, "Token erneuern")

    def test_personal_calendar_feed_query_count(self):
        token = self.member.ical_token
        url = f"/mitglieder/kalender/{token}.ics"
        with self.assertNumQueries(3):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
