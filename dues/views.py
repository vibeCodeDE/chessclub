"""Beitragsverwaltung in der Oberfläche (PRD M2.2, M2.3, M2.4).

Die Rollenprüfung (nur Vorstand, PRD §3.8) und das Auslösen als POST liegen in
den Views; die Regelbasis des Laufs und des Zahlungsstands selbst in
:mod:`dues.services`.
"""

import csv
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import AuditLog
from core.roles import ADMIN_GROUP, role_required
from members.models import Member

from .export import beitragszeilen
from .mahnung import mahnungen_setzen, mahnstufe_text, offene_posten
from .models import FeeAmount, FeePost, Payment, SepaMandate
from .services import (
    PostenStatus,
    eur,
    fuehre_lauf,
    plan_lauf,
    posten_mit_status,
    posten_status,
)

# Jahresangaben werden auf plausible Beitragsjahre begrenzt, damit ein
# Tippfehler nicht in einer leeren Abfrage landet.
MIN_JAHR = 2000
MAX_JAHR = 2100


def _parse_jahr(roh):
    if roh is None:
        return None
    try:
        jahr = int(str(roh).strip())
    except (TypeError, ValueError):
        return None
    return jahr if MIN_JAHR <= jahr <= MAX_JAHR else None


def _aktives_jahr():
    return timezone.localdate().year


def _jahre():
    """Jahre, die im Auswahlfeld sinnvoll sind: Sätze, Posten, aktuelles Jahr."""
    saetze = FeeAmount.objects.values_list("jahr", flat=True)
    posten = FeePost.objects.values_list("jahr", flat=True)
    return sorted({*saetze, *posten, _aktives_jahr()}, reverse=True)


def _ist_angehakt(querystring):
    return querystring.get("passiv") in ("1", "on", "true", "ja")


def _liste_und_jahr(jahr):
    # reverse() nimmt keinen Query-String mit, deshalb wird der Pfad gebaut.
    return f"{reverse('dues:posten_liste')}?jahr={jahr}"


def _zahlungen_und_jahr(jahr):
    return f"{reverse('dues:zahlungsliste')}?jahr={jahr}"


def _betrag(roh):
    """Deutsches Zahlenformat aus dem Formular („90,00“ -> Decimal)."""
    if roh is None:
        return None
    text = str(roh).strip().replace("€", "").replace(" ", "").replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ArithmeticError):
        return None


def _datum(roh):
    """Datum aus dem Formular; None, wenn es unlesbar ist."""
    if not roh:
        return timezone.localdate()
    try:
        return date.fromisoformat(str(roh).strip())
    except ValueError:
        return None


def _datum_leer(roh):
    """Optionales Datum aus dem Formular: leer bleibt leer (die Frist ist freiwillig)."""
    if not str(roh or "").strip():
        return None
    return _datum(roh)


@role_required(ADMIN_GROUP)
def posten_liste(request):
    """Posten eines Jahres plus die Vorschau, was ein Lauf dort erzeugen würde."""
    jahr = _parse_jahr(request.GET.get("jahr"))
    if jahr is None:
        if request.GET.get("jahr") is not None:
            # Unlesbare Jahresangabe: zurück auf die Übersicht ohne Filter.
            return redirect("dues:posten_liste")
        jahr = _aktives_jahr()
    passiv_einbezogen = _ist_angehakt(request.GET)

    context = {
        "jahr": jahr,
        "jahre": _jahre(),
        "passiv_einbezogen": passiv_einbezogen,
        # plan_lauf schreibt nichts — die Vorschau ist gefahrlos aufrufbar.
        "plan": plan_lauf(jahr, passiv_einbezogen=passiv_einbezogen),
        # posten_mit_status liefert den Zahlungsstand in derselben Abfrage.
        "posts": posten_mit_status(jahr),
    }
    return render(request, "dues/posten_liste.html", context)


