"""Beitragslauf (PRD M2.2) — Tests für den Lauf-Service in `dues/services.py`."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from dues.models import FeeAmount, FeeCategory, FeePost
from dues.services import fuehre_lauf, plan_lauf
from members.models import Member


def make_user(username, group_name=None):
    user = User.objects.create_user(username, password="x")
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


def make_member(kategorie=None, **kwargs):
    defaults = {
        "vorname": "Anna",
        "nachname": "Meier",
        "eintrittsdatum": date(2020, 1, 15),
    }
    if kategorie is not None:
        defaults["beitragskategorie"] = kategorie
    defaults.update(kwargs)
    return Member.objects.create(**defaults)


def kategorie(code):
    return FeeCategory.objects.get(code=code)


class PlanTests(TestCase):
    """Die Vorschau zeigt, was ein Lauf tun würde — und legt nichts an."""

    def setUp(self):
        self.erwachsene = kategorie("erwachsene")
        self.jugend = kategorie("jugend")

    def test_plan_enthaelt_aktive_mitglieder_mit_kategorie(self):
        member = make_member(self.erwachsene)

        plan = plan_lauf(2027)

        self.assertEqual([posten.member for posten in plan.posten], [member])

    def test_plan_nimmt_den_satz_der_kategorie_fuer_das_jahr(self):
        make_member(self.erwachsene)

        plan = plan_lauf(2027)

        self.assertEqual(plan.posten[0].betrag, Decimal("95.00"))
        self.assertEqual(plan.posten[0].kategorie, self.erwachsene)

    def test_plan_summiert_die_neu_zu_buchenden_betraege(self):
        make_member(self.erwachsene)
        make_member(self.jugend, vorname="Bernd", nachname="Schmidt")

        plan = plan_lauf(2027)

        self.assertEqual(plan.summe_neu, Decimal("142.00"))

    def test_plan_bucht_keinen_posten_fuer_mitglied_ohne_kategorie(self):
        make_member(kategorie=None)

        plan = plan_lauf(2027)

        self.assertEqual(plan.posten, [])

    def test_plan_meldet_mitglieder_ohne_kategorie_als_uebersprungen(self):
        member = make_member(kategorie=None)

        plan = plan_lauf(2027)

        self.assertEqual(plan.uebersprungen, [member])

    def test_plan_ueberspringt_ausgetretene_mitglieder(self):
        """Negativtest: Restkategorie eines ausgetretenen Mitglieds wird nie gebucht."""
        make_member(
            self.erwachsene,
            status=Member.Status.AUSGETRETEN,
            austrittsdatum=date(2026, 3, 1),
        )

        plan = plan_lauf(2027)

        self.assertEqual(plan.posten, [])

    def test_plan_ueberspringt_passive_mitglieder_standardmaessig(self):
        member = make_member(self.erwachsene, status=Member.Status.PASSIV)

        plan = plan_lauf(2027)

        self.assertEqual(plan.posten, [])
        # Ohne diesen Hinweis wäre das Ergebnis nicht von „alle gebucht"
        # unterscheidbar — der Schalter im Lauf-Dialog wäre eine Falle.
        self.assertEqual(plan.passiv_ausgenommen, [member])

    def test_plan_bezieht_passive_mitglieder_auf_wunsch_ein(self):
        member = make_member(self.erwachsene, status=Member.Status.PASSIV)

        plan = plan_lauf(2027, passiv_einbezogen=True)

        self.assertEqual([posten.member for posten in plan.posten], [member])
        self.assertEqual(plan.passiv_ausgenommen, [])

    def test_plan_meldet_kategorie_ohne_satz_fuer_das_jahr(self):
        """Negativtest: statt eines 0-€-Postens wird der fehlende Satz gemeldet."""
        make_member(self.jugend)

        plan = plan_lauf(2028)

        self.assertEqual(plan.fehlende_saetze, [self.jugend])

    def test_plan_wird_nicht_durch_die_vorschau_ausgefuehrt(self):
        make_member(self.erwachsene)

        plan_lauf(2027)

        self.assertEqual(FeePost.objects.count(), 0)

    def test_plan_zaehlt_bereits_buchbare_posten_separat(self):
        make_member(self.erwachsene)
        make_member(self.jugend, vorname="Bernd", nachname="Schmidt")
        FeePost.objects.create(
            member=Member.objects.get(nachname="Schmidt"),
            jahr=2027,
            kategorie=self.jugend,
            betrag=Decimal("47.00"),
        )

        plan = plan_lauf(2027)

        self.assertEqual(len(plan.posten), 1)
        self.assertEqual(plan.anzahl_vorhanden, 1)
        self.assertEqual(plan.summe_gesamt, Decimal("142.00"))


class LaufTests(TestCase):
    """Der Lauf erzeugt genau einen Posten je Mitglied und Jahr (PRD M2.2)."""

    def setUp(self):
        self.erwachsene = kategorie("erwachsene")

    def test_lauf_legt_je_mitglied_einen_posten_an(self):
        """Akzeptanz laut Plan T8: 10 Testmitglieder → 10 Posten."""
        for index in range(10):
            make_member(self.erwachsene, vorname=f"Mitglied{index}")

        plan = fuehre_lauf(2027)

        self.assertEqual(len(plan.posten), 10)
        self.assertEqual(FeePost.objects.filter(jahr=2027).count(), 10)

    def test_lauf_uebernimmt_die_kategorie_und_den_betrag(self):
        make_member(self.erwachsene)

        fuehre_lauf(2027)

        post = FeePost.objects.get(jahr=2027)
        self.assertEqual(post.kategorie, self.erwachsene)
        self.assertEqual(post.betrag, Decimal("95.00"))

    def test_zweiter_lauf_erzeugt_nichts_zusaetzlich(self):
        """Akzeptanz laut Plan T8: zweiter Lauf → weiterhin 10 Posten."""
        for index in range(10):
            make_member(self.erwachsene, vorname=f"Mitglied{index}")

        fuehre_lauf(2027)
        plan = fuehre_lauf(2027)

        self.assertEqual(plan.posten, [])
        self.assertEqual(FeePost.objects.filter(jahr=2027).count(), 10)

    def test_zweiter_lauf_ergaenzt_nur_fehlende_posten(self):
        """Ein später beigetretenes Mitglied bekommt seinen Posten nachgezogen."""
        make_member(self.erwachsene)
        fuehre_lauf(2027)
        spaeter = make_member(self.erwachsene, vorname="Bernd", nachname="Schmidt")

        plan = fuehre_lauf(2027)

        self.assertEqual([posten.member for posten in plan.posten], [spaeter])
        self.assertEqual(FeePost.objects.filter(jahr=2027).count(), 2)

    def test_lauf_braucht_fuer_jedes_mitglied_genau_einen_posten_pro_jahr(self):
        member = make_member(self.erwachsene)
        FeePost.objects.create(
            member=member, jahr=2027, kategorie=self.erwachsene,
            betrag=Decimal("95.00"),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FeePost.objects.create(
                    member=member, jahr=2027, kategorie=self.erwachsene,
                    betrag=Decimal("95.00"),
                )

    def test_buchter_betrag_bleibt_bei_spaeterer_satzaenderung_erhalten(self):
        """Der Posten ist ein Finanznachweis: eine Satzänderung darf ihn nicht überschreiben."""
        make_member(self.erwachsene)
        fuehre_lauf(2027)
        FeeAmount.objects.filter(kategorie=self.erwachsene, jahr=2027).update(
            betrag=Decimal("120.00")
        )

        self.assertEqual(FeePost.objects.get(jahr=2027).betrag, Decimal("95.00"))


class FehlenderSatzTests(TestCase):
    """Ohne Satz für das Laufjahr bricht der Lauf ab — ohne Teilbuchung (T7-Hinweis)."""

    def setUp(self):
        self.jugend = kategorie("jugend")
        self.erwachsene = kategorie("erwachsene")

    def test_lauf_bricht_mit_klarer_meldung_ab(self):
        make_member(self.jugend)

        with self.assertRaises(ValidationError) as ctx:
            fuehre_lauf(2028)

        self.assertIn("Jugendliche", ctx.exception.messages[0])
        self.assertIn("2028", ctx.exception.messages[0])

    def test_lauf_bricht_ab_wenn_nur_eine_kategorie_fehlt(self):
        make_member(self.erwachsene)
        make_member(self.jugend, vorname="Bernd", nachname="Schmidt")
        FeeAmount.objects.filter(kategorie=self.jugend, jahr=2027).delete()

        with self.assertRaises(ValidationError) as ctx:
            fuehre_lauf(2027)

        self.assertEqual(FeePost.objects.count(), 0)
        self.assertIn("Jugendliche", ctx.exception.messages[0])

    def test_lauf_bricht_nicht_wenn_alle_kategorien_einen_satz_haben(self):
        make_member(self.jugend)

        plan = fuehre_lauf(2027)

        self.assertEqual(len(plan.posten), 1)


class AuditTests(TestCase):
    """Der Lauf ist eine Sammelaktion und landet deshalb im Audit-Log (PRD M7.3)."""

    def setUp(self):
        from core.models import AuditLog

        self.audit_log = AuditLog
        self.erwachsene = kategorie("erwachsene")

    def test_lauf_wird_mit_benutzer_und_anzahl_protokolliert(self):
        admin = make_user("vorstand", "admin")
        make_member(self.erwachsene)

        fuehre_lauf(2027, benutzer=admin)

        eintrag = self.audit_log.objects.get(aktion="Beitragslauf ausgeführt")
        self.assertEqual(eintrag.benutzer, admin)
        self.assertIn("2027", eintrag.text)
        self.assertIn("1", eintrag.text)

    def test_lauf_ohne_neue_posten_protokolliert_nichts(self):
        """Kein Log-Rauschen: ein zweiter Lauf ohne Änderung ist keine Aktion."""
        admin = make_user("vorstand", "admin")
        make_member(self.erwachsene)
        fuehre_lauf(2027, benutzer=admin)

        fuehre_lauf(2027, benutzer=admin)

        self.assertEqual(
            self.audit_log.objects.filter(aktion="Beitragslauf ausgeführt").count(), 1
        )
