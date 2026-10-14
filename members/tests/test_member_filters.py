"""Tests für Schnellfilter und Smart Badges in der Mitgliederliste (Hebel F5)."""

from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase

from dues.models import FeeCategory, SepaMandate
from members.models import Member


def make_admin():
    user = User.objects.create_user("vorstand", password="x")
    group, _ = Group.objects.get_or_create(name="admin")
    user.groups.add(group)
    return user


class MemberFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_admin()
        cls.kategorie = FeeCategory.objects.create(name="Erwachsene")

        # 1. Jugendliches Mitglied (14 Jahre alt) mit Kategorie und Mandat
        cls.m_jugend = Member.objects.create(
            vorname="Tim", nachname="Talent",
            geburtsdatum=date(2012, 5, 10),
            eintrittsdatum=date(2020, 1, 1),
            status=Member.Status.AKTIV,
            beitragskategorie=cls.kategorie,
        )
        SepaMandate.objects.create(
            member=cls.m_jugend, referenz="MND-JUGEND",
            iban="DE89370400440532013000", kontoinhaber="Eltern",
            erteilt_am=date(2020, 1, 1), status=SepaMandate.Status.AKTIV,
        )

        # 2. Senior (68 Jahre alt) mit Kategorie OHNE Mandat
        cls.m_senior = Member.objects.create(
            vorname="Siegfried", nachname="Senior",
            geburtsdatum=date(1958, 3, 15),
            eintrittsdatum=date(2010, 1, 1),
            status=Member.Status.AKTIV,
            beitragskategorie=cls.kategorie,
        )

        # 3. Erwachsener (30 Jahre alt) OHNE Kategorie mit Mandat
        cls.m_ohne_kat = Member.objects.create(
            vorname="Otto", nachname="Ohnekat",
            geburtsdatum=date(1996, 7, 20),
            eintrittsdatum=date(2024, 1, 1),
            status=Member.Status.AKTIV,
            beitragskategorie=None,
        )
        SepaMandate.objects.create(
            member=cls.m_ohne_kat, referenz="MND-OTTO",
            iban="DE89370400440532013001", kontoinhaber="Otto Ohnekat",
            erteilt_am=date(2024, 1, 1), status=SepaMandate.Status.AKTIV,
        )

        # 4. Passives Mitglied
        cls.m_passiv = Member.objects.create(
            vorname="Paul", nachname="Passiv",
            geburtsdatum=date(1990, 1, 1),
            eintrittsdatum=date(2015, 1, 1),
            status=Member.Status.PASSIV,
        )

    def test_filter_u18(self):
        self.client.force_login(self.admin)
        response = self.client.get("/mitglieder/?filter=u18")
        self.assertEqual(response.status_code, 200)
        mitglieder = list(response.context["mitglieder"])
        self.assertIn(self.m_jugend, mitglieder)
        self.assertNotIn(self.m_senior, mitglieder)
        self.assertNotIn(self.m_ohne_kat, mitglieder)

    def test_filter_senioren(self):
        self.client.force_login(self.admin)
        response = self.client.get("/mitglieder/?filter=senioren")
        self.assertEqual(response.status_code, 200)
        mitglieder = list(response.context["mitglieder"])
        self.assertIn(self.m_senior, mitglieder)
        self.assertNotIn(self.m_jugend, mitglieder)

    def test_filter_ohne_kategorie(self):
        self.client.force_login(self.admin)
        response = self.client.get("/mitglieder/?filter=ohne_kategorie")
        self.assertEqual(response.status_code, 200)
        mitglieder = list(response.context["mitglieder"])
        self.assertIn(self.m_ohne_kat, mitglieder)
        self.assertNotIn(self.m_jugend, mitglieder)

    def test_filter_ohne_mandat(self):
        self.client.force_login(self.admin)
        response = self.client.get("/mitglieder/?filter=ohne_mandat")
        self.assertEqual(response.status_code, 200)
        mitglieder = list(response.context["mitglieder"])
        self.assertIn(self.m_senior, mitglieder)
        self.assertNotIn(self.m_jugend, mitglieder)

    def test_smart_counts_im_kontext(self):
        self.client.force_login(self.admin)
        response = self.client.get("/mitglieder/")
        self.assertEqual(response.status_code, 200)
        counts = response.context["smart_counts"]
        self.assertEqual(counts["gesamt"], 4)
        self.assertEqual(counts["aktiv"], 3)
        self.assertEqual(counts["u18"], 1)
        self.assertEqual(counts["senioren"], 1)
        self.assertEqual(counts["ohne_kategorie"], 1)
        self.assertEqual(counts["ohne_mandat"], 1)
