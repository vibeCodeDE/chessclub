"""Fachlogik Beitragswesen: Beitragslauf, Zahlungen, Mahnwesen (PRD M2)."""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from cashbook.models import CashEntry

from .models import DunningLetter, MembershipFee, Payment

STANDARD_FAELLIGKEIT = date(2000, 1, 31)  # Platzhalter; Jahr wird ersetzt


def _faelligkeit(jahr):
    return date(jahr, 1, 31)


@transaction.atomic
def beitragslauf(jahr, faellig_am=None, benutzer=None):
    """Erzeugt Beitragsposten für alle aktiven Mitglieder mit Kategorie (M2.2).

    Idempotent: ein zweiter Lauf für dasselbe Jahr legt nichts doppelt an.
    """
    from members.models import Member

    faellig_am = faellig_am or _faelligkeit(jahr)
    angelegt = []
    uebersprungen = 0
    mitglieder = (
        Member.objects.filter(status=Member.Status.AKTIV, beitragskategorie__isnull=False)
        .select_related("beitragskategorie")
        .order_by("nachname", "vorname")
    )
    vorhandene = set(
        MembershipFee.objects.filter(jahr=jahr).values_list("member_id", flat=True)
    )
    ohne_kategorie = Member.objects.filter(
        status=Member.Status.AKTIV, beitragskategorie__isnull=True
    ).count()
    for member in mitglieder:
        if member.pk in vorhandene:
            uebersprungen += 1
            continue
        kategorie = member.beitragskategorie
        angelegt.append(
            MembershipFee(
                member=member,
                jahr=jahr,
                kategorie_name=kategorie.name,
                betrag=kategorie.betrag,
                faellig_am=faellig_am,
            )
        )
    MembershipFee.objects.bulk_create(angelegt)
    return {
        "angelegt": len(angelegt),
        "uebersprungen": uebersprungen,
        "ohne_kategorie": ohne_kategorie,
        "summe": sum((fee.betrag for fee in angelegt), Decimal("0.00")),
        "jahr": jahr,
    }


@transaction.atomic
def zahlung_erfassen(fee, betrag, datum=None, art=Payment.Art.UEBERWEISUNG, notiz="", benutzer=None):
    """Bucht eine Zahlung und gleicht Status + Kassenbuch ab (M2.3b/M2.5)."""
    betrag = Decimal(str(betrag)).quantize(Decimal("0.01"))
    zahlung = Payment.objects.create(
        fee=fee,
        betrag=betrag,
        datum=datum or timezone.localdate(),
        art=art,
        notiz=notiz,
        erfasst_von=benutzer,
    )
    fee.status_aktualisieren()
    CashEntry.objects.create(
        art=CashEntry.Art.EINNAHME,
        kategorie=CashEntry.Kategorie.BEITRAEGE,
        betrag=betrag,
        datum=zahlung.datum,
        beschreibung=f"Beitrag {fee.jahr} – {fee.member}",
        belegnummer=f"BEITRAG-{fee.jahr}-{fee.member_id}",
        erfasst_von=benutzer,
    )
    return zahlung


@transaction.atomic
def mahnung_erstellen(fee, gebuehr=Decimal("0.00"), notiz="", benutzer=None):
    """Erhöht die Mahnstufe (max. 2) und protokolliert die Mahnung (M2.4)."""
    stufe = min(fee.mahnstufe + 1, 2)
    fee.mahnstufe = stufe
    fee.letzte_mahnung_am = timezone.localdate()
    fee.save(update_fields=["mahnstufe", "letzte_mahnung_am"])
    return DunningLetter.objects.create(
        fee=fee,
        stufe=stufe,
        gebuehr=Decimal(str(gebuehr or "0.00")),
        notiz=notiz,
        erstellt_von=benutzer,
    )


def mahntext(dunning):
    """Textbausteine für den Mahnbrief – abhängig von der Mahnstufe."""
    if dunning.stufe >= 2:
        return (
            "trotz unserer ersten Mahnung konnten wir keinen Zahlungseingang "
            "feststellen. Wir bitten Sie letztmalig, den offenen Betrag zu begleichen."
        )
    return (
        "sicherlich haben Sie unsere Zahlungsbitte übersehen. Wir bitten Sie "
        "freundlich, den offenen Betrag innerhalb von 14 Tagen zu überweisen."
    )
