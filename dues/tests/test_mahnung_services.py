"""Stufenregel des Mahnwesens (PRD M2.5) — ohne HTTP, nur Services."""

from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import AuditLog
from dues.mahnung import (
    mahnungen_setzen,
    mahnstufe_text,
    naechste_stufe,
    offene_posten,
    posten_fuer_brief,
)
from dues.models import FeeCategory, FeePost, Mahnung, Payment
from members.models import Member


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


class MahnstufeTextTests(TestCase):
    def test_erste_und_zweite_stufe(self):
        self.assertEqual(mahnstufe_text(1), "1. Mahnung")
        self.assertEqual(mahnstufe_text(2), "2. Mahnung")

    def test_ausgeschoepfte_stufen(self):
        self.assertEqual(mahnstufe_text(None), "ausgeschöpft")


class NaechsteStufeTests(TestCase):
    def setUp(self):
        self.post = make_post()

    def test_ohne_mahnung_ist_stufe_eins_naechste(self):
        self.assertEqual(naechste_stufe(self.post), 1)

    def test_nach_erster_mahnung_ist_stufe_zwei_naechste(self):
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        self.assertEqual(naechste_stufe(self.post), 2)

    def test_nach_zwei_mahnungen_ist_keine_stufe_mehr_frei(self):
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2)

        self.assertIsNone(naechste_stufe(self.post))

    def test_stufe_ist_pro_posten_eigenstaendig(self):
        anderer = make_post(member=make_member(nachname="Koch", kategorie=self.post.kategorie))
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2)

        self.assertEqual(naechste_stufe(anderer), 1)


