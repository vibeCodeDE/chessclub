"""Beitragslauf, Zahlungen, Mahnwesen und Mandate."""

import json
from datetime import date
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase

from cashbook.models import CashEntry, jahresabschluss
from core.models import AuditLog
from dues.admin import DunningLetterAdmin, MembershipFeeAdmin, PaymentAdmin
from dues.models import (
    DunningLetter,
    FeeCategory,
    MembershipFee,
    Payment,
    SepaMandate,
    jahres_uebersicht,
)
from dues.services import (
    beitragslauf,
    mahnung_erstellen,
    zahlung_erfassen,
    zahlung_stornieren,
)
from members.models import Member


def make_admin(username="vorstand"):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name="admin")
    user.groups.add(group)
    return user


class BeitragslaufTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.erwachsene = FeeCategory.objects.create(name="Erwachsene", betrag=Decimal("90.00"))
        self.jugend = FeeCategory.objects.create(name="Jugendliche", betrag=Decimal("45.00"))
        for index in range(3):
            Member.objects.create(
                vorname=f"Anna{index}", nachname=f"Meier{index}",
                eintrittsdatum=date(2020, 1, 1), beitragskategorie=self.erwachsene,
            )
        Member.objects.create(
            vorname="Passiv", nachname="Person",
            eintrittsdatum=date(2020, 1, 1), status=Member.Status.PASSIV,
            beitragskategorie=self.erwachsene,
        )
        Member.objects.create(vorname="Ohne", nachname="Kategorie", eintrittsdatum=date(2020, 1, 1))

    def test_lauf_erzeugt_nur_fuer_aktive_mit_kategorie(self):
        ergebnis = beitragslauf(2026)
        self.assertEqual(ergebnis["angelegt"], 3)
        self.assertEqual(ergebnis["summe"], Decimal("270.00"))
        self.assertEqual(ergebnis["ohne_kategorie"], 1)
        self.assertEqual(MembershipFee.objects.filter(jahr=2026).count(), 3)

    def test_lauf_ist_idempotent(self):
        beitragslauf(2026)
        zweiter = beitragslauf(2026)
        self.assertEqual(zweiter["angelegt"], 0)
        self.assertEqual(zweiter["uebersprungen"], 3)
        self.assertEqual(MembershipFee.objects.filter(jahr=2026).count(), 3)

    def test_ajax_lauf_meldet_ergebnis(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/beitraege/lauf/", {"jahr": "2027"}, HTTP_ACCEPT="application/json"
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertIn("3 Posten", daten["message"])


class ZahlungTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 1)
        )
        self.fee = MembershipFee.objects.create(
            member=self.member, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )

    def test_teilzahlung_setzt_status_und_bucht_kasse(self):
        zahlung_erfassen(self.fee, betrag=Decimal("40.00"), benutzer=self.admin)
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.status, MembershipFee.Status.TEILWEISE)
        self.assertEqual(self.fee.offener_betrag, Decimal("50.00"))
        self.assertEqual(self.fee.bezahlter_betrag, Decimal("40.00"))
        eintrag = CashEntry.objects.get()
        self.assertEqual(eintrag.art, CashEntry.Art.EINNAHME)
        self.assertEqual(eintrag.betrag, Decimal("40.00"))
        self.assertEqual(eintrag.kategorie, CashEntry.Kategorie.BEITRAEGE)

    def test_vollzahlung_schliesst_posten(self):
        zahlung_erfassen(self.fee, betrag=Decimal("90.00"), benutzer=self.admin)
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.status, MembershipFee.Status.BEZAHLT)
        self.assertEqual(self.fee.offener_betrag, Decimal("0.00"))
        self.assertEqual(self.fee.fortschritt_prozent, 100)

    def test_ajax_zahlung_aktualisiert_zeile(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/beitraege/posten/{self.fee.pk}/zahlung/",
            {"betrag": "90.00", "datum": "2026-03-01", "art": "ueberweisung", "notiz": "Test"},
            HTTP_ACCEPT="application/json",
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertEqual(daten["patch"][f"[data-fee-open='{self.fee.pk}']"], "0.00 €")
        self.assertEqual(Payment.objects.count(), 1)

    def test_zahlung_validiert_betrag(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/beitraege/posten/{self.fee.pk}/zahlung/",
            {"betrag": "0", "datum": "2026-03-01", "art": "bar"},
            HTTP_ACCEPT="application/json",
        )
        self.assertFalse(json.loads(response.content)["ok"])
        self.assertEqual(Payment.objects.count(), 0)

    def test_storno_vollzahlung_setzt_posten_und_kasse_zurueck(self):
        zahlung = zahlung_erfassen(
            self.fee, betrag=Decimal("90.00"), datum=date(2026, 3, 10), benutzer=self.admin
        )
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.status, MembershipFee.Status.BEZAHLT)

        gegen = zahlung_stornieren(zahlung, grund="Irrläufer", benutzer=self.admin)
        self.fee.refresh_from_db()
        self.assertTrue(zahlung.ist_storniert)
        self.assertTrue(gegen.ist_storno)
        self.assertEqual(gegen.storno_von, zahlung)
        self.assertEqual(gegen.betrag, Decimal("-90.00"))
        self.assertEqual(self.fee.bezahlter_betrag, Decimal("0.00"))
        self.assertEqual(self.fee.offener_betrag, Decimal("90.00"))
        self.assertEqual(self.fee.status, MembershipFee.Status.OFFEN)
        # Kassenbuch hat Original + Gegenbuchung, Saldo = 0.00 €
        self.assertEqual(CashEntry.objects.count(), 2)
        self.assertEqual(jahresabschluss(2026)["saldo"], Decimal("0.00"))
        self.assertTrue(
            AuditLog.objects.filter(aktion="Zahlung storniert", member=self.member).exists()
        )

    def test_storno_teilzahlung_setzt_status_auf_teilweise(self):
        z1 = zahlung_erfassen(self.fee, betrag=Decimal("40.00"), datum=date(2026, 2, 1), benutzer=self.admin)
        z2 = zahlung_erfassen(self.fee, betrag=Decimal("50.00"), datum=date(2026, 3, 1), benutzer=self.admin)
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.status, MembershipFee.Status.BEZAHLT)

        zahlung_stornieren(z2, grund="Rücklastschrift", benutzer=self.admin)
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.status, MembershipFee.Status.TEILWEISE)
        self.assertEqual(self.fee.bezahlter_betrag, Decimal("40.00"))
        self.assertEqual(self.fee.offener_betrag, Decimal("50.00"))
        self.assertFalse(z1.ist_storniert)
        self.assertTrue(z2.ist_storniert)

    def test_storno_ueber_route_und_doppelstorno_schutz(self):
        self.client.force_login(self.admin)
        zahlung = zahlung_erfassen(
            self.fee, betrag=Decimal("90.00"), datum=date(2026, 3, 1), benutzer=self.admin
        )
        response = self.client.post(
            f"/beitraege/zahlung/{zahlung.pk}/storno/",
            {"grund": "Doppelt erfasst"},
            HTTP_ACCEPT="application/json",
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertEqual(daten["patch"][f"[data-fee-open='{self.fee.pk}']"], "90.00 €")
        self.assertEqual(daten["patch"][f"[data-fee-status='{self.fee.pk}']"], "Offen")

        # Zweiter Storno-Versuch schlägt fehl (AJAX + Formular-POST)
        nochmal = self.client.post(
            f"/beitraege/zahlung/{zahlung.pk}/storno/", HTTP_ACCEPT="application/json"
        )
        self.assertFalse(json.loads(nochmal.content)["ok"])
        nochmal_html = self.client.post(f"/beitraege/zahlung/{zahlung.pk}/storno/")
        self.assertRedirects(nochmal_html, f"/beitraege/posten/{self.fee.pk}/")

        gegen = Payment.objects.get(storno_von=zahlung)
        with self.assertRaises(ValidationError):
            zahlung_stornieren(gegen, benutzer=self.admin)


class MahnwesenTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 1)
        )
        self.fee = MembershipFee.objects.create(
            member=self.member, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2025, 1, 31),
        )
        self.client.force_login(self.admin)

    def test_mahnung_erhoeht_stufe_bis_zwei(self):
        mahnung_erstellen(self.fee, gebuehr=Decimal("5.00"), benutzer=self.admin)
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.mahnstufe, 1)
        self.assertIsNotNone(self.fee.letzte_mahnung_am)

        mahnung_erstellen(self.fee, gebuehr=Decimal("5.00"), benutzer=self.admin)
        mahnung_erstellen(self.fee, gebuehr=Decimal("5.00"), benutzer=self.admin)
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.mahnstufe, 2, "Mehr als zwei Mahnstufen sind nicht vorgesehen")
        self.assertEqual(DunningLetter.objects.count(), 3)

    def test_ajax_mahnung_und_uebersicht(self):
        response = self.client.post(
            f"/beitraege/mahnwesen/{self.fee.pk}/mahnung/",
            {"gebuehr": "5.00", "notiz": "Erinnerung"},
            HTTP_ACCEPT="application/json",
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertEqual(daten["patch"][f"[data-mahnstufe='{self.fee.pk}']"], "1. Mahnung")

        uebersicht = self.client.get("/beitraege/mahnwesen/")
        self.assertContains(uebersicht, "Anna")
        self.assertContains(uebersicht, "Mahnprotokoll")

    def test_mahnbrief_ist_druckbar(self):
        mahnung_erstellen(self.fee, benutzer=self.admin)
        response = self.client.get(f"/beitraege/mahnwesen/{self.fee.pk}/brief/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1. Mahnung")
        self.assertContains(response, "90,00 €")
        self.assertContains(response, "Meier")

    def test_bezahlter_posten_kann_nicht_gemahnt_werden(self):
        zahlung_erfassen(self.fee, betrag=Decimal("90.00"), benutzer=self.admin)
        response = self.client.post(
            f"/beitraege/mahnwesen/{self.fee.pk}/mahnung/", {}, HTTP_ACCEPT="application/json"
        )
        self.assertFalse(json.loads(response.content)["ok"])


class MandatTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 1)
        )
        self.client.force_login(self.admin)

    def test_mandat_wird_maskiert_angezeigt(self):
        SepaMandate.objects.create(
            member=self.member, referenz="SCKS-2026-001",
            iban="DE89 3704 0044 0532 0130 00", erteilt_am=date(2026, 1, 5),
        )
        response = self.client.get("/beitraege/mandate/")
        inhalt = response.content.decode()
        self.assertIn("SCKS-2026-001", inhalt)
        self.assertIn("DE89 •••• •••• 3000", inhalt)
        self.assertNotIn("3704 0044 0532", inhalt.replace("•", ""))

    def test_ungueltige_iban_wird_abgelehnt(self):
        response = self.client.post(
            "/beitraege/mandate/neu/",
            {
                "member": self.member.pk,
                "referenz": "SCKS-2026-002",
                "iban": "DE12",
                "erteilt_am": "2026-01-05",
                "status": "aktiv",
                "kontoinhaber": "",
                "notiz": "",
                "widerrufen_am": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SepaMandate.objects.exists())
        self.assertContains(response, "gültige IBAN")

    def test_kategorie_toggle_und_loeschschutz(self):
        kategorie = FeeCategory.objects.create(name="Familie", betrag=Decimal("130.00"))
        self.member.beitragskategorie = kategorie
        self.member.save()
        response = self.client.post(
            f"/beitraege/kategorien/{kategorie.pk}/loeschen/", HTTP_ACCEPT="application/json"
        )
        self.assertFalse(json.loads(response.content)["ok"], "Zugeordnete Kategorie darf nicht gelöscht werden")

        response = self.client.post(
            f"/beitraege/kategorien/{kategorie.pk}/status/", HTTP_ACCEPT="application/json"
        )
        kategorie.refresh_from_db()
        self.assertFalse(kategorie.aktiv)
        self.assertFalse(json.loads(response.content)["checked"])


class MitgliedsKontoTests(TestCase):
    def test_mitglied_sieht_nur_eigene_posten_und_keine_fremden(self):
        user = User.objects.create_user("p1", password="x")
        fremd_user = User.objects.create_user("p2", password="x")
        group, _ = Group.objects.get_or_create(name="mitglied")
        user.groups.add(group)
        fremd_user.groups.add(group)
        member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 1), user=user
        )
        fremd = Member.objects.create(
            vorname="Bernd", nachname="Geheim", eintrittsdatum=date(2020, 1, 1), user=fremd_user
        )
        MembershipFee.objects.create(
            member=member, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )
        MembershipFee.objects.create(
            member=fremd, jahr=2026, kategorie_name="Sondertarif-Fremd",
            betrag=Decimal("777.00"), faellig_am=date(2026, 1, 31),
        )
        SepaMandate.objects.create(
            member=fremd, referenz="FREMD-MANDAT-999", iban="DE89370400440532013000",
            erteilt_am=date(2026, 1, 5),
        )
        self.client.force_login(user)
        response = self.client.get("/mein-beitragskonto/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "90,00 €")
        self.assertContains(response, "Offen")
        self.assertNotContains(response, "777,00")
        self.assertNotContains(response, "Sondertarif-Fremd")
        self.assertNotContains(response, "FREMD-MANDAT-999")
        self.assertNotContains(response, "Geheim")


class BerechtigungsUndFehlerpfadTests(TestCase):
    """403-Negativtests ('403 verändert nichts'), Fehlerpfade, Admin-Schutz & Query-Budget."""

    def setUp(self):
        self.admin = make_admin()
        self.mitglied = User.objects.create_user("mitglied1", password="x")
        g_m, _ = Group.objects.get_or_create(name="mitglied")
        self.mitglied.groups.add(g_m)
        self.kapitaen = User.objects.create_user("kapitaen1", password="x")
        g_k, _ = Group.objects.get_or_create(name="kapitaen")
        self.kapitaen.groups.add(g_k)

        self.kategorie = FeeCategory.objects.create(name="Erwachsene", betrag=Decimal("90.00"))
        self.member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 1),
            beitragskategorie=self.kategorie,
        )
        self.fee = MembershipFee.objects.create(
            member=self.member, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )
        self.zahlung = zahlung_erfassen(
            self.fee, betrag=Decimal("40.00"), datum=date(2026, 2, 1), benutzer=self.admin
        )

    def test_nicht_admin_erhaelt_403_und_veraendert_nichts(self):
        for benutzer in (self.mitglied, self.kapitaen):
            self.client.force_login(benutzer)
            routen = [
                ("GET", "/beitraege/", {}),
                ("POST", "/beitraege/lauf/", {"jahr": "2027"}),
                ("GET", "/beitraege/export.csv", {}),
                ("POST", "/beitraege/kategorien/", {"name": "Neu", "betrag": "10.00"}),
                ("POST", f"/beitraege/kategorien/{self.kategorie.pk}/status/", {}),
                ("POST", f"/beitraege/kategorien/{self.kategorie.pk}/loeschen/", {}),
                ("GET", "/beitraege/mandate/", {}),
                ("POST", "/beitraege/mandate/neu/", {"member": self.member.pk, "referenz": "X", "iban": "DE89370400440532013000", "erteilt_am": "2026-01-01", "status": "aktiv"}),
                ("GET", "/beitraege/mahnwesen/", {}),
                ("POST", f"/beitraege/mahnwesen/{self.fee.pk}/mahnung/", {"gebuehr": "5.00"}),
                ("GET", f"/beitraege/mahnwesen/{self.fee.pk}/brief/", {}),
                ("GET", f"/beitraege/posten/{self.fee.pk}/", {}),
                ("POST", f"/beitraege/posten/{self.fee.pk}/zahlung/", {"betrag": "50.00", "datum": "2026-03-01", "art": "bar"}),
                ("POST", f"/beitraege/zahlung/{self.zahlung.pk}/storno/", {}),
            ]
            for methode, url, daten in routen:
                with self.subTest(benutzer=benutzer.username, url=url):
                    resp = self.client.get(url) if methode == "GET" else self.client.post(url, daten)
                    self.assertEqual(resp.status_code, 403)

        # „403 verändert nichts“
        self.fee.refresh_from_db()
        self.zahlung.refresh_from_db()
        self.kategorie.refresh_from_db()
        self.assertEqual(self.fee.bezahlter_betrag, Decimal("40.00"))
        self.assertFalse(self.zahlung.ist_storniert)
        self.assertTrue(self.kategorie.aktiv)
        self.assertFalse(SepaMandate.objects.exists())

    def test_fehlerpfade_und_formular_views_in_dues(self):
        self.client.force_login(self.admin)
        # Übersicht mit Filter & Suche + Detailseite
        self.assertEqual(self.client.get("/beitraege/?jahr=2026&status=offen&q=Meier").status_code, 200)
        self.assertEqual(self.client.get("/beitraege/?jahr=2026&status=bezahlt").status_code, 200)
        self.assertEqual(self.client.get(f"/beitraege/posten/{self.fee.pk}/").status_code, 200)

        # Ungültige Zahlung ohne AJAX -> Redirect zurück zur Detailseite
        resp = self.client.post(f"/beitraege/posten/{self.fee.pk}/zahlung/", {"betrag": "-5", "datum": "2026-03-01", "art": "bar"})
        self.assertRedirects(resp, f"/beitraege/posten/{self.fee.pk}/")

        # Ungültige Mahnung mit und ohne AJAX
        resp_ajax = self.client.post(
            f"/beitraege/mahnwesen/{self.fee.pk}/mahnung/", {"gebuehr": "-5"}, HTTP_ACCEPT="application/json"
        )
        self.assertFalse(json.loads(resp_ajax.content)["ok"])
        resp_html = self.client.post(f"/beitraege/mahnwesen/{self.fee.pk}/mahnung/", {"gebuehr": "-5"})
        self.assertRedirects(resp_html, "/beitraege/")

        # Ungültiger Beitragslauf mit und ohne AJAX
        lauf_ajax = self.client.post("/beitraege/lauf/", {"jahr": "1900"}, HTTP_ACCEPT="application/json")
        self.assertFalse(json.loads(lauf_ajax.content)["ok"])
        lauf_html = self.client.post("/beitraege/lauf/", {"jahr": "1900"})
        self.assertRedirects(lauf_html, "/beitraege/")

        # Kategorien anlegen, bearbeiten, löschen (unbenutzte Kategorie)
        kat_resp = self.client.post(
            "/beitraege/kategorien/", {"name": "Passiv-Satz", "betrag": "30.00", "aktiv": "on"},
            HTTP_ACCEPT="application/json",
        )
        self.assertTrue(json.loads(kat_resp.content)["ok"])
        neu_kat = FeeCategory.objects.get(name="Passiv-Satz")
        self.assertEqual(self.client.get(f"/beitraege/kategorien/{neu_kat.pk}/bearbeiten/").status_code, 200)
        upd_resp = self.client.post(
            f"/beitraege/kategorien/{neu_kat.pk}/bearbeiten/",
            {"name": "Passiv-Satz", "betrag": "35.00", "aktiv": "on"},
        )
        self.assertRedirects(upd_resp, "/beitraege/kategorien/")
        del_resp = self.client.post(f"/beitraege/kategorien/{neu_kat.pk}/loeschen/", HTTP_ACCEPT="application/json")
        self.assertTrue(json.loads(del_resp.content)["ok"])

        # Mandat anlegen und bearbeiten
        m_resp = self.client.post(
            "/beitraege/mandate/neu/",
            {
                "member": self.member.pk, "referenz": "SCKS-2026-010",
                "iban": "DE89 3704 0044 0532 0130 00", "erteilt_am": "2026-01-05", "status": "aktiv",
            },
            HTTP_ACCEPT="application/json",
        )
        self.assertTrue(json.loads(m_resp.content)["ok"])
        mandat = SepaMandate.objects.get(referenz="SCKS-2026-010")
        self.assertEqual(self.client.get(f"/beitraege/mandate/{mandat.pk}/bearbeiten/").status_code, 200)
        m_upd = self.client.post(
            f"/beitraege/mandate/{mandat.pk}/bearbeiten/",
            {
                "member": self.member.pk, "referenz": "SCKS-2026-010",
                "iban": "DE89 3704 0044 0532 0130 00", "erteilt_am": "2026-01-05",
                "status": "widerrufen", "widerrufen_am": "2026-06-01",
            },
        )
        self.assertRedirects(m_upd, "/beitraege/mandate/")

    def test_admin_verbietet_loeschen_von_finanzdaten(self):
        site = AdminSite()
        self.assertFalse(PaymentAdmin(Payment, site).has_delete_permission(None, self.zahlung))
        self.assertFalse(MembershipFeeAdmin(MembershipFee, site).has_delete_permission(None, self.fee))
        self.assertFalse(DunningLetterAdmin(DunningLetter, site).has_delete_permission(None, None))

    def test_beitrags_export_hat_konstante_query_anzahl(self):
        self.client.force_login(self.admin)
        for idx in range(5):
            m = Member.objects.create(
                vorname=f"M{idx}", nachname=f"Nach{idx}",
                eintrittsdatum=date(2020, 1, 1), beitragskategorie=self.kategorie,
            )
            f = MembershipFee.objects.create(
                member=m, jahr=2026, kategorie_name="Erwachsene",
                betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
            )
            Payment.objects.create(fee=f, betrag=Decimal("45.00"), datum=date(2026, 2, 1))
        # select_related("member") + prefetch_related("zahlungen") verhindert N+1 beim CSV-Export (5 Queries statt 17)
        with self.assertNumQueries(5):
            resp = self.client.get("/beitraege/export.csv?jahr=2026")
            self.assertEqual(resp.status_code, 200)


