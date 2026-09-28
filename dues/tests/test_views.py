"""Beitragslauf in der Oberfläche (PRD M2.2) — Zugriff, Vorschau, Ausführung."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase

from dues.models import FeeAmount, FeeCategory, FeePost
from members.models import Member

LISTE = "/beitraege/"
LAUF = "/beitraege/lauf/"


def make_user(username, group_name):
    user = User.objects.create_user(username, password="x")
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


class ZugriffTests(TestCase):
    """Beiträge sind Vorstandssache (PRD §3.8)."""

    def setUp(self):
        self.admin = make_user("vorstand", "admin")

    def test_admin_darf_die_postenliste_sehen(self):
        self.client.force_login(self.admin)

        response = self.client.get(LISTE)

        self.assertEqual(response.status_code, 200)

    def test_mitglied_erhaelt_403_auf_der_postenliste(self):
        user = make_user("mitglied", "mitglied")
        self.client.force_login(user)

        response = self.client.get(LISTE)

        self.assertEqual(response.status_code, 403)

    def test_kapitaen_erhaelt_403_auf_der_postenliste(self):
        user = make_user("kapitaen", "kapitaen")
        self.client.force_login(user)

        response = self.client.get(LISTE)

        self.assertEqual(response.status_code, 403)

    def test_gast_wird_zum_anmelden_umgeleitet(self):
        response = self.client.get(LISTE)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response["Location"])

    def test_mitglied_erhaelt_403_beim_lauf(self):
        """Negativtest: der verweigerte Zugriff darf keine Posten erzeugen."""
        user = make_user("mitglied", "mitglied")
        make_member(kategorie("erwachsene"))
        self.client.force_login(user)

        response = self.client.post(LAUF, {"jahr": 2027})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(FeePost.objects.count(), 0)

    def test_beitragslauf_ist_nur_per_post_ausloesbar(self):
        """Negativtest: kein Auslösen per GET/Link (Buchung ohne Klick-Bestätigung)."""
        self.client.force_login(self.admin)

        response = self.client.get(LAUF)

        self.assertEqual(response.status_code, 405)


class PostenListeTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user("vorstand", "admin"))
        self.erwachsene = kategorie("erwachsene")

    def test_zeigt_die_posten_des_gewahlten_jahres(self):
        member = make_member(self.erwachsene)
        FeePost.objects.create(
            member=member, jahr=2027, kategorie=self.erwachsene,
            betrag=Decimal("95.00"),
        )

        response = self.client.get(LISTE, {"jahr": 2027})

        self.assertEqual(list(response.context["posts"]), [FeePost.objects.get()])
        self.assertContains(response, "Meier")

    def test_jahr_query_parameter_wechselt_den_jahrgang(self):
        make_member(self.erwachsene)
        FeePost.objects.create(
            member=make_member(self.erwachsene, vorname="Bernd", nachname="Schmidt"),
            jahr=2026, kategorie=self.erwachsene, betrag=Decimal("90.00"),
        )

        response = self.client.get(LISTE, {"jahr": 2027})

        self.assertEqual(response.context["jahr"], 2027)
        self.assertEqual(list(response.context["posts"]), [])

    def test_zeigt_die_vorschau_mit_anzahl_und_summe(self):
        make_member(self.erwachsene)
        make_member(kategorie("jugend"), vorname="Bernd", nachname="Schmidt")

        response = self.client.get(LISTE, {"jahr": 2027})

        self.assertEqual(response.context["plan"].anzahl_neu, 2)
        self.assertEqual(response.context["plan"].summe_neu, Decimal("142.00"))

    def test_betraege_werden_im_deutschen_format_angezeigt(self):
        make_member(self.erwachsene)

        response = self.client.get(LISTE, {"jahr": 2027})

        self.assertContains(response, "95,00")

    def test_vorschau_erzeugt_keinen_posten(self):
        make_member(self.erwachsene)

        self.client.get(LISTE, {"jahr": 2027})

        self.assertEqual(FeePost.objects.count(), 0)

    def test_meldet_fehlende_saetze_und_blockiert_den_lauf(self):
        """Negativtest: ohne Satz für das Jahr gibt es keine Ausführen-Schaltfläche."""
        make_member(kategorie("jugend"))

        response = self.client.get(LISTE, {"jahr": 2028})

        self.assertContains(response, "Jugendliche")
        self.assertNotContains(response, f'action="{LAUF}"')

    def test_zeigt_mitglieder_ohne_kategorie_als_uebersprungen(self):
        make_member(kategorie=None)

        response = self.client.get(LISTE, {"jahr": 2027})

        self.assertEqual(len(response.context["plan"].uebersprungen), 1)

    def test_bucht_fuer_ein_jahr_ohne_kategorie_keine_0_euro_posten(self):
        """Negativtest: statt eines 0-€-Postens erscheint der Hinweis."""
        make_member(kategorie=None)

        response = self.client.get(LISTE, {"jahr": 2027})

        self.assertEqual(list(response.context["posts"]), [])
        self.assertContains(response, "ohne Kategorie")

    def test_ohne_jahr_parameter_wird_das_laufjahr_gewahlt(self):
        response = self.client.get(LISTE)

        self.assertEqual(response.context["jahr"], date.today().year)

    def test_ungueltiges_jahr_fuehrt_zur_uebersicht_zurueck(self):
        """Negativtest: eine kaputte Jahr-Angabe landet nicht in einer Abfrage."""
        response = self.client.get(LISTE, {"jahr": "kein-jahr"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], LISTE)


class LaufAusfuehrenTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user("vorstand", "admin"))
        self.erwachsene = kategorie("erwachsene")

    def _lauf(self, follow=False, **daten):
        daten.setdefault("jahr", 2027)
        return self.client.post(LAUF, daten, follow=follow)

    def test_lauf_legt_die_posten_an(self):
        make_member(self.erwachsene)
        make_member(self.erwachsene, vorname="Bernd", nachname="Schmidt")

        self._lauf()

        self.assertEqual(FeePost.objects.filter(jahr=2027).count(), 2)

    def test_lauf_meldet_anzahl_und_summe(self):
        make_member(self.erwachsene)

        response = self._lauf(follow=True)

        self.assertContains(response, "1")
        self.assertContains(response, "95,00")

    def test_lauf_zeigt_das_ergebnis_des_gewahlten_jahres(self):
        make_member(self.erwachsene)

        response = self._lauf(follow=True)

        self.assertEqual(response.context["jahr"], 2027)

    def test_zweiter_lauf_meldet_dass_nichts_neues_entstanden(self):
        make_member(self.erwachsene)
        self._lauf()

        response = self._lauf(follow=True)

        self.assertEqual(FeePost.objects.filter(jahr=2027).count(), 1)
        self.assertContains(response, "nichts")

    def test_passiv_werden_nur_auf_wunsch_gebucht(self):
        make_member(self.erwachsene, status=Member.Status.PASSIV)

        self._lauf()

        self.assertEqual(FeePost.objects.count(), 0)

    def test_passiv_werden_mit_aktivem_schalter_gebucht(self):
        make_member(self.erwachsene, status=Member.Status.PASSIV)

        self._lauf(passiv="1")

        self.assertEqual(FeePost.objects.count(), 1)

    def test_fehlender_satz_bricht_ab_und_bucht_nichts(self):
        """Negativtest: die Abbruchmeldung nennt die Kategorie, es entsteht kein 0-€-Posten."""
        make_member(self.erwachsene)
        make_member(kategorie("jugend"), vorname="Bernd", nachname="Schmidt")
        FeeAmount.objects.filter(kategorie__code="jugend", jahr=2027).delete()

        response = self._lauf(follow=True)

        self.assertEqual(FeePost.objects.count(), 0)
        self.assertContains(response, "Jugendliche")

    def test_ausgetretenes_mitglied_wird_nicht_gebucht(self):
        make_member(
            self.erwachsene,
            status=Member.Status.AUSGETRETEN,
            austrittsdatum=date(2026, 3, 1),
        )

        self._lauf(passiv="1")

        self.assertEqual(FeePost.objects.count(), 0)
