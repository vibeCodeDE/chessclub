"""Gruppen-E-Mail-Versand mit Opt-in-Beachtung und Protokollierung (PRD M5.2)."""

from django.conf import settings
from django.core.mail import send_mail

from members.models import Member

from .models import MailLog


def empfaenger_queryset(zielgruppe):
    """Basis-Menge der angeschriebenen Mitglieder (ohne Ausgetretene)."""
    basis = Member.objects.exclude(status=Member.Status.AUSGETRETEN)
    if zielgruppe == MailLog.Zielgruppe.AKTIV:
        basis = basis.filter(status=Member.Status.AKTIV)
    elif zielgruppe == MailLog.Zielgruppe.PASSIV:
        basis = basis.filter(status=Member.Status.PASSIV)
    elif zielgruppe == MailLog.Zielgruppe.VORSTAND:
        basis = basis.filter(user__groups__name="admin")
    elif zielgruppe == MailLog.Zielgruppe.KAPITAENE:
        basis = basis.filter(user__groups__name="kapitaen")
    return basis.distinct()


def empfaenger_und_uebersprungene(zielgruppe):
    """Trennt Empfänger:innen mit Opt-in von denen ohne Einwilligung/E-Mail."""
    basis = list(empfaenger_queryset(zielgruppe).order_by("nachname", "vorname"))
    adressen = [m.email for m in basis if m.email_opt_in and m.email]
    return adressen, len(basis) - len(adressen)


def sende_gruppenmail(*, betreff, text, zielgruppe, benutzer=None, test_empfaenger=""):
    """Versendet einzeln (kein offenes An-Feld) und schreibt das Protokoll."""
    test_adressen = [adresse.strip() for adresse in test_empfaenger.split(",") if adresse.strip()]
    adressen, uebersprungen = empfaenger_und_uebersprungene(zielgruppe)

    if test_adressen:
        ziele, uebersprungen = test_adressen, 0
        status = MailLog.Status.TEST
    else:
        ziele = adressen
        status = MailLog.Status.GESENDET

    fehler = 0
    for adresse in ziele:
        try:
            send_mail(betreff, text, settings.DEFAULT_FROM_EMAIL, [adresse], fail_silently=False)
        except Exception:  # noqa: BLE001 – ein Fehler darf den Rest nicht stoppen
            fehler += 1

    if ziele and fehler == len(ziele):
        status = MailLog.Status.FEHLGESCHLAGEN
    elif fehler:
        status = MailLog.Status.TEILWEISE

    return MailLog.objects.create(
        betreff=betreff,
        text=text,
        zielgruppe=zielgruppe,
        anzahl_empfaenger=len(ziele),
        anzahl_uebersprungen=uebersprungen,
        anzahl_fehler=fehler,
        status=status,
        test_empfaenger=", ".join(test_adressen),
        erstellt_von=benutzer if getattr(benutzer, "is_authenticated", False) else None,
    )
