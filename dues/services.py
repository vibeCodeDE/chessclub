"""Fachlogik Beitragswesen: Beitragslauf, Zahlungen, Mahnwesen (PRD M2)."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from cashbook.models import CashEntry, storniere_kassenbuchung

from .models import DunningLetter, FeeAmount, MembershipFee, Payment

STANDARD_FAELLIGKEIT = date(2000, 1, 31)  # Platzhalter; Jahr wird ersetzt


def _faelligkeit(jahr):
    return date(jahr, 1, 31)


@transaction.atomic
def beitragslauf(jahr, faellig_am=None, benutzer=None):
    """Erzeugt Beitragsposten für alle aktiven Mitglieder mit Kategorie (M2.2, ADR-004, ADR-005).

    Idempotent: ein zweiter Lauf für dasselbe Jahr legt nichts doppelt an.
    Bricht ab, wenn für eine Kategorie im angegebenen Jahr kein Beitragssatz hinterlegt ist.
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

    zu_verarbeitende_kategorien = {
        member.beitragskategorie for member in mitglieder if member.pk not in vorhandene
    }
    saetze = {
        fa.kategorie_id: fa.betrag
        for fa in FeeAmount.objects.filter(
            kategorie__in=zu_verarbeitende_kategorien, jahr=jahr
        )
    }
    fehlende = [
        kat.name
        for kat in sorted(zu_verarbeitende_kategorien, key=lambda k: k.name)
        if kat.pk not in saetze
    ]
    if fehlende:
        namen = ", ".join(f"„{name}“" for name in fehlende)
        raise ValidationError(
            f"Für das Beitragsjahr {jahr} ist für folgende Beitragskategorie(n) kein Beitragssatz hinterlegt: {namen}."
        )

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
                betrag=saetze[kategorie.pk],
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
    zahlungsdatum = datum or timezone.localdate()
    kassenbuchung = CashEntry.objects.create(
        art=CashEntry.Art.EINNAHME,
        kategorie=CashEntry.Kategorie.BEITRAEGE,
        betrag=betrag,
        datum=zahlungsdatum,
        beschreibung=f"Beitrag {fee.jahr} – {fee.member}",
        belegnummer=f"BEITRAG-{fee.jahr}-{fee.member_id}",
        erfasst_von=benutzer,
    )
    zahlung = Payment.objects.create(
        fee=fee,
        betrag=betrag,
        datum=zahlungsdatum,
        art=art,
        notiz=notiz,
        kassenbuchung=kassenbuchung,
        erfasst_von=benutzer,
    )
    fee.status_aktualisieren()
    return zahlung


@transaction.atomic
def zahlung_stornieren(zahlung, *, grund="", datum=None, benutzer=None):
    """Storniert eine Beitragszahlung per Gegenbuchung inkl. Kassenbuch und Audit-Log."""
    from core.models import AuditLog

    if zahlung.ist_storno:
        raise ValidationError("Eine Storno-Gegenbuchung kann nicht erneut storniert werden.")
    if zahlung.ist_storniert:
        raise ValidationError("Diese Zahlung wurde bereits storniert.")

    fee = zahlung.fee
    storno_datum = datum or zahlung.datum
    zusatz = f": {grund}" if grund else ""
    notiz = f"Storno zu Zahlung #{zahlung.pk}{zusatz}"[:200]

    kassen_storno = None
    ursprungs_kasse = zahlung.kassenbuchung
    if ursprungs_kasse is None:
        ursprungs_kasse = (
            CashEntry.objects.filter(
                art=CashEntry.Art.EINNAHME,
                kategorie=CashEntry.Kategorie.BEITRAEGE,
                betrag=zahlung.betrag,
                belegnummer=f"BEITRAG-{fee.jahr}-{fee.member_id}",
                storno_von__isnull=True,
                storno_buchung__isnull=True,
            )
            .order_by("-pk")
            .first()
        )
    if ursprungs_kasse is not None and not ursprungs_kasse.ist_storniert:
        kassen_grund = grund or f"Storno Beitragszahlung #{zahlung.pk}"
        kassen_storno = storniere_kassenbuchung(
            ursprungs_kasse, benutzer=benutzer, grund=kassen_grund, datum=storno_datum
        )

    gegenbuchung = Payment.objects.create(
        fee=fee,
        betrag=-zahlung.betrag,
        datum=storno_datum,
        art=zahlung.art,
        notiz=notiz,
        storno_von=zahlung,
        kassenbuchung=kassen_storno,
        erfasst_von=benutzer,
    )
    fee.status_aktualisieren()
    AuditLog.objects.create(
        benutzer=benutzer,
        aktion="Zahlung storniert",
        text=f"Storno zu Zahlung #{zahlung.pk} ({zahlung.betrag:.2f} €) für {fee.member} ({fee.jahr}){zusatz}",
        member=fee.member,
    )
    return gegenbuchung


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
