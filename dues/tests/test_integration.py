"""End-to-End über ein ganzes Beitragsjahr (T9).

Deckt den Fluss ab, den der Verein tatsächlich fährt: Beitragslauf →
Zahlung buchen → Posten ist bezahlt → Fehlbuchung stornieren → wieder offen.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase

from core.models import AuditLog
from dues.models import FeeCategory, FeePost, Payment, SepaMandate
from dues.services import PostenStatus, fuehre_lauf, offen, posten_status
from members.models import Member

BUCHEN = "/beitraege/zahlungen/buchen/"


class BeitragsjahrVerlaufTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("vorstand", password="x")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.client.force_login(self.admin)
        self.member = Member.objects.create(
            vorname="Anna",
            nachname="Meier",
            eintrittsdatum=date(2020, 1, 15),
            beitragskategorie=FeeCategory.objects.get(code="erwachsene"),
        )
        SepaMandate.objects.create(member=self.member, referenz="M-2026-001")

    def test_lauf_buchung_storno_und_ueberzahlung(self):
        fuehre_lauf(2026)
        post = FeePost.objects.get(jahr=2026)
        self.assertEqual(post.betrag, Decimal("90.00"))
        self.assertEqual(posten_status(post), PostenStatus.UNBEZAHLT)

        # 1) SEPA-Einzug über den vollen Betrag.
        self.client.post(
            BUCHEN,
            {"post": post.pk, "betrag": "90,00", "art": Payment.Art.SEPA},
            follow=True,
        )
        post.refresh_from_db()
        self.assertEqual(posten_status(post), PostenStatus.BEZAHLT)
        self.assertEqual(offen(post), Decimal("0.00"))

        # 2) Überzahlung im Folgejahr: sichtbar als Gutschrift, nicht gekappt.
        fuehre_lauf(2027)
        post_2027 = FeePost.objects.get(jahr=2027)
        self.client.post(
            BUCHEN,
            {"post": post_2027.pk, "betrag": "100.00", "art": Payment.Art.UEBERWEISUNG},
        )
        self.assertEqual(posten_status(post_2027), PostenStatus.GUTSCHRIFT)
        self.assertEqual(offen(post_2027), Decimal("-5.00"))

        # 3) Fehlbuchung aufheben: Gegenbuchung, Original bleibt erhalten.
        original = Payment.objects.get(post=post_2027)
        self.client.post(f"/beitraege/zahlungen/{original.pk}/storno/")
        self.assertTrue(Payment.objects.filter(pk=original.pk).exists())
        self.assertEqual(posten_status(post_2027), PostenStatus.UNBEZAHLT)
        self.assertEqual(offen(post_2027), Decimal("95.00"))

    def test_audit_log_erzaehlt_den_ganzen_verlauf(self):
        fuehre_lauf(2026)
        post = FeePost.objects.get(jahr=2026)
        self.client.post(
            BUCHEN, {"post": post.pk, "betrag": "90.00", "art": Payment.Art.SEPA}
        )
        zahlung = Payment.objects.get()
        self.client.post(f"/beitraege/zahlungen/{zahlung.pk}/storno/")

        aktionen = list(
            AuditLog.objects.filter(
                aktion__in=["Beitragslauf ausgeführt", "Zahlung gebucht", "Zahlung storniert"]
            )
            .order_by("pk")
            .values_list("aktion", flat=True)
        )
        self.assertEqual(
            aktionen,
            [
                "Beitragslauf ausgeführt",
                "Zahlung gebucht",
                "Zahlung storniert",
            ],
        )
        # Die Zahlungszeilen tragen das Mitglied; der Lauf ist eine Sammelzeile
        # über alle Posten (Muster aus T8) und hat deshalb kein einzelnes Mitglied.
        for eintrag in AuditLog.objects.filter(
            aktion__in=["Zahlung gebucht", "Zahlung storniert"]
        ):
            self.assertEqual(eintrag.member, self.member)
            self.assertEqual(eintrag.benutzer, self.admin)
        self.assertIsNone(AuditLog.objects.get(aktion="Beitragslauf ausgeführt").member)