@role_required(ADMIN_GROUP)
@require_POST
def beitragslauf(request):
    """Beitragslauf auslösen (PRD M2.2) — idempotent, siehe :mod:`dues.services`."""
    jahr = _parse_jahr(request.POST.get("jahr"))
    if jahr is None:
        messages.error(request, "Bitte ein gültiges Beitragsjahr wählen.")
        return redirect("dues:posten_liste")

    try:
        plan = fuehre_lauf(
            jahr, benutzer=request.user, passiv_einbezogen=_ist_angehakt(request.POST)
        )
    except ValidationError as exc:
        messages.error(
            request,
            "Der Beitragslauf wurde abgebrochen: " + " ".join(exc.messages),
        )
        return redirect(_liste_und_jahr(jahr))

    if plan.posten:
        messages.success(
            request,
            f"Beitragslauf {jahr}: {len(plan.posten)} Beitragsposten über "
            f"{eur(plan.summe_neu)} erzeugt.",
        )
    else:
        messages.info(
            request,
            f"Beitragslauf {jahr}: nichts Neues erzeugt — "
            f"{plan.anzahl_vorhanden} Posten sind bereits vorhanden.",
        )
    return redirect(_liste_und_jahr(jahr))


def _zahlungs_context(jahr, formular=None, gewaehlt=None):
    """Kontext der Zahlungsseite — geteilt von Liste, Buchung und Fehlerfall."""
    return {
        "jahr": jahr,
        "jahre": _jahre(),
        "zahlungen": Payment.objects.filter(post__jahr=jahr).select_related(
            "post", "post__member", "erfasst_von"
        ),
        "posten": posten_mit_status(jahr),
        "mandate": SepaMandate.objects.select_related("member"),
        "gewaehlt": gewaehlt,
        "formular": formular or {},
        "art_choices": Payment.Art.choices,
        "mandat_status_choices": SepaMandate.Status.choices,
        "mitglieder": Member.objects.exclude(
            status=Member.Status.AUSGETRETEN
        ).order_by("nachname", "vorname"),
    }


@role_required(ADMIN_GROUP)
def zahlungsliste(request):
    """Zahlungen buchen und SEPA-Mandate verwalten (PRD M2.3, M2.4)."""
    jahr = _parse_jahr(request.GET.get("jahr")) or _aktives_jahr()
    posten = posten_mit_status(jahr)

    gewaehlt = None
    gewaehlt_pk = (request.GET.get("posten") or "").strip()
    if gewaehlt_pk.isdigit():
        gesucht = int(gewaehlt_pk)
        gewaehlt = next((z for z in posten if z["post"].pk == gesucht), None)
    formular = {
        "post": gewaehlt["post"].pk if gewaehlt else "",
        "betrag": gewaehlt["offen"] if gewaehlt else "",
        "art": Payment.Art.UEBERWEISUNG,
        "datum": "",
        "referenz": "",
        "notiz": "",
    }
    return render(
        request, "dues/zahlungen.html", _zahlungs_context(jahr, formular, gewaehlt)
    )


