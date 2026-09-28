from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import AuditLog
from dues.models import FeeAmount, FeeCategory, FeePost
from members.models import Member


class FeeCategoryAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser("root", password="x")
        self.client.login(username="root", password="x")

    def test_changelist_zeigt_die_ge_seedeten_kategorien(self):
        response = self.client.get("/admin/dues/feecategory/")
        self.assertEqual(response.status_code, 200)
        for code in ("erwachsene", "jugend", "familie", "ermaeßigt"):
            self.assertContains(response, code)

    def test_inline_zeigt_die_jahresbetraege(self):
        kategorie = FeeCategory.objects.get(code="erwachsene")
        response = self.client.get(f"/admin/dues/feecategory/{kategorie.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026")
        self.assertContains(response, "2027")
        self.assertContains(response, "90,00")

    def test_betrag_2027_ueber_admin_aendert_2026_nicht(self):
        """Der Jahreswechsel im Admin: 2027 pflegen, 2026 bleibt unberührt."""
        kategorie = FeeCategory.objects.get(code="erwachsene")
        vorher_2026 = kategorie.betraege.get(jahr=2026).betrag

        response = self.client.post(
            f"/admin/dues/feecategory/{kategorie.pk}/change/",
            {
                "code": kategorie.code,
                "bezeichnung": kategorie.bezeichnung,
                "aktiv": "on",
                "betraege-TOTAL_FORMS": "2",
                "betraege-INITIAL_FORMS": "2",
                "betraege-MIN_NUM_FORMS": "0",
                "betraege-MAX_NUM_FORMS": "1000",
                "betraege-0-id": str(kategorie.betraege.get(jahr=2026).pk),
                "betraege-0-kategorie": str(kategorie.pk),
                "betraege-0-jahr": "2026",
                "betraege-0-betrag": "90.00",
                "betraege-1-id": str(kategorie.betraege.get(jahr=2027).pk),
                "betraege-1-kategorie": str(kategorie.pk),
                "betraege-1-jahr": "2027",
                "betraege-1-betrag": "99.00",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(kategorie.betraege.get(jahr=2026).betrag, vorher_2026)
        self.assertEqual(kategorie.betraege.get(jahr=2027).betrag, Decimal("99.00"))


class FeeAmountAdminTests(TestCase):
    def setUp(self):
        User.objects.create_superuser("root", password="x")
        self.client.login(username="root", password="x")

    def test_anlegen_eines_satzes_fuer_ein_neues_jahr(self):
        kategorie = FeeCategory.objects.get(code="jugend")
        vorher = FeeAmount.objects.count()
        response = self.client.post(
            "/admin/dues/feeamount/add/",
            {
                "kategorie": str(kategorie.pk),
                "jahr": "2028",
                "betrag": "49.00",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FeeAmount.objects.count(), vorher + 1)
        self.assertTrue(
            FeeAmount.objects.filter(
                kategorie=kategorie, jahr=2028, betrag=Decimal("49.00")
            ).exists()
        )

    def test_negativer_betrag_wird_im_admin_abgelehnt(self):
        """Negativtest: die Formularvalidierung greift vor der Datenbank."""
        kategorie = FeeCategory.objects.get(code="jugend")
        vorher = FeeAmount.objects.count()
        response = self.client.post(
            "/admin/dues/feeamount/add/",
            {
                "kategorie": str(kategorie.pk),
                "jahr": "2029",
                "betrag": "-5.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Betrag darf nicht negativ sein")
        self.assertEqual(FeeAmount.objects.count(), vorher)


class MemberKategorieAdminTests(TestCase):
    """Die Kategorie wird im Mitglieder-Admin gepflegt (T7)."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser("root", password="x")
        self.client.login(username="root", password="x")
        self.kategorie = FeeCategory.objects.get(code="familie")

    def _stammdaten(self, **kwargs):
        daten = {
            "vorname": "Anna",
            "nachname": "Meier",
            "geburtsdatum": "",
            "strasse": "",
            "plz": "",
            "ort": "",
            "email": "",
            "telefon": "",
            "eintrittsdatum": "15.01.2020",
            "austrittsdatum": "",
            "status": "aktiv",
            "user": "",
            "beitragskategorie": str(self.kategorie.pk),
            "status_history-TOTAL_FORMS": "0",
            "status_history-INITIAL_FORMS": "0",
        }
        daten.update(kwargs)
        return daten

    def test_admin_kann_mitglied_eine_kategorie_zuweisen(self):
        response = self.client.post(
            "/admin/members/member/add/", self._stammdaten()
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Member.objects.filter(nachname="Meier", beitragskategorie=self.kategorie).exists()
        )

    def test_mitglied_kann_ohne_kategorie_gespeichert_werden(self):
        response = self.client.post(
            "/admin/members/member/add/", self._stammdaten(beitragskategorie="")
        )
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(Member.objects.get(nachname="Meier").beitragskategorie)

    def test_ausgetreten_mit_kategorie_wird_im_admin_abgelehnt(self):
        """Negativtest laut Plan T7 – greift im Member-Formular."""
        vorher = Member.objects.count()
        response = self.client.post(
            "/admin/members/member/add/",
            self._stammdaten(status="ausgetreten", austrittsdatum="30.06.2026"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "ausgetretenes Mitglied kann keiner Beitragskategorie zugeordnet"
        )
        self.assertEqual(Member.objects.count(), vorher)

    def test_changelist_filtert_nach_kategorie(self):
        Member.objects.create(
            vorname="Anna",
            nachname="Meier",
            eintrittsdatum=date(2020, 1, 15),
            beitragskategorie=self.kategorie,
        )
        Member.objects.create(vorname="Bernd", nachname="Schmidt", eintrittsdatum=date(2020, 1, 15))
        response = self.client.get(
            "/admin/members/member/", {"beitragskategorie__id__exact": self.kategorie.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meier")
        self.assertNotContains(response, "Schmidt")


class FeePostAdminTests(TestCase):
    """Beitragsposten sind Finanznachweis: kein Anlegen, kein Löschen, Änderung mit Spur."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser("root", password="x")
        self.client.login(username="root", password="x")
        self.kategorie = FeeCategory.objects.get(code="erwachsene")
        self.member = Member.objects.create(
            vorname="Anna",
            nachname="Meier",
            eintrittsdatum=date(2020, 1, 15),
            beitragskategorie=self.kategorie,
        )
        self.post = FeePost.objects.create(
            member=self.member,
            jahr=2027,
            kategorie=self.kategorie,
            betrag=Decimal("95.00"),
        )

    def test_changelist_zeigt_die_posten(self):
        response = self.client.get("/admin/dues/feepost/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meier")
        self.assertContains(response, "2027")

    def test_posten_kann_im_admin_nicht_angelegt_werden(self):
        """Negativtest: Posten entstehen nur über den Beitragslauf (PRD M2.2)."""
        vorher = FeePost.objects.count()

        response = self.client.get("/admin/dues/feepost/add/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(FeePost.objects.count(), vorher)

    def test_posten_kann_im_admin_nicht_geloescht_werden(self):
        """Negativtest: die Löschaktion des Admin entfernt keinen Posten."""
        response = self.client.post(
            "/admin/dues/feepost/",
            {
                "action": "delete_selected",
                "_selected_action": [str(self.post.pk)],
                "post": "yes",
            },
        )

        self.assertNotContains(response, "wurde gelöscht")
        self.assertTrue(FeePost.objects.filter(pk=self.post.pk).exists())

    def test_betragskorrektur_bleibt_nachvollziehbar(self):
        """Korrektur eines falschen Betrags ist erlaubt — aber mit Audit-Eintrag."""
        response = self.client.post(
            f"/admin/dues/feepost/{self.post.pk}/change/",
            {
                "member": self.member.pk,
                "jahr": 2027,
                "kategorie": self.kategorie.pk,
                "betrag": "80.00",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.betrag, Decimal("80.00"))
        eintrag = AuditLog.objects.get(aktion="Beitragsposten geändert")
        self.assertEqual(eintrag.alt_wert, "95.00")
        self.assertEqual(eintrag.neu_wert, "80.00")
        self.assertEqual(eintrag.member, self.member)
