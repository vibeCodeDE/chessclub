"""Kassenbuch mit Jahresabschluss und CSV-Export (PRD S6.1/S6.2)."""

import csv

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.roles import ADMIN_GROUP, role_required
from core.ui import fehler, is_ajax, ok, paginate

from .forms import CashEntryForm
from .models import CashEntry, jahresabschluss, storniere_kassenbuchung


def _jahr(request):
    jahr = request.GET.get("jahr", "")
    return int(jahr) if jahr.isdigit() else timezone.localdate().year


@role_required(ADMIN_GROUP)
def entry_list(request):
    jahr = _jahr(request)
    buchungen = CashEntry.objects.filter(datum__year=jahr).select_related("erfasst_von")
    art = request.GET.get("art", "")
    kategorie = request.GET.get("kategorie", "")
    if art in CashEntry.Art.values:
        buchungen = buchungen.filter(art=art)
    if kategorie in CashEntry.Kategorie.values:
        buchungen = buchungen.filter(kategorie=kategorie)
    jahre = sorted(
        set(CashEntry.objects.values_list("datum__year", flat=True)) | {timezone.localdate().year},
        reverse=True,
    )
    kontext = {
        "jahr": jahr,
        "jahre": jahre,
        "abschluss": jahresabschluss(jahr),
        "buchungen": paginate(buchungen, request, per_page=25),
        "art": art,
        "kategorie": kategorie,
        "art_choices": CashEntry.Art.choices,
        "kategorie_choices": CashEntry.Kategorie.choices,
    }
    return render(request, "cashbook/entry_list.html", kontext)


@role_required(ADMIN_GROUP)
def entry_create(request):
    if request.method == "POST":
        form = CashEntryForm(request.POST)
        if form.is_valid():
            buchung = form.save(commit=False)
            buchung.erfasst_von = request.user
            buchung.save()
            if is_ajax(request):
                return ok(message=f"Buchung über {buchung.betrag:.2f} € gespeichert.", reload=True)
            messages.success(request, f"Buchung über {buchung.betrag:.2f} € gespeichert.")
            return redirect("cashbook:entry_list")
        if is_ajax(request):
            return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    else:
        form = CashEntryForm(initial={"datum": timezone.localdate()})
    return render(request, "cashbook/entry_form.html", {"form": form, "buchung": None})


@role_required(ADMIN_GROUP)
def entry_update(request, pk):
    buchung = get_object_or_404(CashEntry, pk=pk)
    if buchung.ist_storniert or buchung.ist_storno:
        hinweis = "Stornierte Buchungen und Gegenbuchungen können nicht bearbeitet werden."
        if is_ajax(request):
            return fehler(hinweis)
        messages.error(request, hinweis)
        return redirect("cashbook:entry_list")
    if request.method == "POST":
        form = CashEntryForm(request.POST, instance=buchung)
        if form.is_valid():
            form.save()
            messages.success(request, "Buchung aktualisiert.")
            return redirect("cashbook:entry_list")
        if is_ajax(request):
            return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    else:
        form = CashEntryForm(instance=buchung)
    return render(request, "cashbook/entry_form.html", {"form": form, "buchung": buchung})


@role_required(ADMIN_GROUP)
@require_POST
def entry_storno(request, pk):
    """Storniert eine Kassenbuchung per Gegenbuchung – kein Hard-Delete von Finanzdaten."""
    buchung = get_object_or_404(CashEntry, pk=pk)
    grund = request.POST.get("grund", "").strip()
    try:
        gegenbuchung = storniere_kassenbuchung(buchung, benutzer=request.user, grund=grund)
    except ValidationError as exc:
        hinweis = " ".join(exc.messages)
        if is_ajax(request):
            return fehler(hinweis)
        messages.error(request, hinweis)
        return redirect("cashbook:entry_list")
    nachricht = f"Buchung „{buchung.beschreibung}“ wurde per Gegenbuchung (#{gegenbuchung.pk}) storniert."
    if is_ajax(request):
        return ok(message=nachricht, reload=True)
    messages.success(request, nachricht)
    return redirect("cashbook:entry_list")


@role_required(ADMIN_GROUP)
def jahresabschluss_view(request):
    jahr = _jahr(request)
    jahre = sorted(
        set(CashEntry.objects.values_list("datum__year", flat=True)) | {timezone.localdate().year},
        reverse=True,
    )
    return render(
        request,
        "cashbook/jahresabschluss.html",
        {"jahr": jahr, "jahre": jahre, "abschluss": jahresabschluss(jahr), "heute": timezone.localdate()},
    )


@role_required(ADMIN_GROUP)
def export(request):
    jahr = _jahr(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="kassenbuch-{jahr}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Datum", "Art", "Kategorie", "Betrag", "Beschreibung", "Beleg-Nr.", "Erfasst von"])
    for buchung in CashEntry.objects.filter(datum__year=jahr).order_by("datum"):
        writer.writerow(
            [
                buchung.datum.strftime("%d.%m.%Y"),
                buchung.get_art_display(),
                buchung.get_kategorie_display(),
                f"{buchung.betrag:.2f}".replace(".", ","),
                buchung.beschreibung,
                buchung.belegnummer,
                buchung.erfasst_von.get_username() if buchung.erfasst_von else "",
            ]
        )
    abschluss = jahresabschluss(jahr)
    writer.writerow([])
    writer.writerow(["Einnahmen", f"{abschluss['einnahmen']:.2f}".replace(".", ",")])
    writer.writerow(["Ausgaben", f"{abschluss['ausgaben']:.2f}".replace(".", ",")])
    writer.writerow(["Saldo", f"{abschluss['saldo']:.2f}".replace(".", ",")])
    return response
