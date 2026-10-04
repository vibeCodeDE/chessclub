"""Dashboard: Kennzahlen, Rollen und Badges in der Navigation."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase

from dues.models import FeeAmount, FeeCategory, MembershipFee
from members.models import ChangeRequest, Member
from teams.models import LeagueMatch, Team


def make_user(username, gruppe=None):
    user = User.objects.create_user(username, password="x")
    if gruppe:
        group, _ = Group.objects.get_or_create(name=gruppe)
        user.groups.add(group)
    return user


class VorstandsDashboardTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.kategorie = FeeCategory.objects.create(name="Erwachsene")
        FeeAmount.objects.create(kategorie=self.kategorie, jahr=date.today().year, betrag=Decimal("90.00"))
        self.member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2026, 1, 8),
            beitragskategorie=self.kategorie,
        )
        self.fee = MembershipFee.objects.create(
            member=self.member, jahr=date.today().year, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )

    def test_kennzahlen_im_kontext(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        uebersicht = response.context["uebersicht"]
        self.assertEqual(uebersicht["soll"], Decimal("90.00"))
        self.assertEqual(uebersicht["offen"], Decimal("90.00"))
        self.assertEqual(uebersicht["offene_anzahl"], 1)

    def test_offene_posten_werden_aufgelistet(self):
        response = self.client.get("/dashboard/")
        self.assertContains(response, "Offene Beiträge")
        self.assertContains(response, "Anna")
        self.assertContains(response, "90,00 €")

    def test_zahlung_reduziert_offenen_betrag(self):
        from dues.services import zahlung_erfassen

        zahlung_erfassen(self.fee, betrag=Decimal("90.00"), benutzer=self.admin)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.context["uebersicht"]["offen"], Decimal("0.00"))
        self.assertContains(response, "Alle Beiträge bezahlt")

    def test_offene_wuensche_und_badges(self):
        ChangeRequest.objects.create(
            member=self.member, feld="telefon", wunschwert="030 123", eingereicht_von=self.admin
        )
        response = self.client.get("/dashboard/")
        self.assertContains(response, "Zu erledigen")
        self.assertContains(response, "030 123")
        badges = {
            link["label"]: link["badge"]
            for sektion in response.context["nav_sektionen"]
            for link in sektion["links"]
        }
        self.assertEqual(badges["Änderungswünsche"], 1)
        self.assertEqual(badges["Beiträge"], 1)

    def test_kommende_termine_erscheinen(self):
        team = Team.objects.create(name="1. Mannschaft", liga="Kreisliga", brettanzahl=4)
        LeagueMatch.objects.create(
            team=team, datum=date.today(), gegner="SV Test"
        )
        response = self.client.get("/dashboard/")
        self.assertContains(response, "SV Test")


class KapitaenDashboardTests(TestCase):
    """PRD §3.8: Beiträge, Zahlungen, Mahnungen, Kasse und Audit-Log sind
    Vorstandssache. Der Kapitän sieht Spielbetrieb – und keinen Cent."""

    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.kapitaen = make_user("kapit1", "kapitaen")
        self.client.force_login(self.kapitaen)
        self.kategorie = FeeCategory.objects.create(name="Erwachsene")
        FeeAmount.objects.create(kategorie=self.kategorie, jahr=date.today().year, betrag=Decimal("90.00"))
        self.member = Member.objects.create(
            vorname="Anna", nachname="Meier",
            eintrittsdatum=date(2020, 1, 15), beitragskategorie=self.kategorie,
        )
        self.fee = MembershipFee.objects.create(
            member=self.member, jahr=date.today().year, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )
        self.team = Team.objects.create(
            name="1. Mannschaft",
            liga="Kreisliga",
            brettanzahl=4,
            kapitaen=Member.objects.create(
                vorname="Karl", nachname="Kapitän",
                eintrittsdatum=date(2019, 5, 1), user=self.kapitaen,
            ),
        )

    def test_keine_finanzkachel_und_kein_exportlink(self):
        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Offene Beiträge")
        self.assertNotContains(response, "Beitrags-CSV")
        self.assertNotContains(response, "Beitragslauf")
        self.assertNotContains(response, "Zahlungen im Monat")
        self.assertNotContains(response, "Offene Beitragsposten")
        self.assertNotContains(response, "Kasse")
        self.assertNotContains(response, "/beitraege/export.csv")

    def test_keine_mitgliederliste_und_kein_auditlog(self):
        response = self.client.get("/dashboard/")

        self.assertNotContains(response, self.member.nachname)
        self.assertNotContains(response, "Letzte Aktivitäten")
        self.assertNotContains(response, "Neue Mitglieder")

    def test_keine_finanzdaten_im_kontext(self):
        """Nicht nur nicht angezeigt – die Daten werden gar nicht geladen."""
        response = self.client.get("/dashboard/")

        for schluessel in ("uebersicht", "offene_posten", "kasse", "zahlungen_monat",
                           "letzte_aktivitaeten", "neue_mitglieder", "offene_wuensche"):
            self.assertNotIn(schluessel, response.context)

    def test_spielbetrit_sichtbar(self):
        LeagueMatch.objects.create(team=self.team, datum=date.today(), gegner="SV Test")

        response = self.client.get("/dashboard/")

        self.assertContains(response, "Meine Mannschaften")
        self.assertContains(response, "1. Mannschaft")
        self.assertContains(response, "SV Test")


class MitgliedDashboardTests(TestCase):
    def setUp(self):
        self.user = make_user("p1", "mitglied")
        self.client.force_login(self.user)
        self.member = Member.objects.create(
            vorname="Lena", nachname="Fischer", eintrittsdatum=date(2024, 3, 1), user=self.user
        )

    def test_eigene_beitraege_erscheinen(self):
        MembershipFee.objects.create(
            member=self.member, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meine Beiträge")
        self.assertContains(response, "90,00 €")
        self.assertContains(response, "Offener Beitrag")

    def test_ohne_mitgliedsprofil_kein_fehler(self):
        self.member.delete()
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_mitglied_sieht_keine_fremden_daten(self):
        anderer = Member.objects.create(
            vorname="Fremd", nachname="Person", eintrittsdatum=date(2020, 1, 1)
        )
        MembershipFee.objects.create(
            member=anderer, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )
        response = self.client.get("/dashboard/")
        self.assertNotContains(response, "Fremd")


class AuditSeitenTests(TestCase):
    def test_audit_liste_zeigt_eintraege(self):
        admin = make_user("vorstand", "admin")
        member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 1)
        )
        member._changed_by = admin
        member.telefon = "030 999"
        member.save()
        self.client.force_login(admin)
        response = self.client.get("/audit/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stammdaten geändert")
        self.assertContains(response, "030 999")

    def test_audit_liste_suchfilter(self):
        admin = make_user("vorstand", "admin")
        self.client.force_login(admin)
        m1 = Member.objects.create(vorname="Spezifisch", nachname="Findling", eintrittsdatum=date(2020, 1, 1))
        m2 = Member.objects.create(vorname="Anderer", nachname="Person", eintrittsdatum=date(2020, 1, 1))
        from core.models import AuditLog
        AuditLog.objects.create(benutzer=admin, aktion="Test1", text="Geheimer Treffer", member=m1)
        AuditLog.objects.create(benutzer=admin, aktion="Test2", text="Uninteressant", member=m2)

        resp = self.client.get("/audit/", {"q": "Findling"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Geheimer Treffer")
        self.assertNotContains(resp, "Uninteressant")

    def test_globale_suche_findet_treffer(self):
        admin = make_user("vorstand", "admin")
        Member.objects.create(vorname="Anna", nachname="Suchmeier", eintrittsdatum=date(2020, 1, 1))
        self.client.force_login(admin)
        response = self.client.get("/suche/", {"q": "Suchmeier"})
        self.assertContains(response, "Suchmeier")
        response = self.client.get("/suche/", {"q": "gibtesnicht"})
        self.assertContains(response, "0 Treffer")


class DashboardErweiterungenTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.kategorie = FeeCategory.objects.create(name="Erwachsene")
        FeeAmount.objects.create(kategorie=self.kategorie, jahr=2026, betrag=Decimal("90.00"))

    def test_ohne_kategorie_alert_erscheint(self):
        # Mitglied ohne Kategorie
        Member.objects.create(vorname="Ohne", nachname="Kat", eintrittsdatum=date(2026, 1, 1))
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Handlungsbedarf")
        self.assertContains(resp, "ohne Beitragskategorie")
        self.assertContains(resp, "kategorie=keine")

    def test_dashboard_jahr_parameter(self):
        FeeAmount.objects.create(kategorie=self.kategorie, jahr=2025, betrag=Decimal("80.00"))
        m = Member.objects.create(vorname="Max", nachname="Alt", eintrittsdatum=date(2024, 1, 1), beitragskategorie=self.kategorie)
        MembershipFee.objects.create(member=m, jahr=2025, kategorie_name="Erwachsene", betrag=Decimal("80.00"), faellig_am=date(2025, 1, 31))

        resp = self.client.get("/dashboard/", {"jahr": "2025"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["jahr"], 2025)
        self.assertContains(resp, "Beitragsjahr 2025")

    def test_kein_n_plus_eins_bei_vielen_posten(self):
        # 15 Mitglieder anlegen, um sicherzustellen, dass Queries nicht linear wachsen
        for i in range(15):
            m = Member.objects.create(vorname=f"Vor{i}", nachname=f"Nach{i}", eintrittsdatum=date(2026, 1, 1), beitragskategorie=self.kategorie)
            MembershipFee.objects.create(member=m, jahr=2026, kategorie_name="Erwachsene", betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31))

        # Die View führt exakt 33 Queries aus (konstant, da kein N+1 pro Mitglied/Posten)
        with self.assertNumQueries(33):
            resp = self.client.get("/dashboard/")
            self.assertEqual(resp.status_code, 200)

        # 10 weitere Mitglieder anlegen: Query-Zahl bleibt exakt bei 33 (kein N+1)
        for i in range(15, 25):
            m = Member.objects.create(vorname=f"Vor{i}", nachname=f"Nach{i}", eintrittsdatum=date(2026, 1, 1), beitragskategorie=self.kategorie)
            MembershipFee.objects.create(member=m, jahr=2026, kategorie_name="Erwachsene", betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31))

        with self.assertNumQueries(33):
            resp = self.client.get("/dashboard/")
            self.assertEqual(resp.status_code, 200)
