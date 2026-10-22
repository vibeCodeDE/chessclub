"""Gruppen-E-Mail-Versand mit Opt-in-Beachtung, Protokollierung und Queue (PRD M5.2, T38)."""

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from members.models import Member

from .models import MailLog, QueuedMail


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


def process_mail_queue_batch(*, limit=50, max_retries=3, dry_run=False, mail_log=None):
    """Versendet anstehende E-Mails aus der Warteschlange blockweise.

    Reine Fachfunktion ohne HTTP-Kontext (AGENTS.md).
    Gibt ein Status-Dictionary zurück:
    {"gesendet": X, "fehlgeschlagen": Y, "dry_run": Z, "verbleibend": W}
    """
    qs = QueuedMail.objects.filter(
        status=QueuedMail.Status.PENDING,
        versuche__lt=max_retries,
    ).select_related("mail_log").order_by("erstellt_am")

    if mail_log is not None:
        qs = qs.filter(mail_log=mail_log)

    batch = list(qs[:limit] if limit is not None else qs)

    gesendet = 0
    fehlgeschlagen = 0
    dry_count = 0
    betroffene_logs = set()

    for item in batch:
        if item.mail_log:
            betroffene_logs.add(item.mail_log)

        if dry_run:
            dry_count += 1
            continue

        try:
            send_mail(
                item.betreff,
                item.text,
                settings.DEFAULT_FROM_EMAIL,
                [item.empfaenger_email],
                fail_silently=False,
            )
            item.status = QueuedMail.Status.SENT
            item.gesendet_am = timezone.now()
            item.versuche += 1
            item.fehler_meldung = ""
            item.save(update_fields=["status", "gesendet_am", "versuche", "fehler_meldung"])
            gesendet += 1
        except Exception as exc:  # noqa: BLE001 – SMTP-Fehler fangen
            item.versuche += 1
            item.fehler_meldung = str(exc)
            if item.versuche >= max_retries:
                item.status = QueuedMail.Status.FAILED
                fehlgeschlagen += 1
            item.save(update_fields=["status", "versuche", "fehler_meldung"])

    # Betroffene MailLog-Einträge aktualisieren
    if not dry_run:
        for log in betroffene_logs:
            _aktualisiere_mail_log_status(log)

    verbleibend = QueuedMail.objects.filter(
        status=QueuedMail.Status.PENDING,
        versuche__lt=max_retries,
    )
    if mail_log is not None:
        verbleibend = verbleibend.filter(mail_log=mail_log)

    return {
        "gesendet": gesendet,
        "fehlgeschlagen": fehlgeschlagen,
        "dry_run": dry_count,
        "verbleibend": verbleibend.count(),
    }


def _aktualisiere_mail_log_status(log):
    """Aktualisiert die Kennzahlen und den Gesamtstatus eines MailLogs."""
    all_queued = log.queued_mails.all()
    total = all_queued.count()
    if total == 0:
        return

    pending = all_queued.filter(status=QueuedMail.Status.PENDING).count()
    failed = all_queued.filter(status=QueuedMail.Status.FAILED).count()
    sent = all_queued.filter(status=QueuedMail.Status.SENT).count()

    log.anzahl_fehler = failed
    if pending == 0:
        if log.status == MailLog.Status.TEST:
            pass  # Test-Status bleibt erhalten
        elif failed == total:
            log.status = MailLog.Status.FEHLGESCHLAGEN
        elif failed > 0:
            log.status = MailLog.Status.TEILWEISE
        else:
            log.status = MailLog.Status.GESENDET
    elif sent > 0 or failed > 0:
        if log.status != MailLog.Status.TEST:
            log.status = MailLog.Status.TEILWEISE

    log.save(update_fields=["status", "anzahl_fehler"])


def sende_gruppenmail(
    *, betreff, text, zielgruppe, benutzer=None, test_empfaenger="", async_send=False
):
    """Reiht Gruppen-E-Mails in die Queue ein, versendet bei Bedarf sofort und schreibt das Protokoll."""
    test_adressen = [adresse.strip() for adresse in test_empfaenger.split(",") if adresse.strip()]
    adressen, uebersprungen = empfaenger_und_uebersprungene(zielgruppe)

    if test_adressen:
        ziele = test_adressen
        uebersprungen = 0
        ist_test = True
    else:
        ziele = adressen
        ist_test = False

    initial_status = (
        MailLog.Status.QUEUED
        if async_send
        else (MailLog.Status.TEST if ist_test else MailLog.Status.GESENDET)
    )

    log = MailLog.objects.create(
        betreff=betreff,
        text=text,
        zielgruppe=zielgruppe,
        anzahl_empfaenger=len(ziele),
        anzahl_uebersprungen=uebersprungen,
        anzahl_fehler=0,
        status=initial_status,
        test_empfaenger=", ".join(test_adressen),
        erstellt_von=benutzer if getattr(benutzer, "is_authenticated", False) else None,
    )

    if not ziele:
        return log

    queued_objects = [
        QueuedMail(
            mail_log=log,
            empfaenger_email=adresse,
            betreff=betreff,
            text=text,
            status=QueuedMail.Status.PENDING,
        )
        for adresse in ziele
    ]
    QueuedMail.objects.bulk_create(queued_objects)

    if not async_send:
        # Sofortiger synchroner Versand
        fehler = 0
        now = timezone.now()
        for item in log.queued_mails.all():
            try:
                send_mail(
                    item.betreff,
                    item.text,
                    settings.DEFAULT_FROM_EMAIL,
                    [item.empfaenger_email],
                    fail_silently=False,
                )
                item.status = QueuedMail.Status.SENT
                item.gesendet_am = now
                item.versuche = 1
                item.save(update_fields=["status", "gesendet_am", "versuche"])
            except Exception as exc:  # noqa: BLE001
                fehler += 1
                item.status = QueuedMail.Status.FAILED
                item.versuche = 1
                item.fehler_meldung = str(exc)
                item.save(update_fields=["status", "versuche", "fehler_meldung"])

        log.anzahl_fehler = fehler
        if fehler == len(ziele):
            log.status = MailLog.Status.FEHLGESCHLAGEN
        elif fehler > 0:
            log.status = MailLog.Status.TEILWEISE
        elif ist_test:
            log.status = MailLog.Status.TEST
        else:
            log.status = MailLog.Status.GESENDET
        log.save(update_fields=["status", "anzahl_fehler"])

    return log
