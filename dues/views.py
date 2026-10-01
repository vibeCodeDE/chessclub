"""Beitragsverwaltung: Übersicht, Beitragslauf, Zahlungen, Mahnwesen, Mandate."""

import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.roles import ADMIN_GROUP, role_required
from core.ui import fehler, is_ajax, ok, paginate
from members.models import Member

from .forms import (
    BeitragslaufForm,
    DunningForm,
    FeeCategoryForm,
    PaymentForm,
    SepaMandateForm,
)
from .models import (
    DunningLetter,
    FeeCategory,
    MembershipFee,
    Payment,
    SepaMandate,
    jahres_uebersicht,
)
from .services import (
    beitragslauf,
    mahntext,
    mahnung_erstellen,
    zahlung_erfassen,
    zahlung_stornieren,
)


def _jahr_aus_request(request):
    jahr = request.GET.get("jahr", "")
    if jahr.isdigit():
        return int(jahr)
    letztes = MembershipFee.objects.order_by("-jahr").values_list("jahr", flat=True).first()
    return letztes or timezone.localdate().year


@role_required(ADMIN_GROUP)
def overview(request):
    jahr = _jahr_aus_request(request)
    status = request.GET.get("status", "")
    suche = request.GET.get("q", "").strip()
    posten = (
        MembershipFee.objects.filter(jahr=jahr)
        .select_related("member", "member__beitragskategorie")
        .prefetch_related("zahlungen")
    )
    if suche:
        posten = posten.filter(
            Q(member__nachname__icontains=suche)
            | Q(member__vorname__icontains=suche)
            | Q(kategorie_name__icontains=suche)
        )
    if status == "offen":
        posten = [fee for fee in posten if fee.ist_offen]
    elif status == "bezahlt":
        posten = [fee for fee in posten if not fee.ist_offen]
    jahre = sorted(
        set(MembershipFee.objects.values_list("jahr", flat=True)) | {timezone.localdate().year},
        reverse=True,
    )
    kontext = {
        "jahr": jahr,
        "jahre": jahre,
        "uebersicht": jahres_uebersicht(jahr),
        "posten": paginate(posten, request, per_page=25),
        "status": status,
        "q": suche,
        "lauf_form": BeitragslaufForm(initial={"jahr": jahr}),
        "anzahl_ohne_kategorie": Member.objects.filter(
            status=Member.Status.AKTIV, beitragskategorie__isnull=True
        ).count(),
        "anzahl_aktive": Member.objects.filter(status=Member.Status.AKTIV).count(),
        "kategorien": FeeCategory.objects.all(),
    }
    return render(request, "dues/overview.html", kontext)


@role_required(ADMIN_GROUP)
def fee_detail(request, pk):
    fee = get_object_or_404(
        MembershipFee.objects.select_related("member").prefetch_related("zahlungen", "mahnungen"), pk=pk
    )
    kontext = {
        "fee": fee,
        "form": PaymentForm(fee=fee),
        "dunning_form": DunningForm(),
        "zahlungen": fee.zahlungen.select_related("erfasst_von"),
        "mahnungen": fee.mahnungen.select_related("erstellt_von"),
    }
    return render(request, "dues/fee_detail.html", kontext)