class BeitragEndToEndIntegrationTests(TestCase):
    """Durchgängige Kette: Beitragslauf → Teilzahlung → Mahnung → Vollzahlung → Storno → Export → Kassenabschluss."""

    def test_komplette_beitragskette(self):
        admin = make_admin("kassenwart_e2e")
        self.client.force_login(admin)
        kat = FeeCategory.objects.create(name="Erwachsene", betrag=Decimal("100.00"))
        anna = Member.objects.create(
            vorname="Anna", nachname="Acker", eintrittsdatum=date(2021, 1, 1), beitragskategorie=kat
        )
        bodo = Member.objects.create(
            vorname="Bodo", nachname="Berg", eintrittsdatum=date(2021, 1, 1), beitragskategorie=kat
        )

        # 1. Beitragslauf
        lauf = beitragslauf(2026, faellig_am=date(2026, 1, 31), benutzer=admin)
        self.assertEqual(lauf["angelegt"], 2)
        fee_anna = MembershipFee.objects.get(member=anna, jahr=2026)
        fee_bodo = MembershipFee.objects.get(member=bodo, jahr=2026)

        # 2. Anna zahlt vollständig, Bodo zahlt teilweise und wird gemahnt
        z_anna = zahlung_erfassen(fee_anna, betrag=Decimal("100.00"), datum=date(2026, 2, 5), benutzer=admin)
        zahlung_erfassen(fee_bodo, betrag=Decimal("40.00"), datum=date(2026, 2, 10), benutzer=admin)
        mahnung = mahnung_erstellen(fee_bodo, gebuehr=Decimal("5.00"), notiz="1. Erinnerung", benutzer=admin)
        self.assertEqual(mahnung.stufe, 1)

        # 3. Irrtümliche Zahlung bei Anna wird storniert und anschließend neu gebucht
        zahlung_stornieren(z_anna, grund="Falsches Konto", datum=date(2026, 2, 6), benutzer=admin)
        fee_anna.refresh_from_db()
        self.assertEqual(fee_anna.status, MembershipFee.Status.OFFEN)
        zahlung_erfassen(fee_anna, betrag=Decimal("100.00"), datum=date(2026, 2, 12), benutzer=admin)
        fee_anna.refresh_from_db()
        self.assertEqual(fee_anna.status, MembershipFee.Status.BEZAHLT)

        # 4. Jahresübersicht, CSV-Export und Kassenbuch-Jahresabschluss stimmen überein
        uebersicht = jahres_uebersicht(2026)
        self.assertEqual(uebersicht["soll"], Decimal("200.00"))
        self.assertEqual(uebersicht["bezahlt"], Decimal("140.00"))
        self.assertEqual(uebersicht["offen"], Decimal("60.00"))

        abschluss = jahresabschluss(2026)
        self.assertEqual(abschluss["einnahmen"], Decimal("140.00"))
        self.assertEqual(abschluss["saldo"], Decimal("140.00"))

        csv_resp = self.client.get("/beitraege/export.csv?jahr=2026")
        csv_text = csv_resp.content.decode("utf-8-sig")
        self.assertIn("Acker;Anna;Erwachsene;100,00;100,00;0,00;Bezahlt", csv_text)
        self.assertIn("Berg;Bodo;Erwachsene;100,00;40,00;60,00;Teilweise bezahlt", csv_text)
