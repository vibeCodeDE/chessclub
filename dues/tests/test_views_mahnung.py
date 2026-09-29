"""Mahnliste, Mahnformular und Export in der Oberfläche (PRD M2.5)."""

import csv
import io
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from dues.models import FeeCategory, FeePost, Mahnung, Payment
from members.models import Member

MAHNLISTE = "/beitraege/mahnungen/"
EXPORT = "/beitraege/export.csv"


def make_user(username, group_name):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


def make_member(nachname="Meier", vorname="Anna", kategorie=None):
    return Member.objects.create(
        vorname=vorname,
        nachname=nachname,
        eintrittsdatum=date(2020, 1, 15),
        beitragskategorie=kategorie,
    )


def make_post(member=None, jahr=2026, betrag="90.00", kategorie=None):
    # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create holt
    # ihn im Testlauf, statt am unique-Slug zu scheitern.
    kategorie = kategorie or FeeCategory.objects.get_or_create(
        code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
    )[0]
    member = member or make_member(kategorie=kategorie)
    return FeePost.objects.create(
        member=member, jahr=jahr, kategorie=kategorie, betrag=Decimal(betrag)
    )


def zahle(post, betrag="90.00"):
    return Payment.objects.create(
        post=post, betrag=Decimal(betrag), art=Payment.Art.BAR
    )


class MahnlisteZugriffTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.post = make_post()

    def setz_url(self):
        return reverse("dues:mahnung_setzen", args=[self.post.pk])

    def gueltiger_body(self):
        """Vollständiger POST-Body.

        Bewusst mit gesetzter Stufe: ein Body ohne ``stufe`` ließe den View auch
        ohne Rollenprüfung an „Unbekannte Mahnstufe." scheitern — der
        Negativtest liefe dann aus dem falschen Grund grün und würde nichts
        über die Rollenprüfung aussagen.
        """
        return {"stufe": "1", "datum": "2026-03-01"}

    def test_admin_darf_die_mahnliste_sehen(self):
        self.client.force_login(self.admin)

        response = self.client.get(MAHNLISTE)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Offene Beiträge")

    def test_mitglied_erhaelt_403(self):
        self.client.force_login(make_user("mitglied", "mitglied"))

        liste = self.client.get(MAHNLISTE)
        post = self.client.post(self.setz_url(), self.gueltiger_body())

        self.assertEqual(liste.status_code, 403)
        self.assertEqual(post.status_code, 403)

    def test_kapitaen_erhaelt_403(self):
        self.client.force_login(make_user("kapitaen", "kapitaen"))

        liste = self.client.get(MAHNLISTE)
        post = self.client.post(self.setz_url(), self.gueltiger_body())

        self.assertEqual(liste.status_code, 403)
        self.assertEqual(post.status_code, 403)

    def test_gast_wird_zum_anmelden_umgeleitet(self):
        liste = self.client.get(MAHNLISTE)
        post = self.client.post(self.setz_url(), self.gueltiger_body())

        self.assertEqual(liste.status_code, 302)
        self.assertIn("/anmelden/", liste["Location"])
        self.assertEqual(post.status_code, 302)
        self.assertIn("/anmelden/", post["Location"])

    def test_403_erzeugt_keine_mahnung(self):
        """Negativtest: der verweigerte Zugriff darf nichts schreiben."""
        self.client.force_login(make_user("mitglied", "mitglied"))

        response = self.client.post(self.setz_url(), self.gueltiger_body())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Mahnung.objects.count(), 0)


class MahnlisteInhaltTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]

    def test_offener_posten_erscheint_mit_summe(self):
        make_post(kategorie=self.kategorie)

        response = self.client.get(MAHNLISTE)

        self.assertEqual(response.context["summe_offen"], Decimal("90.00"))
        self.assertContains(response, "Meier")
        self.assertContains(response, "1. Mahnung")

    def test_bezahlter_posten_erscheint_nicht(self):
        post = make_post(kategorie=self.kategorie)
        zahle(post)

        response = self.client.get(MAHNLISTE)

        self.assertEqual(response.context["zeilen"], [])
        self.assertEqual(response.context["summe_offen"], Decimal("0.00"))

    def test_jahr_ohne_lauf_zeigt_hinweis_statt_crash(self):
        response = self.client.get(MAHNLISTE)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Für dieses Jahr wurden keine Beiträge gebucht.")

    def test_jahresfilter_zeigt_das_gewahlte_jahr(self):
        make_post(kategorie=self.kategorie)
        response = self.client.get(MAHNLISTE, {"jahr": "2026"})

        self.assertEqual(response.context["jahr"], 2026)
        self.assertEqual(len(response.context["zeilen"]), 1)

    def test_unlesbares_jahr_zeigt_das_aktuelle(self):
        ungefolgt = self.client.get(MAHNLISTE, {"jahr": "keinjahr"})
        # follow=True holt genau die Seite, die der Vorstand nach der Umleitung
        # sieht — der erste Aufruf belegt zusätzlich, dass überhaupt umgeleitet
        # wird und nicht still ein Ersatzjahr gerendert wird.
        response = self.client.get(MAHNLISTE, {"jahr": "keinjahr"}, follow=True)

        self.assertEqual(ungefolgt.status_code, 302)
        self.assertEqual(ungefolgt["Location"], MAHNLISTE)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jahr"], date.today().year)

    def test_mahnbutton_nur_wenn_noch_eine_stufe_frei_ist(self):
        post = make_post(kategorie=self.kategorie)

        response = self.client.get(MAHNLISTE)
        self.assertContains(response, "/setzen/")

        Mahnung.objects.create(post=post, stufe=1, datum=date(2026, 3, 1))
        Mahnung.objects.create(post=post, stufe=2, datum=date(2026, 4, 1))

        response = self.client.get(MAHNLISTE)
        self.assertNotContains(response, "/setzen/")

    def test_bisherige_mahnungen_werden_angezeigt(self):
        post = make_post(kategorie=self.kategorie)
        Mahnung.objects.create(post=post, stufe=1, datum=date(2026, 3, 1))

        response = self.client.get(MAHNLISTE)

        # Das Template formatiert das Datum deutsch, nicht als ISO-String.
        self.assertContains(response, "01.03.2026")
        self.assertContains(response, "1. Mahnung am 01.03.2026")

    def test_mahnliste_verweist_auf_den_mahnbrief(self):
        """Der Mahnbrief-Link muss auf der Mahnliste stehen.

        Ohne diesen Test verschwindet er still wieder: die Route fehlte in
        Task 6, und ein nicht auflösbares {% url %} schlägt bei DJANGO_DEBUG=1
        die ganze Seite fehl, statt nur den Link.
        """
        post = make_post(kategorie=self.kategorie)

        response = self.client.get(MAHNLISTE)

        self.assertContains(
            response, f'href="{reverse("dues:mahnbrief", args=[post.pk])}"'
        )


class MahnbriefPlatzhalterTests(TestCase):
    """Der Platzhalter, den Task 7 ersetzt — hier nur, dass er trägt."""

    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.post = make_post()

    def url(self):
        return reverse("dues:mahnbrief", args=[self.post.pk])

    def test_admin_bekommt_die_briefseite(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meier")

    def test_mitglied_erhaelt_403(self):
        self.client.force_login(make_user("mitglied", "mitglied"))

        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 403)

    def test_unbekannter_posten_ergibt_404(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("dues:mahnbrief", args=[999999]))

        self.assertEqual(response.status_code, 404)


class MahnungSetzenTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.post = make_post()

    def url(self):
        return reverse("dues:mahnung_setzen", args=[self.post.pk])

    def test_setzt_die_mahnung_und_leitet_auf_die_liste(self):
        response = self.client.post(
            self.url(), {"stufe": "1", "datum": "2026-03-01", "frist": "2026-04-01"}
        )

        mahnung = Mahnung.objects.get()
        self.assertEqual(mahnung.post, self.post)
        self.assertEqual(mahnung.stufe, 1)
        self.assertEqual(mahnung.datum, date(2026, 3, 1))
        self.assertEqual(mahnung.frist, date(2026, 4, 1))
        self.assertEqual(mahnung.erstellt_von, self.admin)
        self.assertRedirects(
            response, f"{MAHNLISTE}?jahr=2026", fetch_redirect_response=False
        )

    def test_ohne_frist_wird_keine_frist_gespeichert(self):
        self.client.post(self.url(), {"stufe": "1", "datum": "2026-03-01"})

        self.assertIsNone(Mahnung.objects.get().frist)

    def test_notiz_wird_uebernommen(self):
        self.client.post(
            self.url(),
            {"stufe": "1", "datum": "2026-03-01", "notiz": "Rückruf vereinbart"},
        )

        self.assertEqual(Mahnung.objects.get().notiz, "Rückruf vereinbart")

    def test_get_ist_nicht_erlaubt(self):
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_uebersprungene_stufe_wird_abgelehnt(self):
        response = self.client.post(self.url(), {"stufe": "2", "datum": "2026-03-01"})

        self.assertEqual(Mahnung.objects.count(), 0)
        self.assertEqual(response.status_code, 302)
        # Die View leitet auf die Liste des Jahres um — dort steht die Meldung.
        self.assertEqual(response["Location"], f"{MAHNLISTE}?jahr=2026")
        # Die Nadel stammt aus der Ablehnung in dues.mahnung.mahnungen_setzen.
        # „1. Mahnung" als Nadel wäre vakuos: das rendert der Listen-Knopf auf
        # jeder Zeile und bliebe auch ohne messages.error grün.
        self.assertContains(
            self.client.get(response["Location"]), "kann nicht gesetzt werden"
        )

    def test_bezahlter_posten_wird_abgelehnt(self):
        zahle(self.post)

        self.client.post(self.url(), {"stufe": "1", "datum": "2026-03-01"})

        self.assertEqual(Mahnung.objects.count(), 0)

    def test_unlesbares_datum_wird_abgelehnt(self):
        response = self.client.post(
            self.url(), {"stufe": "1", "datum": "kein-datum"}, follow=True
        )

        self.assertEqual(Mahnung.objects.count(), 0)
        # Die Nadel stammt aus der Ablehnung in dues.mahnung.mahnungen_setzen.
        # „Mahndatum" als Nadel wäre vakuos: das steht im aria-label jedes
        # Datumsfeldes der Liste und bliebe ohne messages.error grün.
        self.assertContains(response, "Bitte ein gültiges Mahndatum")

    def test_unbekannter_posten_ergibt_404(self):
        response = self.client.post(
            reverse("dues:mahnung_setzen", args=[999999]),
            {"stufe": "1", "datum": "2026-03-01"},
        )

        self.assertEqual(response.status_code, 404)


class ExportViewTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]
        # Ohne ?jahr= exportiert die View das aktuelle Jahr; ein festes Jahr im
        # Test wäre eine Zeitbombe, die zum Jahreswechsel fehlschlägt.
        self.jahr = date.today().year

    def test_export_ist_eine_csv_datei(self):
        make_post(kategorie=self.kategorie, jahr=self.jahr)

        response = self.client.get(EXPORT)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(f"beitraege_{self.jahr}.csv", response["Content-Disposition"])

    def test_export_ist_bom_und_semikolon(self):
        make_post(kategorie=self.kategorie, jahr=self.jahr)

        inhalt = self.client.get(EXPORT).content.decode("utf-8")

        self.assertTrue(inhalt.startswith("\ufeff"))
        self.assertIn("Nachname;Vorname", inhalt)

    def test_export_ist_lesbar_und_komplett(self):
        make_post(kategorie=self.kategorie, jahr=self.jahr)
        Mahnung.objects.create(
            post=FeePost.objects.get(), stufe=1, datum=date(2026, 3, 1)
        )

        inhalt = self.client.get(EXPORT).content.decode("utf-8")
        zeilen = list(csv.reader(io.StringIO(inhalt.lstrip("\ufeff")), delimiter=";"))

        self.assertEqual(zeilen[0][0], "Jahr")
        self.assertEqual(zeilen[1][0], str(self.jahr))
        self.assertEqual(len(zeilen), 2)

    def test_zwei_exporte_sind_identisch(self):
        make_post(kategorie=self.kategorie, jahr=self.jahr)

        erster = self.client.get(EXPORT).content
        zweiter = self.client.get(EXPORT).content

        self.assertEqual(erster, zweiter)

    def test_jahr_aus_der_querystring(self):
        make_post(kategorie=self.kategorie, jahr=2027)

        response = self.client.get(EXPORT, {"jahr": "2027"})

        self.assertIn("beitraege_2027.csv", response["Content-Disposition"])

    def test_unlesbares_jahr_wird_umgeleitet_statt_geraten(self):
        """Gleiches Verhalten wie mahnliste und posten_liste.

        Sonst bekäme der Vorstand still den Export des falschen Jahres — bei
        einer Datei, die danach in der Buchhaltung landet, ist Raten zu teuer.
        """
        make_post(kategorie=self.kategorie, jahr=self.jahr)

        response = self.client.get(EXPORT, {"jahr": "keinjahr"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], MAHNLISTE)

    def test_mitglied_erhaelt_403_und_keine_datei(self):
        self.client.force_login(make_user("mitglied", "mitglied"))
        make_post(kategorie=self.kategorie, jahr=self.jahr)

        response = self.client.get(EXPORT)

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("text/csv", response.get("Content-Type", ""))

