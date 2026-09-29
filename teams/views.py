"""Spielbetrieb: Mannschaften, Ligaspiele, Aufstellungen, Tabellen."""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, role_of, role_required
from core.ui import fehler, is_ajax, ok, paginate
from members.models import Member

from .forms import LineupBoardForm, MatchForm, TeamForm
from .models import LeagueMatch, LineupEntry, Team
from .services import tabelle

TEAM_ROLES = (ADMIN_GROUP, KAPITAEN_GROUP)


def _darf_aufstellen(request, match):
    rolle = role_of(request.user)
    if rolle == ADMIN_GROUP:
        return True
    if rolle == KAPITAEN_GROUP:
        return match.team.kapitaen_id == getattr(
            Member.objects.filter(user=request.user).first(), "pk", None
        ) or match.team.kapitaen_id is None
    return False


@role_required(*TEAM_ROLES)
def team_list(request):
    teams = Team.objects.select_related("kapitaen").prefetch_related("matches")
    kontext = {
        "teams": teams,
        "anzahl_aktiv": teams.filter(aktiv=True).count(),
        "spiele_gesamt": LeagueMatch.objects.count(),
        "naechste_woche": LeagueMatch.objects.filter(
            datum__gte=timezone.localdate(),
            datum__lte=timezone.localdate() + timedelta(days=7),
        ).count(),
        "naechste_spiele": LeagueMatch.objects.filter(datum__gte=timezone.localdate())
        .select_related("team")
        .order_by("datum")[:8],
    }
    return render(request, "teams/team_list.html", kontext)


@role_required(*TEAM_ROLES)
def team_create(request):
    if request.method == "POST":
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save()
            if is_ajax(request):
                return ok(message=f"Mannschaft „{team.name}“ angelegt.", reload=True)
            messages.success(request, f"Mannschaft „{team.name}“ angelegt.")
            return redirect("teams:team_detail", pk=team.pk)
        if is_ajax(request):
            return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    else:
        form = TeamForm()
    return render(request, "teams/team_form.html", {"form": form, "team": None})


@role_required(*TEAM_ROLES)
def team_update(request, pk):
    team = get_object_or_404(Team, pk=pk)
    if request.method == "POST":
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            messages.success(request, "Mannschaft aktualisiert.")
            return redirect("teams:team_detail", pk=team.pk)
    else:
        form = TeamForm(instance=team)
    return render(request, "teams/team_form.html", {"form": form, "team": team})


@role_required(ADMIN_GROUP)
@require_POST
def team_delete(request, pk):
    team = get_object_or_404(Team, pk=pk)
    if team.matches.exists():
        return fehler(
            f"„{team.name}“ hat noch {team.matches.count()} Ligaspiele – bitte zuerst archivieren."
        )
    name = team.name
    team.delete()
    return ok(message=f"Mannschaft „{name}“ gelöscht.", remove_selector=f"[data-row='team-{pk}']")


@role_required(*TEAM_ROLES)
def team_detail(request, pk):
    team = get_object_or_404(Team.objects.select_related("kapitaen"), pk=pk)
    matches = team.matches.all().order_by("-datum")
    kontext = {
        "team": team,
        "matches": matches,
        "kommende": [m for m in matches if m.datum >= timezone.localdate()][:6],
        "bilanz": team.bilanz,
        "tabelle": tabelle(team.liga),
        "aufstellungen": LineupEntry.objects.filter(match__team=team)
        .select_related("member", "match")
        .order_by("-match__datum")[:12],
    }
    return render(request, "teams/team_detail.html", kontext)


@role_required(*TEAM_ROLES)
def match_list(request):
    matches = LeagueMatch.objects.select_related("team").prefetch_related("aufstellung")
    team_id = request.GET.get("team", "")
    status = request.GET.get("status", "")
    zeitraum = request.GET.get("zeitraum", "")
    if team_id.isdigit():
        matches = matches.filter(team_id=int(team_id))
    if status in LeagueMatch.Status.values:
        matches = matches.filter(status=status)
    if zeitraum == "kommend":
        matches = matches.filter(datum__gte=timezone.localdate())
    elif zeitraum == "vergangen":
        matches = matches.filter(datum__lt=timezone.localdate())
    kontext = {
        "matches": paginate(matches, request, per_page=25),
        "teams": Team.objects.all(),
        "team_id": team_id,
        "status": status,
        "zeitraum": zeitraum,
        "status_choices": LeagueMatch.Status.choices,
    }
    return render(request, "teams/match_list.html", kontext)


@role_required(*TEAM_ROLES)
def match_create(request):
    if request.method == "POST":
        form = MatchForm(request.POST)
        if form.is_valid():
            match = form.save()
            messages.success(request, f"Ligaspiel gegen {match.gegner} angelegt.")
            return redirect("teams:match_detail", pk=match.pk)
    else:
        form = MatchForm(
            initial={"datum": timezone.localdate(), "heimspiel": True, "status": LeagueMatch.Status.GEPLANT}
        )
    return render(request, "teams/match_form.html", {"form": form, "match": None})


@role_required(*TEAM_ROLES)
def match_update(request, pk):
    match = get_object_or_404(LeagueMatch, pk=pk)
    if request.method == "POST":
        form = MatchForm(request.POST, instance=match)
        if form.is_valid():
            form.save()
            messages.success(request, "Ligaspiel aktualisiert.")
            return redirect("teams:match_detail", pk=match.pk)
    else:
        form = MatchForm(instance=match)
    return render(request, "teams/match_form.html", {"form": form, "match": match})


