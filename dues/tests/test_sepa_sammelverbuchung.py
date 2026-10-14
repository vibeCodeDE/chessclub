"""Tests für die SEPA-Sammelverbuchung (Hebel F1)."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import AuditLog
from dues.models import FeeAmount, FeeCategory, MembershipFee, Payment, SepaMandate
from dues.services import sepa_sammelverbuchung
from members.models import Member


def make_user(username, role="admin"):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    return user


class SepaSammelverbuchungServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("kassenwart", "admin")
        cls.kategorie = FeeCategory.objects.create(name="Erwachsene")
        FeeAmount.objects.create(kategorie=cls.kategorie, jahr=2026, betrag=Decimal("90.00"))

        # Mitglied 1: Offener Posten mit aktivem Mandat
        cls.m1 = Member.objects.create(
            vorname="Max", nachname="Mustermann",
            eintrittsdatum=date(2020, 1, 1), beitragskategorie=cls.kategorie,
        )
        cls.mandat1 = SepaMandate.objects.create(
            member=cls.m1, referenz="MND-001",
            iban="DE89370400440532013000", kontoinhaber="Max Mustermann",
            erteilt_am=date(2025, 1, 10), status=SepaMandate.Status.AKTIV,
        )
        cls.fee1 = MembershipFee.objects.create(
            member=cls.m1, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
            status=MembershipFee.Status.OFFEN,
        )

        # Mitglied 2: Teilweise bezahlt mit aktivem Mandat (Rest 40 €)
        cls.m2 = Member.objects.create(
            vorname="Anna", nachname="Schmidt",
            eintrittsdatum=date(2021, 1, 1), beitragskategorie=cls.kategorie,
        )
        cls.mandat2 = SepaMandate.objects.create(
            member=cls.m2, referenz="MND-002",
            iban="DE89370400440532013001", kontoinhaber="Anna Schmidt",
            erteilt_am=date(2025, 1, 10), status=SepaMandate.Status.AKTIV,
        )
        cls.fee2 = MembershipFee.objects.create(
            member=cls.m2, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
            status=MembershipFee.Status.TEILWEISE,
        )
        Payment.objects.create(
            fee=cls.fee2, betrag=Decimal("50.00"), datum=date(2026, 2, 1),
            art=Payment.Art.BAR,
        )

        # Mitglied 3: Offener Posten OHNE Mandat (darf NICHT verbucht werden)
        cls.m3 = Member.objects.create(
            vorname="Bernd", nachname="Bauer",
            eintrittsdatum=date(2022, 1, 1), beitragskategorie=cls.kategorie,
        )
        cls.fee3 = MembershipFee.objects.create(
            member=cls.m3, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
            status=MembershipFee.Status.OFFEN,
        )

        # Mitglied 4: Bereits VOLLSTÄNDIG bezahlt (darf nicht doppelt gebucht werden)
        cls.m4 = Member.objects.create(
            vorname="Clara", nachname="Claus",
            eintrittsdatum=date(2023, 1, 1), beitragskategorie=cls.kategorie,
        )
        cls.mandat4 = SepaMandate.objects.create(
            member=cls.m4, referenz="MND-004",
            iban="DE89370400440532013004", kontoinhaber="Clara Claus",
            erteilt_am=date(2025, 1, 10), status=SepaMandate.Status.AKTIV,
        )
        cls.fee4 = MembershipFee.objects.create(
            member=cls.m4, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
            status=MembershipFee.Status.BEZAHLT,
        )
        Payment.objects.create(
            fee=cls.fee4, betrag=Decimal("90.00"), datum=date(2026, 1, 20),
            art=Payment.Art.UEBERWEISUNG,
        )

    def test_sepa_sammelverbuchung_service_erfolg(self):
        res = sepa_sammelverbuchung(jahr=2026, benutzer=self.admin, buchungsdatum=date(2026, 3, 1))

        self.assertEqual(res["anzahl"], 2)
        self.assertEqual(res["summe"], Decimal("130.00"))  # 90.00 von fee1 + 40.00 von fee2

        self.fee1.refresh_from_db()
        self.fee2.refresh_from_db()
        self.fee3.refresh_from_db()
        self.fee4.refresh_from_db()

        self.assertEqual(self.fee1.status, MembershipFee.Status.BEZAHLT)
        self.assertEqual(self.fee1.offener_betrag, Decimal("0.00"))
        self.assertEqual(self.fee2.status, MembershipFee.Status.BEZAHLT)
        self.assertEqual(self.fee2.offener_betrag, Decimal("0.00"))

        # Posten ohne Mandat bleibt unberührt
        self.assertEqual(self.fee3.status, MembershipFee.Status.OFFEN)
        self.assertEqual(self.fee3.offener_betrag, Decimal("90.00"))

        # Posten der bereits bezahlt war hat keine weiteren Zahlungen erhalten
        self.assertEqual(self.fee4.zahlungen.count(), 1)

        # AuditLog vorhanden
        self.assertTrue(
            AuditLog.objects.filter(aktion="SEPA-Sammelverbuchung", benutzer=self.admin).exists()
        )

    def test_sepa_sammelverbuchung_ohne_offene_posten_wirft_validation_error(self):
        # Jahr 2025 hat keine Posten
        with self.assertRaises(ValidationError) as ctx:
            sepa_sammelverbuchung(jahr=2025, benutzer=self.admin)
        self.assertIn("Keine offenen Posten mit aktivem SEPA-Mandat", str(ctx.exception))


class SepaSammelverbuchungViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("admin_user", "admin")
        cls.kapitaen = make_user("kapitaen_user", "kapitaen")
        cls.mitglied = make_user("mitglied_user", "mitglied")

        cls.kategorie = FeeCategory.objects.create(name="Erwachsene")
        FeeAmount.objects.create(kategorie=cls.kategorie, jahr=2026, betrag=Decimal("90.00"))
        cls.m1 = Member.objects.create(
            vorname="Max", nachname="Mustermann",
            eintrittsdatum=date(2020, 1, 1), beitragskategorie=cls.kategorie,
        )
        cls.mandat1 = SepaMandate.objects.create(
            member=cls.m1, referenz="MND-001",
            iban="DE89370400440532013000", kontoinhaber="Max Mustermann",
            erteilt_am=date(2025, 1, 10), status=SepaMandate.Status.AKTIV,
        )
        cls.fee1 = MembershipFee.objects.create(
            member=cls.m1, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
            status=MembershipFee.Status.OFFEN,
        )

    def test_sepa_sammelverbuchung_view_admin_erfolg(self):
        self.client.force_login(self.admin)
        url = "/beitraege/lauf/2026/sepa-verbuchen/"
        response = self.client.post(url, {"buchungsdatum": "2026-03-01"})
        self.assertRedirects(response, "/beitraege/?jahr=2026")
        self.fee1.refresh_from_db()
        self.assertEqual(self.fee1.status, MembershipFee.Status.BEZAHLT)

    def test_sepa_sammelverbuchung_view_negativtest_403(self):
        # PRD §3.8: Rolle kapitaen und mitglied erhalten 403
        for user in [self.kapitaen, self.mitglied]:
            self.client.force_login(user)
            url = "/beitraege/lauf/2026/sepa-verbuchen/"
            response = self.client.post(url, {"buchungsdatum": "2026-03-01"})
            self.assertEqual(response.status_code, 403, f"User {user.username} should get 403")
            self.fee1.refresh_from_db()
            self.assertEqual(self.fee1.status, MembershipFee.Status.OFFEN)

    def test_sepa_sammelverbuchung_view_negativtest_get_405(self):
        self.client.force_login(self.admin)
        url = "/beitraege/lauf/2026/sepa-verbuchen/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)