class MahnungenSetzenTests(TestCase):
    def setUp(self):
        self.post = make_post()

    def test_setzt_die_erste_mahnung_mit_datum(self):
        mahnung = mahnungen_setzen(
            self.post, 1, date(2026, 3, 1), benutzer=User.objects.create_user("v")
        )

        self.assertEqual(mahnung.post, self.post)
        self.assertEqual(mahnung.stufe, 1)
        self.assertEqual(mahnung.datum, date(2026, 3, 1))
        self.assertIsNone(mahnung.frist)
        self.assertEqual(mahnung.notiz, "")

    def test_setzt_die_zweite_mahnung_mit_frist_und_notiz(self):
        mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        mahnung = mahnungen_setzen(
            self.post,
            2,
            date(2026, 4, 1),
            frist=date(2026, 4, 15),
            notiz="Telefonisch angekündigt",
        )

        self.assertEqual(mahnung.stufe, 2)
        self.assertEqual(mahnung.frist, date(2026, 4, 15))
        self.assertEqual(mahnung.notiz, "Telefonisch angekündigt")

    def test_rueckdatiertes_datum_wird_akzeptiert(self):
        """Eine Rückdatierung ist legitim — der Vorstand plant im Voraus."""

        mahnung = mahnungen_setzen(self.post, 1, date(2026, 1, 5))

        self.assertEqual(mahnung.datum, date(2026, 1, 5))

    def test_bezahlter_posten_wird_abgelehnt(self):
        zahle(self.post)

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        self.assertIn("bezahlt", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_gutschrift_wird_abgelehnt(self):
        zahle(self.post, "100.00")

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        self.assertIn("bezahlt", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_teilzahlung_bleibt_mahnbar(self):
        zahle(self.post, "40.00")

        mahnung = mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        self.assertEqual(mahnung.stufe, 1)

    def test_ueberspringen_der_stufe_wird_abgelehnt(self):
        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 2, date(2026, 3, 1))

        self.assertIn("1. Mahnung", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_doppelte_stufe_wird_abgelehnt(self):
        mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 4, 1))

        self.assertIn("existiert bereits", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 1)

    def test_nach_zwei_mahnungen_ist_keine_stufe_mehr_setzbar(self):
        mahnungen_setzen(self.post, 1, date(2026, 3, 1))
        mahnungen_setzen(self.post, 2, date(2026, 4, 1))

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 5, 1))

        self.assertIn("ausgeschöpft", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 2)

    def test_unbekannte_stufe_wird_abgelehnt(self):
        with self.assertRaises(ValidationError):
            mahnungen_setzen(self.post, 3, date(2026, 3, 1))

        self.assertEqual(Mahnung.objects.count(), 0)

    def test_ohne_datum_wird_abgelehnt(self):
        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, None)

        self.assertIn("Mahndatum", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_schreibt_einen_audit_eintrag_mit_mitglied(self):
        benutzer = User.objects.create_user("vorstand")

        mahnungen_setzen(
            self.post, 1, date(2026, 3, 1), frist=date(2026, 4, 1), benutzer=benutzer
        )

        eintrag = AuditLog.objects.get(aktion="Mahnung gesetzt")
        self.assertEqual(eintrag.member, self.post.member)
        self.assertEqual(eintrag.benutzer, benutzer)
        self.assertIn("1. Mahnung", eintrag.text)
        self.assertIn("2026-03-01", eintrag.text)

    def test_doppelbuchung_aus_dem_doppelklick_ergibt_keinen_500(self):
        """Zwei gleichzeitige Klicks: die Constraint wird als ValidationError gefangen.

        ``naechste_stufe`` wird auf „Stufe 1 ist frei" festgenagelt, obwohl die
        Datenbank die 1. Mahnung schon kennt. Genau das ist der Zwischenmoment
        zwischen Prüfung und Insert, in dem ein zweiter Klick durchrutscht: hier
        wirft die Constraint ``unique_mahnung_pro_post_stufe`` einen **echten**
        ``IntegrityError``, nicht einen simulierten — sonst würde der Test den
        Vorab-Check von :meth:`test_doppelte_stufe_wird_abgelehnt` nur wiederholen
        und den Nebenläufigkeitszweig unbewiesen lassen.
        """
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        with mock.patch(
            "dues.mahnung.naechste_stufe", return_value=Mahnung.Stufe.MAHNUNG_1
        ):
            with self.assertRaises(ValidationError) as fehler:
                mahnungen_setzen(self.post, 1, date(2026, 4, 1))

        self.assertIn("existiert bereits", str(fehler.exception))
        # Ein abgefangener IntegrityError darf keine halbe Buchung hinterlassen.
        self.assertEqual(AuditLog.objects.filter(aktion="Mahnung gesetzt").count(), 0)
        # Und der Savepoint muss die Transaktion benutzbar gelassen haben —
        # schlug das fehl, wäre der nächste Schreibvorgang ein
        # TransactionManagementError statt einer Mahnung.
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2)
        self.assertEqual(Mahnung.objects.count(), 2)

    def test_audit_fehler_bricht_die_gesamte_buchung_ab(self):
        """Eine Mahnung ohne Protokollzeile wäre hinterher nicht mehr auffindbar.

        Der Audit-Ausfall wird als ``RuntimeError`` simuliert und **nicht** als
        Datenbankfehler: nur so bleibt die Verbindung nach dem Fehler benutzbar
        und der Test kann überhaupt erst zählen, ob eine Mahnung zurückblieb.
        Der ``IntegrityError``-Pfad ist in
        :meth:`test_doppelbuchung_aus_dem_doppelklick_ergibt_keinen_500`
        abgedeckt.
        """
        with mock.patch(
            "core.models.AuditLog.objects.create",
            side_effect=RuntimeError("Audit-Ausfall"),
        ):
            with self.assertRaises(RuntimeError):
                mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        self.assertEqual(Mahnung.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_abgelehnte_stufe_erzeugt_keinen_zusatzlichen_audit_eintrag(self):
        """Eine abgelehnte Operation darf das Protokoll nicht verfälschen."""
        mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        with self.assertRaises(ValidationError):
            mahnungen_setzen(self.post, 1, date(2026, 4, 1))

        self.assertEqual(AuditLog.objects.filter(aktion="Mahnung gesetzt").count(), 1)

    def test_frist_vor_dem_mahndatum_wird_akzeptiert(self):
        """Die Frist wird bewusst nicht gegen das Mahndatum geprüft.

        Sie ist ein Textfeld für den Brief, kein abgeleitetes Datum — der Vorstand
        entscheidet, welches Zahlungsziel im Schreiben steht.
        """
        mahnung = mahnungen_setzen(
            self.post, 1, date(2026, 3, 1), frist=date(2026, 1, 1)
        )

        self.assertEqual(mahnung.frist, date(2026, 1, 1))


class OffenePostenTests(TestCase):
    def setUp(self):
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]

    def _posten(self, anzahl, jahr=2026, betrag="90.00"):
        posten = []
        for nummer in range(anzahl):
            member = make_member(
                nachname=f"Mustermann{nummer:02d}",
                vorname="Anna",
                kategorie=self.kategorie,
            )
            posten.append(
                make_post(member=member, jahr=jahr, betrag=betrag, kategorie=self.kategorie)
            )
        return posten

    def _posten_mit_namen(self, namen, jahr=2026, betrag="90.00"):
        """Legt je ``(nachname, vorname)`` einen Posten an — in genau der Reihenfolge."""
        return [
            make_post(
                member=make_member(
                    nachname=nachname, vorname=vorname, kategorie=self.kategorie
                ),
                jahr=jahr,
                betrag=betrag,
                kategorie=self.kategorie,
            )
            for nachname, vorname in namen
        ]

    def test_leeres_jahr_ergibt_leere_liste(self):
        self.assertEqual(offene_posten(2030), [])

    def test_bezahlter_posten_erscheint_auch_bei_offenen_nicht(self):
        """Der Vertrag an dieser Stelle ist **Filtern**, nicht Sortieren.

        Die Übersicht zeigt nur, was noch offen ist; ein bezahlter Posten
        verschwindet, auch wenn daneben ein offener steht. Der Test hieß früher
        „offene Posten kommen vor bezahlten" und behauptete damit eine
        Reihenfolge, die es nicht gibt — er prüft keine.
        """
        offen_post, bezahlt_post = self._posten(2)
        zahle(bezahlt_post)

        zeilen = offene_posten(2026)

        self.assertEqual([zeile["post"] for zeile in zeilen], [offen_post])

    def test_bezahlter_posten_faehlt_heraus(self):
        (post,) = self._posten(1)
        zahle(post)

        self.assertEqual(offene_posten(2026), [])

    def test_teilzahlung_bleibt_offen(self):
        (post,) = self._posten(1, betrag="90.00")
        zahle(post, "40.00")

        (zeile,) = offene_posten(2026)

        self.assertEqual(zeile["offen"], Decimal("50.00"))
        self.assertEqual(zeile["status"], "teilbezahlt")

    def test_gutschrift_faehlt_heraus(self):
        (post,) = self._posten(1, betrag="90.00")
        zahle(post, "100.00")

        self.assertEqual(offene_posten(2026), [])

    def test_zeile_traegt_die_felder_der_postenliste(self):
        (post,) = self._posten(1)
        mahnungen_setzen(post, 1, date(2026, 3, 1))

        (zeile,) = offene_posten(2026)

        self.assertEqual(zeile["post"], post)
        self.assertEqual(zeile["member"], post.member)
        self.assertEqual(zeile["kategorie"], post.kategorie)
        self.assertEqual(zeile["betrag"], Decimal("90.00"))
        self.assertEqual(zeile["bezahlt"], Decimal("0.00"))
        self.assertEqual(zeile["offen"], Decimal("90.00"))
        self.assertEqual(zeile["status"], "unbezahlt")
        self.assertEqual(zeile["status_label"], "Unbezahlt")
        self.assertEqual(zeile["status_klasse"], "badge-unbezahlt")
        self.assertEqual(len(zeile["mahnungen"]), 1)
        self.assertEqual(zeile["stufe"], 2)
        self.assertEqual(zeile["stufe_text"], "2. Mahnung")

    def test_stufe_ist_none_bei_ausgeschoepften_stufen(self):
        (post,) = self._posten(1)
        mahnungen_setzen(post, 1, date(2026, 3, 1))
        mahnungen_setzen(post, 2, date(2026, 4, 1))

        (zeile,) = offene_posten(2026)

        self.assertIsNone(zeile["stufe"])
        self.assertEqual(zeile["stufe_text"], "ausgeschöpft")

    def test_sortiert_nach_nachname_und_vorname(self):
        """Die Übersicht sortiert wie die Postenliste: Nachname, dann Vorname (Spec 5.3).

        Die Mitglieder werden bewusst **anti**sortiert angelegt und die
        Erwartung ist eine feste Liste statt eines ``sorted(...)``-Vergleichs.
        Nur so schlägt der Test fehl, wenn die Sortierung entfällt oder nur zur
        Hälfte dasteht: die frühere Fassung legte ``Mustermann00/01/02`` bereits
        sortiert an und verglich gegen ``sorted(...)`` — sie war grün, egal was
        ``offene_posten`` tat.

        Die beiden gleichnamigen Paare (Meyer und Bauer) sind gegeneinander
        umgekehrt angelegt. Welches davon bei Gleichstand im Nachnamen zuerst
        kommt, entscheidet die Datenbank — aber **eine** der beiden Reihenfolgen
        muss vom Vornamen entschieden werden. Damit ist der Vorname-Teil des
        Vertrags abgesichert, ohne die Ausführungsreihenfolge einer
        Gleichstandsregel zu unterstellen.
        """
        anlegen = [
            ("Ziegler", "Anna"),
            ("Alpha", "Zoe"),
            ("Meyer", "Zoe"),
            ("Meyer", "Anna"),
            ("Bauer", "Anna"),
            ("Bauer", "Zoe"),
        ]
        self._posten_mit_namen(anlegen)

        zeilen = offene_posten(2026)

        self.assertEqual(
            [(z["member"].nachname, z["member"].vorname) for z in zeilen],
            [
                ("Alpha", "Zoe"),
                ("Bauer", "Anna"),
                ("Bauer", "Zoe"),
                ("Meyer", "Anna"),
                ("Meyer", "Zoe"),
                ("Ziegler", "Anna"),
            ],
        )

    def test_anderes_jahr_wird_ignoriert(self):
        self._posten(2, jahr=2026)
        self._posten(1, jahr=2027)

        self.assertEqual(len(offene_posten(2026)), 2)
        self.assertEqual(len(offene_posten(2027)), 1)

    def test_ohne_zusatzabfragen(self):
        """Eine Abfrage für die Liste, eine für die Mahnungen — keine N+1."""
        self._posten(5)
        for zeile in offene_posten(2026):
            mahnungen_setzen(zeile["post"], 1, date(2026, 3, 1))

        with self.assertNumQueries(2):
            zeilen = offene_posten(2026)
            werte = [(z["offen"], z["stufe"], len(z["mahnungen"])) for z in zeilen]

        self.assertEqual(len(werte), 5)