@role_required(ADMIN_GROUP)
@require_POST
def payment_create(request, pk):
    fee = get_object_or_404(MembershipFee.objects.select_related("member"), pk=pk)
    form = PaymentForm(request.POST, fee=fee)
    if not form.is_valid():
        if not is_ajax(request):
            messages.error(request, "Zahlung konnte nicht gebucht werden: " + "; ".join(
                f"{feld}: {', '.join(fehler)}" for feld, fehler in form.errors.items()
            ))
            return redirect("dues:fee_detail", pk=fee.pk)
        return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    zahlung = zahlung_erfassen(
        fee,
        betrag=form.cleaned_data["betrag"],
        datum=form.cleaned_data["datum"],
        art=form.cleaned_data["art"],
        notiz=form.cleaned_data["notiz"],
        benutzer=request.user,
    )
    fee.refresh_from_db()
    if not is_ajax(request):
        messages.success(request, f"Zahlung über {zahlung.betrag:.2f} € gebucht.")
        return redirect("dues:fee_detail", pk=fee.pk)
    zeilen_html = "".join(
        f"<tr><td class='nowrap'>{z.datum:%d.%m.%Y}</td><td class='mono'>{z.betrag:.2f} €</td>"
        f"<td>{z.get_art_display()}</td><td class='cell-sub'>{z.notiz or '–'}</td></tr>"
        for z in fee.zahlungen.all()
    ) or "<tr><td colspan='4' class='muted'>Noch keine Zahlungen erfasst.</td></tr>"
    return ok(
        message=f"Zahlung über {zahlung.betrag:.2f} € gebucht.",
        patch={
            f"[data-fee-status='{fee.pk}']": fee.get_status_display(),
            f"[data-fee-open='{fee.pk}']": f"{fee.offener_betrag:.2f} €",
            f"[data-fee-paid='{fee.pk}']": f"{fee.bezahlter_betrag:.2f} €",
            "[data-payment-total]": f"{fee.bezahlter_betrag:.2f} €",
            "[data-payment-open]": f"{fee.offener_betrag:.2f} €",
        },
        html={"[data-payment-rows]": zeilen_html},
        classes={
            f"[data-fee-badge='{fee.pk}']": {
                "add": [f"badge-{fee.status}"],
                "remove": [f"badge-{wert}" for wert in MembershipFee.Status.values],
            }
        },
    )


@role_required(ADMIN_GROUP)
@require_POST
def payment_storno(request, pk):
    """Storniert eine Beitragszahlung per Gegenbuchung inkl. Kassenbuch und Statusabgleich."""
    zahlung = get_object_or_404(Payment.objects.select_related("fee", "fee__member"), pk=pk)
    fee = zahlung.fee
    grund = request.POST.get("grund", "").strip()
    try:
        zahlung_stornieren(zahlung, grund=grund, benutzer=request.user)
    except ValidationError as exc:
        hinweis = " ".join(exc.messages)
        if is_ajax(request):
            return fehler(hinweis)
        messages.error(request, hinweis)
        return redirect("dues:fee_detail", pk=fee.pk)

    fee.refresh_from_db()
    nachricht = f"Zahlung über {zahlung.betrag:.2f} € wurde per Gegenbuchung storniert."
    if not is_ajax(request):
        messages.success(request, nachricht)
        return redirect("dues:fee_detail", pk=fee.pk)
    zeilen_html = "".join(
        f"<tr><td class='nowrap'>{z.datum:%d.%m.%Y}</td><td class='mono'>{z.betrag:.2f} €</td>"
        f"<td>{z.get_art_display()}</td><td class='cell-sub'>{z.notiz or '–'}</td></tr>"
        for z in fee.zahlungen.all()
    ) or "<tr><td colspan='4' class='muted'>Noch keine Zahlungen erfasst.</td></tr>"
    return ok(
        message=nachricht,
        patch={
            f"[data-fee-status='{fee.pk}']": fee.get_status_display(),
            f"[data-fee-open='{fee.pk}']": f"{fee.offener_betrag:.2f} €",
            f"[data-fee-paid='{fee.pk}']": f"{fee.bezahlter_betrag:.2f} €",
            "[data-payment-total]": f"{fee.bezahlter_betrag:.2f} €",
            "[data-payment-open]": f"{fee.offener_betrag:.2f} €",
        },
        html={"[data-payment-rows]": zeilen_html},
        classes={
            f"[data-fee-badge='{fee.pk}']": {
                "add": [f"badge-{fee.status}"],
                "remove": [f"badge-{wert}" for wert in MembershipFee.Status.values],
            }
        },
    )