@role_required(ADMIN_GROUP)
@require_POST
def zahlung_buchen(request):
    """Bucht eine Zahlung auf einen Beitragsposten.

    Bei einem Fehler wird die Seite mit den eingegebenen Werten erneut
    gerendert (kein Redirect) — sonst verlöre der Vorstand die Eingabe.
    """
    jahr = _parse_jahr(request.POST.get("jahr")) or _aktives_jahr()
    formular = {
        "post": request.POST.get("post", ""),
        "betrag": request.POST.get("betrag", ""),
        "art": request.POST.get("art", Payment.Art.UEBERWEISUNG),
        "datum": request.POST.get("datum", ""),
        "referenz": request.POST.get("referenz", ""),
        "notiz": request.POST.get("notiz", ""),
    }

    post = FeePost.objects.filter(pk=formular["post"]).select_related("member").first()
    betrag = _betrag(formular["betrag"])
    datum = _datum(formular["datum"])
    art = formular["art"] if formular["art"] in dict(Payment.Art.choices) else None
    if post is None or betrag is None or datum is None or art is None:
        messages.error(request, "Bitte Beitragsposten, Betrag, Datum und Zahlungsart prüfen.")
        return render(
            request, "dues/zahlungen.html", _zahlungs_context(jahr, formular)
        )

    try:
        with transaction.atomic():
            payment = Payment(
                post=post,
                betrag=betrag,
                art=art,
                datum=datum,
                referenz=formular["referenz"],
                notiz=formular["notiz"],
                erfasst_von=request.user,
            )
            payment.full_clean()
            payment.save()
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Zahlung gebucht",
                text=(
                    f"{post.jahr} · {post.member}: {payment.get_art_display()} "
                    f"{eur(payment.betrag)} am {payment.datum.isoformat()}"
                ),
                member=post.member,
            )
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return render(
            request, "dues/zahlungen.html", _zahlungs_context(jahr, formular)
        )

    messages.success(
        request,
        f"Zahlung über {eur(betrag)} gebucht — Posten jetzt: "
        f"{PostenStatus(posten_status(post)).label}.",
    )
    return redirect(_zahlungen_und_jahr(post.jahr))


@role_required(ADMIN_GROUP)
@require_POST
def zahlung_stornieren(request, pk):
    """Hebt eine Fehlbuchung per Gegenbuchung auf — Löschen gibt es nicht."""
    original = get_object_or_404(
        Payment.objects.select_related("post", "post__member"), pk=pk
    )
    if original.storno_von_id is not None:
        messages.error(
            request, f"Zahlung #{original.pk} ist selbst eine Gegenbuchung."
        )
        return redirect(_zahlungen_und_jahr(original.post.jahr))

    with transaction.atomic():
        storno = Payment.objects.create(
            post=original.post,
            betrag=-original.betrag,
            art=original.art,
            datum=timezone.localdate(),
            storno_von=original,
            notiz=f"Storno zu #{original.pk}",
            erfasst_von=request.user,
        )
        AuditLog.objects.create(
            benutzer=request.user,
            aktion="Zahlung storniert",
            text=(
                f"Storno zu #{original.pk} über {eur(storno.betrag)} "
                f"am {storno.datum.isoformat()}"
            ),
            member=original.post.member,
        )
    messages.success(
        request, f"Zahlung #{original.pk} storniert — der Beitragsposten ist wieder offen."
    )
    return redirect(_zahlungen_und_jahr(original.post.jahr))


@role_required(ADMIN_GROUP)
@require_POST
def mandat_anlegen(request):
    """SEPA-Mandat anlegen (PRD M2.3) — ohne IBAN, der Einzug läuft über die Bank."""
    member = get_object_or_404(Member, pk=request.POST.get("member"))
    referenz = request.POST.get("referenz", "").strip()
    datum = _datum(request.POST.get("datum")) or timezone.localdate()
    if not referenz:
        messages.error(request, "Bitte eine Mandatsreferenz angeben.")
        return redirect(_zahlungen_und_jahr(_aktives_jahr()))
    try:
        with transaction.atomic():
            mandat = SepaMandate(
                member=member,
                referenz=referenz,
                datum=datum,
                status=SepaMandate.Status.AKTIV,
                notiz=request.POST.get("notiz", ""),
            )
            mandat.full_clean()
            mandat.save()
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="SEPA-Mandat angelegt",
                text=f"Referenz {mandat.referenz} ab {mandat.datum.isoformat()}",
                member=member,
            )
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect(_zahlungen_und_jahr(_aktives_jahr()))
    messages.success(request, f"SEPA-Mandat {mandat.referenz} für {member} angelegt.")
    return redirect(_zahlungen_und_jahr(_aktives_jahr()))


