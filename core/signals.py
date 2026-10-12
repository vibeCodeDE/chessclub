from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from members.models import Member

from .models import AuditLog

AUDIT_FELDER = [f for f in Member._meta.concrete_fields if f.name != "id"]


def _wert(value):
    return "" if value is None else str(value)


@receiver(pre_save, sender=Member)
def stammdaten_altwerte_ablesen(sender, instance, **kwargs):
    if instance.pk is None or getattr(instance, "_is_anonymizing", False):
        return
    zeile = (
        sender.objects.filter(pk=instance.pk)
        .values(*(feld.attname for feld in AUDIT_FELDER))
        .first()
    )
    instance._audit_alt_werte = dict(zeile) if zeile else {}


@receiver(post_save, sender=Member)
def stammdaten_anderungen_protokollieren(sender, instance, created, **kwargs):
    if created or getattr(instance, "_is_anonymizing", False) or not hasattr(instance, "_audit_alt_werte"):
        return
    alt_werte = instance._audit_alt_werte
    benutzer = getattr(instance, "_changed_by", None)
    for feld in AUDIT_FELDER:
        alt = alt_werte.get(feld.attname)
        neu = getattr(instance, feld.attname)
        if alt == neu:
            continue
        AuditLog.objects.create(
            benutzer=benutzer,
            aktion="Stammdaten geändert",
            feld=feld.name,
            alt_wert=_wert(alt),
            neu_wert=_wert(neu),
            member=instance,
        )


def _ip(request):
    if request is None:
        return "—"
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "—")


@receiver(user_logged_in)
def login_protokollieren(request, user, **kwargs):
    AuditLog.objects.create(
        benutzer=user,
        aktion="Anmeldung",
        text=f"IP: {_ip(request)}",
    )


@receiver(user_logged_out)
def logout_protokollieren(request, user, **kwargs):
    if user is None or not user.is_authenticated:
        return
    AuditLog.objects.create(
        benutzer=user,
        aktion="Abmeldung",
        text=f"IP: {_ip(request)}",
    )


@receiver(user_login_failed)
def login_abgelehnt_protokollieren(request, credentials, **kwargs):
    AuditLog.objects.create(
        benutzer=None,
        aktion="Anmeldung abgelehnt",
        text=f"Benutzer: {credentials.get('username', '—')} · IP: {_ip(request)}",
    )