@role_required(ADMIN_GROUP)
@require_POST
def dunning_create(request, pk):
    fee = get_object_or_404(MembershipFee, pk=pk)
    if not fee.ist_offen:
        return fehler("Für diesen Posten ist nichts offen – keine Mahnung nötig.")
    form = DunningForm(request.POST)
    if not form.is_valid():
        if not is_ajax(request):
            messages.error(request, "Mahngebühr bitte prüfen.")
            return redirect("dues:overview")
        return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    dunning = mahnung_erstellen(
        fee,
        gebuehr=form.cleaned_data.get("gebuehr") or Decimal("0.00"),
        notiz=form.cleaned_data.get("notiz", ""),
        benutzer=request.user,
    )
    if not is_ajax(request):
        messages.success(request, f"{dunning.stufe}. Mahnung für {fee.member} erstellt.")
        return redirect("dues:overview")
    return ok(
        message=f"{dunning.stufe}. Mahnung für {fee.member} erstellt.",
        patch={
            f"[data-mahnstufe='{fee.pk}']": f"{dunning.stufe}. Mahnung",
            "[data-dunning-count]": str(MembershipFee.objects.filter(mahnstufe__gt=0).count()),
        },
        classes={f"[data-mahn-badge='{fee.pk}']": {"add": ["badge-mahnung"], "remove": ["badge-neutral"]}},
    )


@role_required(ADMIN_GROUP)
def dunning_letter(request, pk):
    fee = get_object_or_404(MembershipFee.objects.select_related("member"), pk=pk)
    dunning = fee.mahnungen.first()
    stufe = dunning.stufe if dunning else max(fee.mahnstufe, 1)
    kontext = {
        "fee": fee,
        "member": fee.member,
        "stufe": stufe,
        "text": mahntext(type("D", (), {"stufe": stufe})()),
        "heute": timezone.localdate(),
        "gebuehr": dunning.gebuehr if dunning else Decimal("0.00"),
        "mandat": getattr(fee.member, "sepa_mandat", None),
    }
    return render(request, "dues/mahnbrief.html", kontext)


@role_required(ADMIN_GROUP)
def dunning_list(request):
    posten = [
        fee
        for fee in MembershipFee.objects.select_related("member")
        .prefetch_related("zahlungen", "mahnungen")
        .order_by("member__nachname")
        if fee.ist_offen and fee.faellig_am <= timezone.localdate()
    ]
    kontext = {
        "posten": posten,
        "mahnungen": DunningLetter.objects.select_related("fee__member", "erstellt_von")[:20],
        "summe_offen": sum((fee.offener_betrag for fee in posten), Decimal("0.00")),
    }
    return render(request, "dues/dunning_list.html", kontext)


@role_required(ADMIN_GROUP)
@require_POST
def run_beitragslauf(request):
    form = BeitragslaufForm(request.POST)
    if not form.is_valid():
        if not is_ajax(request):
            messages.error(request, "Bitte Jahr und Fälligkeit prüfen.")
            return redirect("dues:overview")
        return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    try:
        ergebnis = beitragslauf(
            form.cleaned_data["jahr"],
            faellig_am=form.cleaned_data["faellig_am"],
            benutzer=request.user,
        )
    except ValidationError as e:
        msg = e.message if hasattr(e, "message") else ", ".join(e.messages) if hasattr(e, "messages") else str(e)
        if not is_ajax(request):
            messages.error(request, msg)
            return redirect("dues:overview")
        return fehler(msg)
    nachricht = (
        f"Beitragslauf {ergebnis['jahr']}: {ergebnis['angelegt']} Posten über "
        f"{ergebnis['summe']:.2f} € angelegt."
    )
    if ergebnis["uebersprungen"]:
        nachricht += f" {ergebnis['uebersprungen']} Mitglieder hatten bereits einen Posten."
    if ergebnis["ohne_kategorie"]:
        nachricht += f" {ergebnis['ohne_kategorie']} aktive Mitglieder ohne Beitragskategorie wurden übersprungen."
    if not is_ajax(request):
        messages.success(request, nachricht)
        return redirect("dues:overview")
    return ok(message=nachricht, reload=True)


@role_required(ADMIN_GROUP)
def category_list(request):
    if request.method == "POST":
        form = FeeCategoryForm(request.POST)
        if form.is_valid():
            kategorie = form.save()
            if is_ajax(request):
                return ok(message=f"Kategorie „{kategorie.name}“ gespeichert.", reload=True)
            messages.success(request, f"Kategorie „{kategorie.name}“ gespeichert.")
            return redirect("dues:category_list")
        if is_ajax(request):
            return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    else:
        form = FeeCategoryForm()
    kontext = {
        "kategorien": FeeCategory.objects.all(),
        "form": form,
        "aktive_mitglieder": Member.objects.filter(status=Member.Status.AKTIV).count(),
    }
    return render(request, "dues/category_list.html", kontext)


