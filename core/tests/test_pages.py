"""Seiten-Smoke-Tests: alle Kernseiten laden und Rollen greifen wie geplant."""

from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase

from dues.models import FeeCategory, MembershipFee
from members.models import Member
from teams.models import LeagueMatch, Team
from tournaments.models import Tournament


def make_user(username, group_name=None, staff=False):
    user = User.objects.create_user(username, password="x", is_staff=staff, is_superuser=staff)
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


def make_member(nachname="Meier", vorname="Anna", user=None, **kwargs):
    daten = {
        "vorname": vorname,
        "nachname": nachname,
        "eintrittsdatum": date(2020, 1, 15),
        "email": "anna@example.org",
        "status": Member.Status.AKTIV,
        "user": user,
    }
    daten.update(kwargs)
    return Member.objects.create(**daten)


class AdminSeitenTests(TestCase):
    """Jede Vorstandsseite muss ohne Fehler rendern (leere Datenbank = Leerzustände)."""

    def setUp(self):
        self.admin = make_user("vorstand", "admin", staff=True)
        self.client.force_login(self.admin)
        self.member = make_member()
        self.team = Team.objects.create(name="1. Mannschaft", liga="Kreisliga", brettanzahl=4)
        self.match = LeagueMatch.objects.create(
            team=self.team, datum=date(2026, 10, 3), gegner="SV Test", brettanzahl=4
        )
        self.turnier = Tournament.objects.create(
            name="Testturnier", datum=date(2026, 11, 1), status=Tournament.Status.ANMELDUNG
        )
        self.kategorie = FeeCategory.objects.create(name="Erwachsene", betrag="90.00")
        self.fee = MembershipFee.objects.create(
            member=self.member,
            jahr=2026,
            kategorie_name="Erwachsene",
            betrag="90.00",
            faellig_am=date(2026, 1, 31),
        )

    def test_alle_seiten_laden(self):
        urls = [
            "/",
            "/dashboard/",
            "/aktuelles/",
            "/suche/?q=meier",
            "/audit/",
            "/mitglieder/",
            "/mitglieder/neu/",
            f"/mitglieder/{self.member.pk}/",
            f"/mitglieder/{self.member.pk}/bearbeiten/",
            "/mitglieder/wuensche/",
            "/mitglied-werden/",
            "/profil/",
            "/mein-beitragskonto/",
            "/beitraege/",
            "/beitraege/kategorien/",
            "/beitraege/mandate/",
            "/beitraege/mandate/neu/",
            "/beitraege/mahnwesen/",
            f"/beitraege/posten/{self.fee.pk}/",
            "/mannschaften/",
            f"/mannschaften/{self.team.pk}/",
            "/mannschaften/neu/",
            "/spiele/",
            f"/spiele/{self.match.pk}/",
            "/spiele/neu/",
            "/ligen/",
            "/meine-einsaetze/",
            "/turniere/",
            "/turniere/verwalten/",
            "/turniere/verwalten/neu/",
            f"/turniere/verwalten/{self.turnier.pk}/",
            f"/turniere/verwalten/{self.turnier.pk}/druck/",
            "/ankuendigungen/",
            "/ankuendigungen/neu/",
            "/kasse/",
            "/kasse/neu/",
            "/kasse/jahresabschluss/",
            "/health/",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_leerzustaende_werden_angezeigt(self):
        """Ohne Daten erscheinen Hinweise statt leerer Tabellen."""
        response = self.client.get("/ankuendigungen/")
        self.assertContains(response, "Noch keine Ankündigungen")
        response = self.client.get("/beitraege/mandate/")
        self.assertContains(response, "Noch keine Mandate")

    def test_exporte_liefern_csv(self):
        for url in ["/mitglieder/export.csv", "/beitraege/export.csv?jahr=2026", "/kasse/export.csv"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/csv", response["Content-Type"])
                self.assertIn("attachment", response["Content-Disposition"])


class RollenTests(TestCase):
    """Mitglieder und Kapitäne dürfen keine Vorstandsseiten sehen (403)."""

    def setUp(self):
        self.member_user = make_user("p1", "mitglied")
        self.kapitaen = make_user("k1", "kapitaen")
        self.mitglied = make_member(user=self.member_user)

    def test_mitglied_wird_abgewiesen(self):
        self.client.force_login(self.member_user)
        for url in ["/mitglieder/", "/beitraege/", "/kasse/", "/turniere/verwalten/", "/audit/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_mitglied_sieht_eigene_seiten(self):
        self.client.force_login(self.member_user)
        for url in ["/dashboard/", "/profil/", "/mein-beitragskonto/", "/meine-einsaetze/", "/turniere/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        # Dashboard der Mitglieder zeigt keine Vorstands-Kacheln
        response = self.client.get("/dashboard/")
        self.assertNotContains(response, "Offene Beiträge")
        self.assertNotContains(response, "Zu erledigen")

    def test_kapitaen_darf_spielbetrieb_nicht_aber_finanzen(self):
        self.client.force_login(self.kapitaen)
        self.assertEqual(self.client.get("/mannschaften/").status_code, 200)
        self.assertEqual(self.client.get("/spiele/").status_code, 200)
        self.assertEqual(self.client.get("/beitraege/").status_code, 403)

    def test_anonyme_landen_auf_login(self):
        for url in ["/dashboard/", "/mitglieder/", "/beitraege/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/anmelden/", response.url)

    def test_oeffentliche_seiten_ohne_login(self):
        self.client.logout()
        for url in ["/", "/aktuelles/", "/turniere/", "/mitglied-werden/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_oeffentliche_turnierseite_zeigt_details(self):
        turnier = Tournament.objects.create(
            name="Offenes Turnier",
            datum=date(2026, 12, 1),
            status=Tournament.Status.ANMELDUNG,
            oeffentlich=True,
            beschreibung="Offen für alle.",
        )
        response = self.client.get(f"/turniere/{turnier.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Offenes Turnier")
        self.assertContains(response, "Ausschreibung")

    def test_entwurf_turnier_ist_nicht_oeffentlich(self):
        turnier = Tournament.objects.create(
            name="Geheim", datum=date(2026, 12, 1), oeffentlich=False
        )
        self.assertEqual(self.client.get(f"/turniere/{turnier.pk}/").status_code, 404)
