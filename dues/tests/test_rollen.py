"""Berechtigungsmatrix für das Beitragswesen (PRD §3.8).

Jede Zeile der Matrix, die das Beitragswesen betrifft, bekommt hier einen
Negativtest: Kapitän und Mitglied erhalten 403, nur die Vorstandsgruppe kommt
durch. Die Sicht ``mein_konto`` ist die einzige Beitragsfläche, die ein
Mitglied sehen darf – und auch dort nur die eigenen Daten.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase

from dues.models import FeeAmount, FeeCategory, MembershipFee, SepaMandate
from members.models import Member


def make_user(username, gruppe):
    user = User.objects.create_user(username, f"{username}@example.org", "x")
    user.groups.add(Group.objects.get_or_create(name=gruppe)[0])
    return user


def make_member(user=None, **kwargs):
    daten = {
        "vorname": "Anna",
        "nachname": "Meier",
        "eintrittsdatum": date(2020, 1, 15),
        "email": "anna@example.org",
        "user": user,
    }
    daten.update(kwargs)
    return Member.objects.create(**daten)


class RollenTests(TestCase):
    """Dieselbe URL, einmal je Rolle – das ist die Matrix als Test."""

    @classmethod
    def setUpTestData(cls):
        cls.kategorie = FeeCategory.objects.create(name="Erwachsene")
        FeeAmount.objects.create(kategorie=cls.kategorie, jahr=2026, betrag=Decimal("90.00"))
        cls.gast = make_user("gast", "mitglied")
        cls.mitglied = make_user("mitglied1", "mitglied")
        cls.kapitaen = make_user("kapit1", "kapitaen")
        cls.admin = make_user("admin1", "admin")
        cls.eigenes = make_member(user=cls.mitglied, beitragskategorie=cls.kategorie)
        cls.fremdes = make_member(user=cls.admin, beitragskategorie=cls.kategorie)
        cls.posten = MembershipFee.objects.create(
            member=cls.eigenes,
            jahr=2026,
            kategorie_name=cls.kategorie.name,
            betrag=Decimal("90.00"),
            faellig_am=date(2026, 1, 31),
        )
        SepaMandate.objects.create(
            member=cls.eigenes,
            referenz="MND-ROLLEN-01",
            iban="DE89370400440532013000",
            kontoinhaber="Anna Meier",
            erteilt_am=date(2025, 1, 1),
            status=SepaMandate.Status.AKTIV,
        )
        # Zweiter Posten an einem anderen Mitglied: eigener Jahrgang und eigene
        # Kategorie, damit der Negativtest eindeutig ist.
        cls.fremde_kategorie = FeeCategory.objects.create(name="Ermäßigt")
        FeeAmount.objects.create(kategorie=cls.fremde_kategorie, jahr=2025, betrag=Decimal("60.00"))
        MembershipFee.objects.create(
            member=cls.fremdes,
            jahr=2025,
            kategorie_name=cls.fremde_kategorie.name,
            betrag=Decimal("60.00"),
            faellig_am=date(2025, 1, 31),
        )

    def setUp(self):
        # Rolle je Test einzeln setzen, damit die Matrix-Zeile isoliert bleibt.
        self.client.force_login(self.mitglied)

    def wechsle(self, user):
        self.client.force_login(user)

    def test_uebersicht_nur_vorstand(self):
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.get("/beitraege/")
                self.assertEqual(antwort.status_code, 200 if erlaubt else 403)

    def test_beitragslauf_nur_vorstand(self):
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.post("/beitraege/lauf/", {"jahr": 2027})
                self.assertEqual(antwort.status_code, 302 if erlaubt else 403)

    def test_export_nur_vorstand(self):
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.get("/beitraege/export.csv")
                self.assertEqual(antwort.status_code, 200 if erlaubt else 403)

    def test_sepa_export_nur_vorstand(self):
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.get("/beitraege/sepa-export.xml?jahr=2026")
                self.assertEqual(antwort.status_code, 200 if erlaubt else 403)

    def test_kassenbericht_nur_vorstand(self):
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.get("/beitraege/kassenbericht/")
                self.assertEqual(antwort.status_code, 200 if erlaubt else 403)

    def test_kassenbericht_export_nur_vorstand(self):
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.get("/beitraege/kassenbericht/export.csv")
                self.assertEqual(antwort.status_code, 200 if erlaubt else 403)

    def test_kategorien_nur_vorstand(self):
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.get("/beitraege/kategorien/")
                self.assertEqual(antwort.status_code, 200 if erlaubt else 403)

    def test_mandate_nur_vorstand(self):
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.get("/beitraege/mandate/")
                self.assertEqual(antwort.status_code, 200 if erlaubt else 403)

    def test_mahnwesen_nur_vorstand(self):
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.get("/beitraege/mahnwesen/")
                self.assertEqual(antwort.status_code, 200 if erlaubt else 403)

    def test_mahnung_setzen_nur_vorstand(self):
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.post(
                    f"/beitraege/mahnwesen/{self.posten.pk}/mahnung/", {"notiz": ""}
                )
                self.assertEqual(antwort.status_code in (200, 302), erlaubt)

    def test_mahnbrief_nur_vorstand(self):
        self.wechsle(self.admin)
        self.client.post(f"/beitraege/mahnwesen/{self.posten.pk}/mahnung/", {"notiz": ""})
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.get(f"/beitraege/mahnwesen/{self.posten.pk}/brief/")
                self.assertEqual(antwort.status_code, 200 if erlaubt else 403)

    def test_zahlung_buchen_nur_vorstand(self):
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.post(
                    f"/beitraege/posten/{self.posten.pk}/zahlung/", {"betrag": "90,00"}
                )
                self.assertEqual(antwort.status_code in (200, 302), erlaubt)

    def test_postendetail_nur_vorstand(self):
        for user, erlaubt in (
            (self.mitglied, False),
            (self.kapitaen, False),
            (self.admin, True),
        ):
            with self.subTest(rolle=user.groups.get().name):
                self.wechsle(user)
                antwort = self.client.get(f"/beitraege/posten/{self.posten.pk}/")
                self.assertEqual(antwort.status_code, 200 if erlaubt else 403)

    def test_gaest_bekommt_kein_beitragskonto(self):
        """Negativtest: ohne Anmeldung führt auch das eigene Konto zum Login."""
        self.client.logout()

        antwort = self.client.get("/mein-beitragskonto/")

        self.assertEqual(antwort.status_code, 302)
        self.assertIn("/anmelden/", antwort.url)

    def test_mein_konto_zeigt_nur_eigene_daten(self):
        """Das Konto zeigt den eigenen Posten und nichts von fremden Mitgliedern."""
        self.wechsle(self.mitglied)

        antwort = self.client.get("/mein-beitragskonto/")

        self.assertEqual(antwort.status_code, 200)
        self.assertContains(antwort, "Beitrag 2026")
        # Der Posten des anderen Mitglieds (2025, andere Kategorie) darf nicht
        # in der Sicht des Mitglieds auftauchen.
        self.assertNotContains(antwort, "Beitrag 2025")
        self.assertNotContains(antwort, "Ermäßigt")

    def test_ablehnter_zugriff_aendert_nichts(self):
        """Negativtest mit Wirkung: ein 403 legt keine Zahlung und keinen Mahnabsch an."""
        self.wechsle(self.kapitaen)

        self.client.post(f"/beitraege/posten/{self.posten.pk}/zahlung/", {"betrag": "90,00"})
        self.client.post(
            f"/beitraege/mahnwesen/{self.posten.pk}/mahnung/", {"notiz": "Test"}
        )

        self.posten.refresh_from_db()
        self.assertEqual(self.posten.mahnstufe, 0)
        self.assertEqual(self.posten.zahlungen.count(), 0)