@role_required(ADMIN_GROUP)
def category_update(request, pk):
    kategorie = get_object_or_404(FeeCategory, pk=pk)
    if request.method == "POST":
        form = FeeCategoryForm(request.POST, instance=kategorie)
        if form.is_valid():
            form.save()
            messages.success(request, f"Kategorie „{kategorie.name}“ aktualisiert.")
            return redirect("dues:category_list")
    else:
        form = FeeCategoryForm(instance=kategorie)
    return render(
        request,
        "dues/category_form.html",
        {"form": form, "kategorie": kategorie},
    )


@role_required(ADMIN_GROUP)
@require_POST
def category_toggle(request, pk):
    kategorie = get_object_or_404(FeeCategory, pk=pk)
    kategorie.aktiv = not kategorie.aktiv
    kategorie.save(update_fields=["aktiv"])
    return ok(
        message=f"„{kategorie.name}“ ist jetzt {'aktiv' if kategorie.aktiv else 'inaktiv'}.",
        checked=kategorie.aktiv,
        patch={f"[data-kategorie-status='{kategorie.pk}']": "Aktiv" if kategorie.aktiv else "Inaktiv"},
        classes={
            f"[data-kategorie-badge='{kategorie.pk}']": {
                "add": ["badge-aktiv" if kategorie.aktiv else "badge-neutral"],
                "remove": ["badge-aktiv", "badge-neutral"],
            }
        },
    )


@role_required(ADMIN_GROUP)
@require_POST
def category_delete(request, pk):
    kategorie = get_object_or_404(FeeCategory, pk=pk)
    if kategorie.mitglieder.exists():
        return fehler(
            f"„{kategorie.name}“ ist noch {kategorie.mitglieder.count()} Mitgliedern zugeordnet – bitte erst umbuchen."
        )
    name = kategorie.name
    kategorie.delete()
    return ok(message=f"Kategorie „{name}“ gelöscht.", remove_selector=f"[data-row='kategorie-{pk}']")


@role_required(ADMIN_GROUP)
def mandate_list(request):
    mandate = SepaMandate.objects.select_related("member")
    ohne_mandat = (
        Member.objects.filter(status=Member.Status.AKTIV, sepa_mandat__isnull=True)
        .order_by("nachname")[:20]
    )
    kontext = {
        "mandate": mandate,
        "anzahl_aktiv": mandate.filter(status=SepaMandate.Status.AKTIV).count(),
        "anzahl_widerrufen": mandate.filter(status=SepaMandate.Status.WIDERRUFEN).count(),
        "ohne_mandat": ohne_mandat,
        "form": SepaMandateForm(),
    }
    return render(request, "dues/mandate_list.html", kontext)


@role_required(ADMIN_GROUP)
def mandate_create(request):
    if request.method == "POST":
        form = SepaMandateForm(request.POST)
        if form.is_valid():
            mandat = form.save()
            if is_ajax(request):
                return ok(message=f"Mandat {mandat.referenz} für {mandat.member} angelegt.", reload=True)
            messages.success(request, f"Mandat {mandat.referenz} für {mandat.member} angelegt.")
            return redirect("dues:mandate_list")
        if is_ajax(request):
            return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    else:
        form = SepaMandateForm()
    return render(request, "dues/mandate_form.html", {"form": form, "mandat": None})


@role_required(ADMIN_GROUP)
def mandate_update(request, pk):
    mandat = get_object_or_404(SepaMandate, pk=pk)
    if request.method == "POST":
        form = SepaMandateForm(request.POST, instance=mandat)
        if form.is_valid():
            form.save()
            messages.success(request, "Mandat aktualisiert.")
            return redirect("dues:mandate_list")
    else:
        form = SepaMandateForm(instance=mandat)
    return render(request, "dues/mandate_form.html", {"form": form, "mandat": mandat})


