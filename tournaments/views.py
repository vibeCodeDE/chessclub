"""Turnierverwaltung inkl. Paarungen, Ergebnissen und öffentlicher Anmeldung."""

import csv

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from core.roles import ADMIN_GROUP, role_required
from core.ui import fehler, ok
from members.models import Member

from .forms import ParticipantForm, PublicRegistrationForm, TournamentForm
from .models import Pairing, Participant, Tournament, TournamentRound, teilnehmer_stand
from .pairing import generate_round, turnier_abschliessen


# ---------------------------------------------------------------- öffentlich
def public_list(request):
    heute = timezone.localdate()
    saison_id = request.GET.get("saison", "")
    kommende = Tournament.objects.filter(oeffentlich=True, datum__gte=heute).select_related("saison").order_by("datum")
    vergangene = Tournament.objects.filter(oeffentlich=True, datum__lt=heute).select_related("saison").order_by("-datum")
    if saison_id:
        if saison_id == "keine":
            kommende = kommende.filter(saison__isnull=True)
            vergangene = vergangene.filter(saison__isnull=True)
        elif saison_id.isdigit():
            kommende = kommende.filter(saison_id=int(saison_id))
            vergangene = vergangene.filter(saison_id=int(saison_id))
        else:
            kommende = kommende.filter(saison__slug=saison_id)
            vergangene = vergangene.filter(saison__slug=saison_id)
    else:
        vergangene = vergangene[:6]
    return render(
        request,
        "tournaments/public_list.html",
        {"kommende": kommende, "vergangene": vergangene, "heute": heute, "saison_id": saison_id},
    )


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def public_detail(request, pk):
    turnier = get_object_or_404(Tournament, pk=pk, oeffentlich=True)
    form = PublicRegistrationForm(tournament=turnier)
    if request.method == "POST":
        if not turnier.anmeldung_offen:
            messages.error(request, "Die Anmeldung für dieses Turnier ist geschlossen.")
        else:
            form = PublicRegistrationForm(request.POST, tournament=turnier)
            if form.is_valid():
                teilnehmer = form.save(commit=False)
                teilnehmer.tournament = turnier
                member = Member.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                if member:
                    teilnehmer.member = member
                teilnehmer.save()
                messages.success(
                    request,
                    "Anmeldung eingegangen! Die Turnierleitung bestätigt sie in Kürze.",
                )
                return redirect("tournaments:public_detail", pk=turnier.pk)
            messages.error(request, "Bitte Eingaben prüfen.")
    stand = teilnehmer_stand(turnier) if turnier.runden.exists() else []
    return render(
        request,
        "tournaments/public_detail.html",
        {"turnier": turnier, "form": form, "stand": stand, "heute": timezone.localdate()},
    )