@role_required(ADMIN_GROUP)
@require_POST
def mandat_status(request, pk):
    """Mandat aktiv/widerrufen/beendet setzen — mit Alt/Neu im Audit-Log."""
    mandat = get_object_or_404(SepaMandate.objects.select_related("member"), pk=pk)
    status = request.POST.get("status", "")
    if status not in dict(SepaMandate.Status.choices):
        messages.error(request, "Unbekannter Mandatsstatus.")
        return redirect(_zahlungen_und_jahr(_aktives_jahr()))
    if mandat.status == status:
        messages.info(request, f"Mandat {mandat.referenz} ist bereits „{status}“.")
        return redirect(_zahlungen_und_jahr(_aktives_jahr()))

    vorher = mandat.status
    mandat.status = status
    mandat.save(update_fields=["status"])
    AuditLog.objects.create(
        benutzer=request.user,
        aktion="SEPA-Mandat geändert",
        text=f"Referenz {mandat.referenz}",
        feld="status",
        alt_wert=vorher,
        neu_wert=status,
        member=mandat.member,
    )
    messages.success(request, f"Mandat {mandat.referenz}: Status {status}.")
    return redirect(_zahlungen_und_jahr(_aktives_jahr()))


def _mahnungen_und_jahr(jahr):
    return f"{reverse('dues:mahnliste')}?jahr={jahr}"


@role_required(ADMIN_GROUP)
def mahnliste(request):
    """Offene Beiträge eines Jahres — Grundlage für Mahnung und Brief (PRD M2.5)."""
    jahr = _parse_jahr(request.GET.get("jahr"))
    if jahr is None:
        if request.GET.get("jahr") is not None:
            return redirect("dues:mahnliste")
        jahr = _aktives_jahr()

    zeilen = offene_posten(jahr)
    return render(
        request,
        "dues/mahnliste.html",
        {
            "jahr": jahr,
            "jahre": _jahre(),
            "zeilen": zeilen,
            "summe_offen": sum((z["offen"] for z in zeilen), Decimal("0.00")),
        },
    )


@role_required(ADMIN_GROUP)
@require_POST
def mahnung_setzen(request, pk):
    """Setzt die nächste Mahnung für einen Beitragsposten (PRD M2.5).

    Die Prüfungen liegen in `dues.mahnung.mahnungen_setzen`; hier wird nur
    übersetzt und eine verständliche Meldung gezeigt.
    """
    post = get_object_or_404(
        FeePost.objects.select_related("member", "kategorie"), pk=pk
    )
    stufe = request.POST.get("stufe", "")
    stufe = int(stufe) if stufe in ("1", "2") else None
    datum = _datum(request.POST.get("datum"))
    frist = _datum_leer(request.POST.get("frist"))

    try:
        mahnung = mahnungen_setzen(
            post,
            stufe,
            datum,
            frist=frist,
            benutzer=request.user,
            notiz=request.POST.get("notiz", ""),
        )
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect(_mahnungen_und_jahr(post.jahr))

    messages.success(
        request,
        f"{mahnstufe_text(mahnung.stufe)} für {post.member} gesetzt "
        f"(Datum {mahnung.datum.strftime('%d.%m.%Y')}).",
    )
    return redirect(_mahnungen_und_jahr(post.jahr))


@role_required(ADMIN_GROUP)
def beitraege_export(request):
    """CSV der Jahresbeiträge (PRD M2.5).

    Kein Audit-Eintrag: der Export ist eine Leseaktion. Protokolliert wird er
    laut PRD mit dem Auskunfts-Export in T23, dort mit Person und Zweck.
    """
    jahr = _parse_jahr(request.GET.get("jahr")) or _aktives_jahr()
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="beitraege_{jahr}.csv"'
    response.write("\ufeff")  # BOM für Excel
    writer = csv.writer(response, delimiter=";")
    for zeile in beitragszeilen(jahr):
        writer.writerow(zeile)
    return response