@role_required(ADMIN_GROUP)
@require_POST
def match_delete(request, pk):
    match = get_object_or_404(LeagueMatch, pk=pk)
    beschreibung = str(match)
    match.delete()
    return ok(message=f"Ligaspiel „{beschreibung}“ gelöscht.", remove_selector=f"[data-row='match-{pk}']")


def _lineup_kontext(request, match):
    eintraege = {eintrag.brett: eintrag for eintrag in match.aufstellung.select_related("member")}
    bretter = []
    for brett in range(1, match.brettanzahl + 1):
        bretter.append({"brett": brett, "eintrag": eintraege.get(brett)})
    return {
        "match": match,
        "bretter": bretter,
        "mitglieder": Member.objects.exclude(status=Member.Status.AUSGETRETEN),
        "ergebnis_choices": LineupEntry.Ergebnis.choices,
        "darf_aufstellen": _darf_aufstellen(request, match),
        "form": LineupBoardForm(match=match),
    }


@role_required(*TEAM_ROLES)
def match_detail(request, pk):
    match = get_object_or_404(LeagueMatch.objects.select_related("team"), pk=pk)
    kontext = _lineup_kontext(request, match)
    kontext["offene_bretter"] = sum(1 for e in match.aufstellung.all() if not e.ergebnis)
    kontext["tabelle"] = tabelle(match.team.liga)
    kontext["gegner_tabelle"] = [zeile for zeile in kontext["tabelle"] if zeile["name"] == match.gegner]
    return render(request, "teams/match_detail.html", kontext)


def _match_patch(match):
    return {
        "[data-brettpunkte]": match.brettpunkte_anzeige,
        "[data-mannschaftspunkte]": {2: "Sieg", 1: "Remis", 0: "Niederlage", None: "–"}[
            match.mannschaftspunkte
        ],
        f"[data-match-status='{match.pk}']": match.get_status_display(),
    }


@role_required(*TEAM_ROLES)
@require_POST
def lineup_board_save(request, pk, brett):
    """Autosave je Brett (optimistisch im UI)."""
    match = get_object_or_404(LeagueMatch, pk=pk)
    if not _darf_aufstellen(request, match):
        return fehler("Nur Mannschaftsführung oder Vorstand darf aufstellen.", status=403)

    eintrag, _ = LineupEntry.objects.get_or_create(match=match, brett=brett)
    member_id = request.POST.get("member") or ""
    eintrag.member = (
        Member.objects.filter(pk=int(member_id)).first() if member_id.isdigit() else None
    )
    eintrag.gegner_name = request.POST.get("gegner_name", "")[:120]
    ergebnis = request.POST.get("ergebnis", "")
    if ergebnis not in dict(LineupEntry.Ergebnis.choices):
        ergebnis = ""
    eintrag.ergebnis = ergebnis
    if eintrag.member is None and not eintrag.gegner_name and not eintrag.ergebnis:
        eintrag.delete()
    else:
        eintrag.save()

    match = LeagueMatch.objects.get(pk=match.pk)
    match.status_aktualisieren()
    return ok(
        message=f"Brett {brett} gespeichert.",
        patch={
            **_match_patch(match),
            f"[data-brett-spieler='{brett}']": eintrag.spieler_name if eintrag.pk else "– nicht benannt –",
            f"[data-brett-ergebnis='{brett}']": ergebnis or "offen",
        },
        classes={f"[data-brett-row='{brett}']": {"add": [f"ergebnis-{ergebnis or 'offen'}"], "remove": [
            "ergebnis-1", "ergebnis-0.5", "ergebnis-0", "ergebnis-offen"
        ]}},
    )


@role_required(*TEAM_ROLES)
@require_POST
def lineup_save(request, pk):
    """Komplettes Speichern der Aufstellung (Fallback ohne JavaScript)."""
    match = get_object_or_404(LeagueMatch, pk=pk)
    if not _darf_aufstellen(request, match):
        messages.error(request, "Nur die Mannschaftsführung oder der Vorstand darf aufstellen.")
        return redirect("teams:match_detail", pk=match.pk)
    form = LineupBoardForm(request.POST, match=match)
    if form.is_valid():
        form.speichern()
        match.status_aktualisieren()
        messages.success(request, "Aufstellung gespeichert.")
    else:
        messages.error(request, "Aufstellung konnte nicht gespeichert werden.")
    return redirect("teams:match_detail", pk=match.pk)


@login_required
def tabelle_list(request):
    """Ligatabellen sind für alle angemeldeten Mitglieder einsehbar."""
    teams = Team.objects.exclude(liga="")
    ligen = {}
    for team in teams:
        ligen.setdefault(team.liga, tabelle(team.liga))
    for freie_teams in Team.objects.filter(liga=""):
        ligen[f"– {freie_teams.name} (keine Liga) –"] = tabelle("")
    kontext = {"ligen": ligen, "anzahl_ligen": len(ligen)}
    return render(request, "teams/tabelle_list.html", kontext)


@login_required
def meine_aufstellungen(request):
    """Eigene Einsätze für Mitglieder."""
    member = Member.objects.filter(user=request.user).first()
    eintraege = (
        member.lineups.select_related("match", "match__team").order_by("-match__datum")
        if member
        else []
    )
    return render(
        request,
        "teams/meine_aufstellungen.html",
        {"member": member, "eintraege": eintraege},
    )