def public_ical(request, pk):
    """iCal-Kalendereintrag für ein öffentliches Turnier herunterladen."""
    turnier = get_object_or_404(Tournament, pk=pk, oeffentlich=True)
    club = getattr(settings, "CLUB_NAME", "Schachverein")
    club_short = getattr(settings, "CLUB_SHORT", "schach")
    now_utc = timezone.now().strftime("%Y%m%dT%H%M%SZ")
    datum_str = turnier.datum.strftime("%Y%m%d")

    def _esc(t):
        if not t:
            return ""
        return str(t).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{_esc(club)}//Turnier//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:turnier-{turnier.pk}@{club_short}.local",
        f"DTSTAMP:{now_utc}",
        f"DTSTART;VALUE=DATE:{datum_str}",
        f"DTEND;VALUE=DATE:{datum_str}",
        f"SUMMARY:{_esc(turnier.name)}",
        f"DESCRIPTION:{_esc(turnier.beschreibung or turnier.name)}",
    ]
    if turnier.ort:
        lines.append(f"LOCATION:{_esc(turnier.ort)}")
    lines.extend([
        "END:VEVENT",
        "END:VCALENDAR",
    ])
    content = "\r\n".join(lines) + "\r\n"
    response = HttpResponse(content, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'inline; filename="turnier_{turnier.pk}.ics"'
    return response


# ------------------------------------------------------------------- Verwaltung
@role_required(ADMIN_GROUP)
def manage_list(request):
    turniere = Tournament.objects.select_related("saison")
    status = request.GET.get("status", "")
    saison_id = request.GET.get("saison", "")
    if saison_id:
        if saison_id == "keine":
            turniere = turniere.filter(saison__isnull=True)
        elif saison_id.isdigit():
            turniere = turniere.filter(saison_id=int(saison_id))
        else:
            turniere = turniere.filter(saison__slug=saison_id)
    if status in Tournament.Status.values:
        turniere = turniere.filter(status=status)
    kontext = {
        "turniere": turniere,
        "status": status,
        "saison_id": saison_id,
        "status_choices": Tournament.Status.choices,
        "anzahl_teilnehmer": Participant.objects.count(),
        "laufend": Tournament.objects.filter(status=Tournament.Status.LAUFEND).count(),
        "offene_startgelder": Participant.objects.filter(startgeld_bezahlt=False).count(),
        "heute": timezone.localdate(),
    }
    return render(request, "tournaments/manage_list.html", kontext)


@role_required(ADMIN_GROUP)
def manage_create(request):
    if request.method == "POST":
        form = TournamentForm(request.POST)
        if form.is_valid():
            turnier = form.save()
            messages.success(request, f"Turnier „{turnier.name}“ angelegt.")
            return redirect("tournaments:manage_detail", pk=turnier.pk)
    else:
        form = TournamentForm(
            initial={"datum": timezone.localdate(), "status": Tournament.Status.ANMELDUNG}
        )
    return render(request, "tournaments/tournament_form.html", {"form": form, "turnier": None})


@role_required(ADMIN_GROUP)
def manage_update(request, pk):
    turnier = get_object_or_404(Tournament, pk=pk)
    if request.method == "POST":
        form = TournamentForm(request.POST, instance=turnier)
        if form.is_valid():
            form.save()
            messages.success(request, "Turnier aktualisiert.")
            return redirect("tournaments:manage_detail", pk=turnier.pk)
    else:
        form = TournamentForm(instance=turnier)
    return render(request, "tournaments/tournament_form.html", {"form": form, "turnier": turnier})


@role_required(ADMIN_GROUP)
@require_POST
def manage_delete(request, pk):
    turnier = get_object_or_404(Tournament, pk=pk)
    if turnier.runden.exists():
        return fehler("Das Turnier hat bereits Runden – bitte zuerst auf „Beendet“ setzen oder Runden löschen.")
    name = turnier.name
    turnier.delete()
    return ok(message=f"Turnier „{name}“ gelöscht.", remove_selector=f"[data-row='turnier-{pk}']")


@role_required(ADMIN_GROUP)
def manage_detail(request, pk):
    turnier = get_object_or_404(Tournament, pk=pk)
    runden = turnier.runden.prefetch_related("paarungen__weiss", "paarungen__schwarz")
    aktuelle_runde = runden.order_by("-nummer").first()
    kontext = {
        "turnier": turnier,
        "runden": runden,
        "aktuelle_runde": aktuelle_runde,
        "paarungen": aktuelle_runde.paarungen.select_related("weiss", "schwarz") if aktuelle_runde else [],
        "teilnehmer": turnier.teilnehmer.select_related("member"),
        "stand": teilnehmer_stand(turnier),
        "form": ParticipantForm(tournament=turnier),
        "naechste_runde": turnier.runden.count() + 1,
        "ergebnis_choices": Pairing.Ergebnis.choices,
        "startgeld_offen": turnier.teilnehmer.filter(startgeld_bezahlt=False).count(),
    }
    return render(request, "tournaments/manage_detail.html", kontext)


@role_required(ADMIN_GROUP)
@require_POST
def participant_create(request, pk):
    turnier = get_object_or_404(Tournament, pk=pk)
    form = ParticipantForm(request.POST, tournament=turnier)
    if not form.is_valid():
        return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    teilnehmer = form.save(commit=False)
    teilnehmer.tournament = turnier
    teilnehmer.save()
    return ok(message=f"{teilnehmer.name} wurde angemeldet.", reload=True)


@role_required(ADMIN_GROUP)
@require_POST
def participant_toggle_startgeld(request, pk):
    teilnehmer = get_object_or_404(Participant, pk=pk)
    if "startgeld_bezahlt" in request.POST:
        teilnehmer.startgeld_bezahlt = request.POST.get("startgeld_bezahlt") not in {"", "0", "false"}
    else:
        teilnehmer.startgeld_bezahlt = not teilnehmer.startgeld_bezahlt
    teilnehmer.save(update_fields=["startgeld_bezahlt"])
    return ok(
        message=f"Startgeld für {teilnehmer.name} {'erfasst' if teilnehmer.startgeld_bezahlt else 'zurückgesetzt'}.",
        checked=teilnehmer.startgeld_bezahlt,
        patch={f"[data-startgeld-text='{teilnehmer.pk}']": "bezahlt" if teilnehmer.startgeld_bezahlt else "offen"},
        classes={
            f"[data-startgeld-badge='{teilnehmer.pk}']": {
                "add": ["badge-bezahlt" if teilnehmer.startgeld_bezahlt else "badge-offen"],
                "remove": ["badge-bezahlt", "badge-offen"],
            }
        },
    )


@role_required(ADMIN_GROUP)
@require_POST
def participant_delete(request, pk):
    teilnehmer = get_object_or_404(Participant, pk=pk)
    if Pairing.objects.filter(weiss=teilnehmer).exists() or Pairing.objects.filter(schwarz=teilnehmer).exists():
        return fehler(
            f"{teilnehmer.name} hat bereits Paarungen – Abmeldung nur vor der ersten Runde möglich."
        )
    name = teilnehmer.name
    teilnehmer.delete()
    return ok(message=f"{name} wurde abgemeldet.", remove_selector=f"[data-row='teilnehmer-{pk}']")


@role_required(ADMIN_GROUP)
@require_POST
def round_generate(request, pk):
    turnier = get_object_or_404(Tournament, pk=pk)
    runde, fehlermeldung = generate_round(turnier)
    if runde is None:
        return fehler(fehlermeldung)
    return ok(message=f"Runde {runde.nummer} mit {runde.paarungen.count()} Paarungen erzeugt.", reload=True)


@role_required(ADMIN_GROUP)
@require_POST
def round_delete(request, pk, nummer):
    turnier = get_object_or_404(Tournament, pk=pk)
    runde = get_object_or_404(TournamentRound, tournament=turnier, nummer=nummer)
    if turnier.runden.exclude(pk=runde.pk).filter(nummer__gt=nummer).exists():
        return fehler("Nur die letzte Runde kann zurückgenommen werden.")
    runde.delete()
    return ok(message=f"Runde {nummer} zurückgenommen.", reload=True)


@role_required(ADMIN_GROUP)
@require_POST
def pairing_result(request, pk):
    """Ergebniserfassung je Brett (optimistisch, sofortige Zwischenwertung)."""
    pairing = get_object_or_404(Pairing.objects.select_related("runde__tournament"), pk=pk)
    ergebnis = request.POST.get("ergebnis", "")
    if ergebnis not in dict(Pairing.Ergebnis.choices):
        return fehler("Unbekanntes Ergebnis.")
    pairing.ergebnis = ergebnis
    pairing.save(update_fields=["ergebnis"])

    turnier = pairing.runde.tournament
    stand = teilnehmer_stand(turnier)
    patch = {f"[data-punkte='{pairing.pk}']": pairing.ergebnis_anzeige}
    for spieler in (pairing.weiss, pairing.schwarz):
        if spieler is None:
            continue
        patch[f"[data-stand-punkte='{spieler.pk}']"] = f"{spieler.punkte:.1f}"
        patch[f"[data-stand-buchholz='{spieler.pk}']"] = f"{spieler.buchholz:.1f}"
    return ok(
        message="Ergebnis gespeichert.",
        patch=patch,
        html={"[data-stand-body]": _stand_table_rows(stand)},
    )


def _stand_table_rows(stand):
    zeilen = []
    for teilnehmer in stand:
        zeilen.append(
            f"<tr><td class='mono'>{teilnehmer.rang}</td>"
            f"<td class='cell-main'>{teilnehmer.name}</td>"
            f"<td class='cell-sub'>{teilnehmer.verein or '–'}</td>"
            f"<td class='num mono' data-stand-punkte='{teilnehmer.pk}'>{teilnehmer.aktuelle_punkte:.1f}</td>"
            f"<td class='num mono' data-stand-buchholz='{teilnehmer.pk}'>{teilnehmer.aktuelle_buchholz:.1f}</td></tr>"
        )
    return "".join(zeilen) or "<tr><td colspan='5' class='muted'>Keine Teilnehmer:innen.</td></tr>"


@role_required(ADMIN_GROUP)
@require_POST
def tournament_finish(request, pk):
    turnier = get_object_or_404(Tournament, pk=pk)
    turnier_abschliessen(turnier)
    return ok(message="Turnier abgeschlossen – Ergebnisliste ist jetzt veröffentlicht.", reload=True)


@role_required(ADMIN_GROUP)
def export_csv(request, pk):
    turnier = get_object_or_404(Tournament, pk=pk)
    stand = teilnehmer_stand(turnier)
    runden = list(turnier.runden.order_by("nummer"))
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="ergebnisse-{turnier.pk}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")

    # Abschnitt [TRN] - Turnier-Metadaten
    writer.writerow(["[TRN]"])
    writer.writerow(["Kennung", "Name", "Datum", "Ort", "Runden", "Format", "Status"])
    writer.writerow(
        [
            "TRN",
            turnier.name,
            turnier.datum.strftime("%d.%m.%Y"),
            turnier.ort or "Vereinsheim",
            turnier.runden_anzahl,
            turnier.get_format_display(),
            turnier.get_status_display(),
        ]
    )
    writer.writerow([])

    # Abschnitt [ARB] - Organisation und Schiedsrichter
    writer.writerow(["[ARB]"])
    writer.writerow(["Kennung", "Organisator", "Kontakt", "Erstelldatum"])
    writer.writerow(
        [
            "ARB",
            settings.CLUB_NAME,
            getattr(settings, "CLUB_CONTACT", ""),
            timezone.localdate().strftime("%d.%m.%Y"),
        ]
    )
    writer.writerow([])

    # Abschnitt [RAN] - Rangliste und Rundenergebnisse
    writer.writerow(["[RAN]"])
    kopf = ["Kennung", "Rang", "Name", "Verein", "DWZ/TWZ", "Punkte", "Buchholz"] + [f"R{n.nummer}" for n in runden]
    writer.writerow(kopf)
    for teilnehmer in stand:
        ergebnisse = []
        for runde in runden:
            paarung = next(
                (
                    p
                    for p in runde.paarungen.all()
                    if p.weiss_id == teilnehmer.pk or p.schwarz_id == teilnehmer.pk
                ),
                None,
            )
            if paarung is None:
                ergebnisse.append("")
            elif paarung.ergebnis == Pairing.Ergebnis.BYE:
                ergebnisse.append("+")
            elif not paarung.ergebnis:
                ergebnisse.append("")
            else:
                eigene_punkte = paarung.punkte_fuer(teilnehmer)
                gegner = paarung.gegner_von(teilnehmer)
                farbe = "w" if paarung.weiss_id == teilnehmer.pk else "s"
                ergebnisse.append(f"{eigene_punkte:g}{farbe} {gegner.name}" if gegner else f"{eigene_punkte:g}{farbe}")
        writer.writerow(
            [
                "RAN",
                teilnehmer.rang,
                teilnehmer.name,
                teilnehmer.verein,
                teilnehmer.twz or "",
                f"{teilnehmer.aktuelle_punkte:.1f}".replace(".", ","),
                f"{teilnehmer.aktuelle_buchholz:.1f}".replace(".", ","),
                *ergebnisse,
            ]
        )
    return response


@role_required(ADMIN_GROUP)
def print_results(request, pk):
    turnier = get_object_or_404(Tournament, pk=pk)
    return render(
        request,
        "tournaments/print_results.html",
        {"turnier": turnier, "stand": teilnehmer_stand(turnier), "heute": timezone.localdate()},
    )


@role_required(ADMIN_GROUP)
def round_print(request, pk, runde_nr):
    """Offizieller A4-Rundenaushang für das Schwarze Brett (Hebel F3 & D3)."""
    turnier = get_object_or_404(Tournament, pk=pk)
    runde = get_object_or_404(TournamentRound, tournament=turnier, nummer=runde_nr)
    paarungen = runde.paarungen.select_related("weiss", "schwarz").order_by("brett")
    return render(
        request,
        "tournaments/round_print.html",
        {
            "turnier": turnier,
            "runde": runde,
            "paarungen": paarungen,
            "heute": timezone.localdate(),
        },
    )