@role_required(ADMIN_GROUP)
def export(request):
    jahr = _jahr_aus_request(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="beitraege-{jahr}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        ["Jahr", "Nachname", "Vorname", "Kategorie", "Betrag", "Bezahlt", "Offen", "Status", "Fällig am", "Mahnstufe"]
    )
    for fee in MembershipFee.objects.filter(jahr=jahr).select_related("member").prefetch_related("zahlungen"):
        writer.writerow(
            [
                fee.jahr,
                fee.member.nachname,
                fee.member.vorname,
                fee.kategorie_name,
                f"{fee.betrag:.2f}".replace(".", ","),
                f"{fee.bezahlter_betrag:.2f}".replace(".", ","),
                f"{fee.offener_betrag:.2f}".replace(".", ","),
                fee.get_status_display(),
                fee.faellig_am.strftime("%d.%m.%Y"),
                fee.mahnstufe,
            ]
        )
    return response


@role_required(ADMIN_GROUP)
def kassenbericht(request):
    """Reine Lese-Sicht für den Kassenbericht (PRD M2.6).

    Zeigt Zahlungen je Mitglied für das gewählte Beitragsjahr,
    Jahressumme der Einnahmen und offene Posten zum Stichtag.
    """
    jahr = _jahr_aus_request(request)
    uebersicht = jahres_uebersicht(jahr)
    zahlungen = (
        Payment.objects.filter(fee__jahr=jahr)
        .select_related("fee", "fee__member", "erfasst_von")
        .order_by("datum", "fee__member__nachname", "fee__member__vorname", "pk")
    )
    jahressumme = zahlungen.aggregate(s=Sum("betrag"))["s"] or Decimal("0.00")
    posten = (
        MembershipFee.objects.filter(jahr=jahr)
        .select_related("member")
        .prefetch_related("zahlungen")
        .order_by("member__nachname", "member__vorname")
    )
    offene_posten = [fee for fee in posten if fee.ist_offen]
    jahre = sorted(
        set(MembershipFee.objects.values_list("jahr", flat=True))
        | set(Payment.objects.values_list("fee__jahr", flat=True))
        | {timezone.localdate().year},
        reverse=True,
    )
    kontext = {
        "jahr": jahr,
        "jahre": jahre,
        "uebersicht": uebersicht,
        "zahlungen": zahlungen,
        "offene_posten": offene_posten,
        "jahressumme": jahressumme,
        "heute": timezone.localdate(),
    }
    return render(request, "dues/kassenbericht.html", kontext)


@role_required(ADMIN_GROUP)
def kassenbericht_export(request):
    """CSV-Export des Kassenberichts (Beitragszahlungen je Mitglied, PRD M2.6)."""
    jahr = _jahr_aus_request(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="kassenbericht-beitraege-{jahr}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Datum", "Nachname", "Vorname", "Kategorie", "Zahlungsart", "Betrag", "Notiz"])
    zahlungen = (
        Payment.objects.filter(fee__jahr=jahr)
        .select_related("fee", "fee__member")
        .order_by("datum", "fee__member__nachname", "fee__member__vorname", "pk")
    )
    for z in zahlungen:
        writer.writerow(
            [
                z.datum.strftime("%d.%m.%Y"),
                z.fee.member.nachname,
                z.fee.member.vorname,
                z.fee.kategorie_name,
                z.get_art_display(),
                f"{z.betrag:.2f}".replace(".", ","),
                z.notiz,
            ]
        )
    return response


@login_required
def mein_konto(request):
    """Mitgliedssicht: eigene Beiträge und Zahlungen (PRD M1.4/M2.5)."""
    member = Member.objects.filter(user=request.user).first()
    posten = (
        MembershipFee.objects.filter(member=member).prefetch_related("zahlungen").order_by("-jahr")
        if member
        else []
    )
    kontext = {
        "member": member,
        "posten": posten,
        "mandat": getattr(member, "sepa_mandat", None) if member else None,
        "offen_summe": sum((fee.offener_betrag for fee in posten), Decimal("0.00")) if member else Decimal("0.00"),
    }
    return render(request, "dues/mein_konto.html", kontext)