class PostenFuerBriefTests(TestCase):
    def setUp(self):
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]

        self.post = make_post(
            member=make_member(kategorie=self.kategorie), kategorie=self.kategorie
        )

    def test_liefert_die_offenen_posten_des_mitglieds(self):
        (posten, summe) = posten_fuer_brief(2026, self.post.member)

        self.assertEqual([p["post"] for p in posten], [self.post])
        self.assertEqual(summe, Decimal("90.00"))

    def test_ignoriert_bezahlte_posten(self):
        zahle(self.post)

        (posten, summe) = posten_fuer_brief(2026, self.post.member)

        self.assertEqual(posten, [])
        self.assertEqual(summe, Decimal("0.00"))

    def test_ignoriert_andere_mitglieder(self):
        anderer = make_post(
            member=make_member(nachname="Koch", kategorie=self.kategorie),
            kategorie=self.kategorie,
        )

        (posten, _) = posten_fuer_brief(2026, self.post.member)

        self.assertEqual([p["post"] for p in posten], [self.post])
        self.assertNotIn(anderer, [p["post"] for p in posten])

    def test_summe_ist_die_summe_aller_offenen_posten_des_mitglieds(self):
        """Zwei Jahre, zwei Beträge: in den Brief zählt nur das angefragte Jahr.

        `FeePost` hat `unique(member, jahr)` — ein zweiter Posten **für dasselbe
        Jahr** ist deshalb gar nicht möglich, und genau das nutzt der Test als
        Beleg dafür, dass `posten_fuer_brief` sauber nach Jahr filtert. Der
        2026er Posten ist der aus dem `setUp`; hier entsteht nur der 2027er.
        """
        post_2026 = self.post
        post_2027 = make_post(
            member=self.post.member, jahr=2027, betrag="50.00", kategorie=self.kategorie
        )
        self.assertNotEqual(post_2026, post_2027)

        (posten, summe) = posten_fuer_brief(2026, self.post.member)

        self.assertEqual([p["post"] for p in posten], [post_2026])
        self.assertEqual(summe, Decimal("90.00"))
