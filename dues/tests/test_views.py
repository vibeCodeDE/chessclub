"""Beitragslauf in der Oberfläche (PRD M2.2) — Zugriff, Vorschau, Ausführung."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.models import AuditLog
from dues.models import FeeAmount, FeeCategory, FeePost, Payment, SepaMandate
from members.models import Member

LISTE = "/beitraege/"
LAUF = "/beitraege/lauf/"
ZAHLUNGEN = "/beitraege/zahlungen/"
BUCHEN = "/beitraege/zahlungen/buchen/"


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


def make_post(jahr=2026, betrag="90.00"):
    kategorie_ = kategorie("erwachsene")
    member = make_member(kategorie_)
    return FeePost.objects.create(
        member=member, jahr=jahr, kategorie=kategorie_, betrag=Decimal(betrag)
    )


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

        self.assertEqual(
            [zeile["post"] for zeile in response.context["posts"]],
            [FeePost.objects.get()],
        )
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


class PostenListeZahlungsanzeigeTests(TestCase):
    """Die Postenliste zeigt den Zahlungsstand aus dues/services.py (T9)."""

    def setUp(self):
        self.client.force_login(make_user("vorstand", "admin"))
        self.post = make_post(jahr=2026, betrag="90.00")

    def test_unbezahlter_posten_zeigt_vollen_betrag_als_offen(self):
        response = self.client.get(LISTE, {"jahr": 2026})

        zeile = response.context["posts"][0]
        self.assertEqual(zeile["offen"], Decimal("90.00"))
        self.assertEqual(zeile["status_label"], "Unbezahlt")
        self.assertContains(response, "Unbezahlt")

    def test_bezahlter_posten_zeigt_null_offen(self):
        Payment.objects.create(
            post=self.post, betrag=Decimal("90.00"), art=Payment.Art.UEBERWEISUNG
        )

        response = self.client.get(LISTE, {"jahr": 2026})

        zeile = response.context["posts"][0]
        self.assertEqual(zeile["offen"], Decimal("0.00"))
        self.assertEqual(zeile["status_label"], "Bezahlt")

    def test_ueberzahlung_erscheint_als_gutschrift(self):
        Payment.objects.create(
            post=self.post, betrag=Decimal("100.00"), art=Payment.Art.UEBERWEISUNG
        )

        response = self.client.get(LISTE, {"jahr": 2026})

        self.assertEqual(response.context["posts"][0]["status_label"], "Gutschrift")
        self.assertContains(response, "-10,00")

    def test_jede_zeile_verweist_auf_die_zahlungsseite(self):
        response = self.client.get(LISTE, {"jahr": 2026})

        self.assertContains(
            response,
            f"{reverse('dues:zahlungsliste')}?jahr=2026&amp;posten={self.post.pk}",
        )


class ZahlungslisteZugriffTests(TestCase):
    """Zahlungen sind Vorstandssache (PRD §3.8)."""

    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.post = make_post()

    def test_admin_darf_die_zahlungsliste_sehen(self):
        self.client.force_login(self.admin)

        response = self.client.get(ZAHLUNGEN)

        self.assertEqual(response.status_code, 200)

    def test_kapitaen_erhaelt_403(self):
        self.client.force_login(make_user("kapitaen", "kapitaen"))

        self.assertEqual(self.client.get(ZAHLUNGEN).status_code, 403)

    def test_mitglied_erhaelt_403_beim_buchen_und_es_bucht_nichts(self):
        """Negativtest: der verweigerte Zugriff darf keine Zahlung erzeugen."""
        self.client.force_login(make_user("mitglied", "mitglied"))

        response = self.client.post(
            BUCHEN, {"post": self.post.pk, "betrag": "90.00", "art": Payment.Art.BAR}
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Payment.objects.count(), 0)

    def test_gast_wird_zum_anmelden_umgeleitet(self):
        response = self.client.get(ZAHLUNGEN)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response["Location"])


class ZahlungBuchenTests(TestCase):
    """Zahlungen von Hand buchen (PRD M2.4)."""

    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.post = make_post()

    def _buchen(self, follow=False, **daten):
        daten.setdefault("post", self.post.pk)
        daten.setdefault("betrag", "90.00")
        daten.setdefault("art", Payment.Art.UEBERWEISUNG)
        return self.client.post(BUCHEN, daten, follow=follow)

    def test_buchung_wird_angelegt(self):
        self._buchen()

        zahlung = Payment.objects.get()
        self.assertEqual(zahlung.post, self.post)
        self.assertEqual(zahlung.betrag, Decimal("90.00"))
        self.assertEqual(zahlung.art, Payment.Art.UEBERWEISUNG)
        self.assertEqual(zahlung.erfasst_von, self.admin)

    def test_betrag_wird_auch_im_deutschen_format_angenommen(self):
        self._buchen(betrag="90,00")

        self.assertEqual(Payment.objects.get().betrag, Decimal("90.00"))

    def test_buchung_wird_im_audit_log_protokolliert(self):
        self._buchen()

        eintrag = AuditLog.objects.get(aktion="Zahlung gebucht")
        self.assertEqual(eintrag.member, self.post.member)
        self.assertEqual(eintrag.benutzer, self.admin)
        self.assertIn("90,00", eintrag.text)

    def test_sepa_ohne_mandat_wird_abgelehnt(self):
        """Negativtest laut Plan T9: SEPA braucht ein aktives Mandat."""
        response = self._buchen(follow=True, art=Payment.Art.SEPA)

        self.assertEqual(Payment.objects.count(), 0)
        self.assertContains(response, "SEPA-Mandat")

    def test_sepa_mit_mandat_wird_gebucht(self):
        SepaMandate.objects.create(member=self.post.member, referenz="M-1")

        self._buchen(art=Payment.Art.SEPA)

        self.assertEqual(Payment.objects.get().art, Payment.Art.SEPA)

    def test_buchung_ist_nur_per_post_moeglich(self):
        """Negativtest: GET bucht nichts (405)."""
        response = self.client.get(BUCHEN)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Payment.objects.count(), 0)

    def test_betrag_null_wird_abgelehnt(self):
        self._buchen(betrag="0")

        self.assertEqual(Payment.objects.count(), 0)

    def test_unlesbarer_betrag_wird_abgelehnt(self):
        self._buchen(betrag="viel")

        self.assertEqual(Payment.objects.count(), 0)

    def test_unbekannter_posten_wird_abgelehnt(self):
        self._buchen(post="99999")

        self.assertEqual(Payment.objects.count(), 0)

    def test_ueberzahlung_wird_als_gutschrift_gebucht(self):
        response = self._buchen(betrag="100.00", follow=True)

        self.assertEqual(Payment.objects.get().betrag, Decimal("100.00"))
        self.assertContains(response, "Gutschrift")

    def test_formular_bleibt_bei_fehler_ausgefuellt(self):
        response = self._buchen(betrag="0", referenz="Kassenbon 42")

        self.assertEqual(response.context["formular"]["referenz"], "Kassenbon 42")
        self.assertEqual(response.context["formular"]["betrag"], "0")
        self.assertEqual(str(response.context["formular"]["post"]), str(self.post.pk))

    def test_fehlerhafte_buchung_zeigt_die_eingabe_nochmal(self):
        response = self._buchen(betrag="0", referenz="Kassenbon 42")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kassenbon 42")

    def test_erfolgreiche_buchung_meldet_die_summe(self):
        response = self._buchen(follow=True)

        self.assertContains(response, "90,00")
        self.assertEqual(response.context["jahr"], 2026)


class StornoTests(TestCase):
    """Fehlbuchungen werden per Gegenbuchung aufgehoben, nicht gelöscht."""

    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.post = make_post()
        self.zahlung = Payment.objects.create(
            post=self.post, betrag=Decimal("90.00"), art=Payment.Art.UEBERWEISUNG
        )

    def _storno(self):
        return self.client.post(f"{ZAHLUNGEN}{self.zahlung.pk}/storno/")

    def test_storno_bucht_eine_gegenbuchung_und_loescht_nichts(self):
        self._storno()

        storno = Payment.objects.get(storno_von=self.zahlung)
        self.assertEqual(storno.betrag, Decimal("-90.00"))
        self.assertEqual(storno.post, self.post)
        self.assertEqual(Payment.objects.count(), 2)
        self.assertTrue(Payment.objects.filter(pk=self.zahlung.pk).exists())

    def test_storno_wird_im_audit_log_protokolliert(self):
        self._storno()

        eintrag = AuditLog.objects.get(aktion="Zahlung storniert")
        self.assertEqual(eintrag.member, self.post.member)
        self.assertIn(str(self.zahlung.pk), eintrag.text)

    def test_nach_dem_storno_ist_der_posten_wieder_offen(self):
        self._storno()

        response = self.client.get(LISTE, {"jahr": 2026})

        self.assertEqual(response.context["posts"][0]["status_label"], "Unbezahlt")
        self.assertEqual(response.context["posts"][0]["offen"], Decimal("90.00"))

    def test_storno_ist_nur_per_post_moeglich(self):
        """Negativtest: GET storniert nichts (405)."""
        response = self.client.get(f"{ZAHLUNGEN}{self.zahlung.pk}/storno/")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Payment.objects.count(), 1)

    def test_ein_storno_kann_nicht_storniert_werden(self):
        """Negativtest: eine Gegenbuchung ist die letzte Buchung im Posten."""
        self._storno()
        storno = Payment.objects.get(storno_von=self.zahlung)

        self.client.post(f"{ZAHLUNGEN}{storno.pk}/storno/")

        self.assertEqual(Payment.objects.count(), 2)

    def test_mitglied_darf_nicht_stornieren(self):
        """Negativtest: Storno ist Vorstandssache."""
        self.client.force_login(make_user("mitglied", "mitglied"))

        response = self._storno()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Payment.objects.count(), 1)


class ZahlungslisteAnzeigeTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user("vorstand", "admin"))
        self.post = make_post()
        SepaMandate.objects.create(member=self.post.member, referenz="M-2026-001")

    def test_zeigt_die_gebuchten_zahlungen_des_jahres(self):
        Payment.objects.create(
            post=self.post, betrag=Decimal("90.00"), art=Payment.Art.BAR
        )

        response = self.client.get(ZAHLUNGEN, {"jahr": 2026})

        self.assertEqual(len(response.context["zahlungen"]), 1)
        self.assertContains(response, "Barzahlung")

    def test_zeigt_die_mandate_des_vereins(self):
        response = self.client.get(ZAHLUNGEN, {"jahr": 2026})

        self.assertContains(response, "M-2026-001")
        self.assertEqual(len(response.context["mandate"]), 1)

    def test_posten_vorauswahl_uebernimmt_den_offenen_betrag(self):
        response = self.client.get(
            ZAHLUNGEN, {"jahr": 2026, "posten": self.post.pk}
        )

        self.assertEqual(response.context["formular"]["betrag"], Decimal("90.00"))
        self.assertEqual(response.context["formular"]["post"], self.post.pk)

    def test_leere_liste_bricht_nicht_ab(self):
        response = self.client.get(ZAHLUNGEN, {"jahr": 2027})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["zahlungen"]), 0)


class MandatAnlegenTests(TestCase):
    """SEPA-Mandate anlegen (PRD M2.3)."""

    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.member = make_member(kategorie("erwachsene"))

    def _anlegen(self, follow=False, **daten):
        daten.setdefault("member", self.member.pk)
        daten.setdefault("referenz", "M-2026-001")
        daten.setdefault("datum", "2026-01-05")
        return self.client.post("/beitraege/mandate/", daten, follow=follow)

    def test_mandat_wird_angelegt_und_ist_aktiv(self):
        self._anlegen()

        mandat = SepaMandate.objects.get()
        self.assertEqual(mandat.member, self.member)
        self.assertEqual(mandat.status, SepaMandate.Status.AKTIV)
        self.assertEqual(mandat.datum, date(2026, 1, 5))

    def test_mandat_wird_im_audit_log_protokolliert(self):
        self._anlegen()

        eintrag = AuditLog.objects.get(aktion="SEPA-Mandat angelegt")
        self.assertEqual(eintrag.member, self.member)
        self.assertIn("M-2026-001", eintrag.text)

    def test_ohne_referenz_wird_nichts_angelegt(self):
        """Negativtest: ohne Referenz ist das Mandat nicht führbar."""
        self._anlegen(referenz="  ")

        self.assertEqual(SepaMandate.objects.count(), 0)

    def test_doppelte_referenz_wird_abgelehnt(self):
        """Negativtest: die Referenz ist eindeutig."""
        SepaMandate.objects.create(member=self.member, referenz="M-2026-001")

        self._anlegen()

        self.assertEqual(SepaMandate.objects.count(), 1)

    def test_mitglied_darf_kein_mandat_anlegen(self):
        """Negativtest: Mandate sind Vorstandssache (PRD §3.8)."""
        self.client.force_login(make_user("mitglied", "mitglied"))

        self._anlegen()

        self.assertEqual(SepaMandate.objects.count(), 0)

    def test_anlegen_ist_nur_per_post_moeglich(self):
        """Negativtest: GET legt kein Mandat an (405)."""
        response = self.client.get("/beitraege/mandate/")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(SepaMandate.objects.count(), 0)


class MandatStatusTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.member = make_member(kategorie("erwachsene"))
        self.mandat = SepaMandate.objects.create(
            member=self.member, referenz="M-1"
        )

    def _status(self, status, follow=False):
        return self.client.post(
            f"/beitraege/mandate/{self.mandat.pk}/status/",
            {"status": status},
            follow=follow,
        )

    def test_widerruf_wird_gesetzt_und_protokolliert(self):
        self._status(SepaMandate.Status.WIDERRUFEN)

        self.mandat.refresh_from_db()
        self.assertEqual(self.mandat.status, SepaMandate.Status.WIDERRUFEN)
        eintrag = AuditLog.objects.get(aktion="SEPA-Mandat geändert")
        self.assertEqual(eintrag.feld, "status")
        self.assertEqual(eintrag.alt_wert, SepaMandate.Status.AKTIV)
        self.assertEqual(eintrag.neu_wert, SepaMandate.Status.WIDERRUFEN)
        self.assertEqual(eintrag.member, self.member)

    def test_nach_widerruf_ist_kein_sepa_einzug_mehr_moeglich(self):
        """Negativtest: die Ableitung greift direkt nach dem Widerruf."""
        self._status(SepaMandate.Status.WIDERRUFEN)
        post = make_post()

        response = self.client.post(
            BUCHEN, {"post": post.pk, "betrag": "90.00", "art": Payment.Art.SEPA},
            follow=True,
        )

        self.assertEqual(Payment.objects.count(), 0)
        self.assertContains(response, "SEPA-Mandat")

    def test_unbekannter_status_wird_abgelehnt(self):
        self._status("geloescht")

        self.mandat.refresh_from_db()
        self.assertEqual(self.mandat.status, SepaMandate.Status.AKTIV)

    def test_status_ist_nur_per_post_moeglich(self):
        """Negativtest: GET ändert nichts (405)."""
        self.client.get(f"/beitraege/mandate/{self.mandat.pk}/status/")

        self.mandat.refresh_from_db()
        self.assertEqual(self.mandat.status, SepaMandate.Status.AKTIV)
