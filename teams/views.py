"""Spielbetrieb: Mannschaften, Ligaspiele, Aufstellungen, Tabellen, iCal-Feeds."""

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, role_of, role_required
from core.ui import fehler, is_ajax, ok, paginate
from members.models import Member

from .forms import LineupBoardForm, MatchForm, SeasonForm, SeasonRolloverForm, TeamForm
from .models import LeagueCalendarFeed, LeagueMatch, LineupEntry, Season, Team
from .services import (
    archive_season,
    check_match_edit_allowed,
    create_season,
    delete_season,
    generate_ical_feed,
    reopen_season,
    rollover_teams,
    set_active_season,
    tabelle,
    validate_match_season_bounds,
)

TEAM_ROLES = (ADMIN_GROUP, KAPITAEN_GROUP)


def _darf_aufstellen(request, match):
    rolle = role_of(request.user)
    if rolle == ADMIN_GROUP:
        return True
    if rolle == KAPITAEN_GROUP:
        member = Member.objects.filter(user=request.user).first()
        return bool(member and match.team.kapitaen_id == member.pk)
    return False


@role_required(*TEAM_ROLES)
def team_list(request):
    saison_id = request.GET.get("saison")
    aktive_saison = Season.get_aktive_saison()
    gewaehlte_saison = None
    if saison_id:
        try:
            gewaehlte_saison = Season.objects.filter(pk=int(saison_id)).first()
        except (ValueError, TypeError):
            gewaehlte_saison = Season.objects.filter(slug=str(saison_id)).first()
    if not gewaehlte_saison and saison_id != "alle":
        gewaehlte_saison = aktive_saison

    teams = Team.objects.select_related("kapitaen", "saison").prefetch_related("matches")
    if gewaehlte_saison:
        teams = teams.filter(saison=gewaehlte_saison)

    spiele_qs = LeagueMatch.objects.all()
    if gewaehlte_saison:
        spiele_qs = spiele_qs.filter(team__saison=gewaehlte_saison)

    kontext = {
        "teams": teams,
        "gewaehlte_saison": gewaehlte_saison,
        "anzahl_aktiv": teams.filter(aktiv=True).count(),
        "spiele_gesamt": spiele_qs.count(),
        "naechste_woche": spiele_qs.filter(
            datum__gte=timezone.localdate(),
            datum__lte=timezone.localdate() + timedelta(days=7),
        ).count(),
        "naechste_spiele": spiele_qs.filter(datum__gte=timezone.localdate())
        .select_related("team")
        .order_by("datum")[:8],
    }
    return render(request, "teams/team_list.html", kontext)


@role_required(ADMIN_GROUP)
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


@role_required(ADMIN_GROUP)
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
    feed_url = request.build_absolute_uri(
        reverse("teams:ical_team", kwargs={"pk": team.pk, "token": team.ical_token})
    )
    kontext = {
        "team": team,
        "matches": matches,
        "kommende": [m for m in matches if m.datum >= timezone.localdate()][:6],
        "bilanz": team.bilanz,
        "tabelle": tabelle(team.liga),
        "aufstellungen": LineupEntry.objects.filter(match__team=team)
        .select_related("member", "match")
        .order_by("-match__datum")[:12],
        "feed_url": feed_url,
    }
    return render(request, "teams/team_detail.html", kontext)


@role_required(*TEAM_ROLES)
def match_list(request):
    saison_id = request.GET.get("saison")
    aktive_saison = Season.get_aktive_saison()
    gewaehlte_saison = None
    if saison_id:
        try:
            gewaehlte_saison = Season.objects.filter(pk=int(saison_id)).first()
        except (ValueError, TypeError):
            gewaehlte_saison = Season.objects.filter(slug=str(saison_id)).first()
    if not gewaehlte_saison and saison_id != "alle":
        gewaehlte_saison = aktive_saison

    matches = LeagueMatch.objects.select_related("team", "team__saison").prefetch_related("aufstellung")
    if gewaehlte_saison:
        matches = matches.filter(team__saison=gewaehlte_saison)

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

    teams_qs = Team.objects.select_related("saison")
    if gewaehlte_saison:
        teams_qs = teams_qs.filter(saison=gewaehlte_saison)

    gesamt_feed_url = request.build_absolute_uri(
        reverse("teams:ical_gesamt", kwargs={"token": LeagueCalendarFeed.get_token()})
    )
    kontext = {
        "matches": paginate(matches, request, per_page=25),
        "teams": teams_qs,
        "gewaehlte_saison": gewaehlte_saison,
        "team_id": team_id,
        "status": status,
        "zeitraum": zeitraum,
        "status_choices": LeagueMatch.Status.choices,
        "gesamt_feed_url": gesamt_feed_url,
    }
    return render(request, "teams/match_list.html", kontext)


@role_required(ADMIN_GROUP)
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


@role_required(ADMIN_GROUP)
def match_update(request, pk):
    match = get_object_or_404(LeagueMatch.objects.select_related("team__saison"), pk=pk)
    check_match_edit_allowed(match)
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
    match = get_object_or_404(LeagueMatch.objects.select_related("team__saison"), pk=pk)
    check_match_edit_allowed(match)
    beschreibung = str(match)
    match.delete()
    return ok(message=f"Ligaspiel „{beschreibung}“ gelöscht.", remove_selector=f"[data-row='match-{pk}']")


def _lineup_kontext(request, match):
    eintraege = {eintrag.brett: eintrag for eintrag in match.aufstellung.select_related("member")}
    bretter = []
    for brett in range(1, match.brettanzahl + 1):
        bretter.append({"brett": brett, "eintrag": eintraege.get(brett)})
    darf_aufstellen = _darf_aufstellen(request, match) and not (
        match.team and match.team.saison and match.team.saison.ist_archiviert
    )
    return {
        "match": match,
        "bretter": bretter,
        "mitglieder": Member.objects.exclude(status=Member.Status.AUSGETRETEN),
        "ergebnis_choices": LineupEntry.Ergebnis.choices,
        "darf_aufstellen": darf_aufstellen,
        "form": LineupBoardForm(match=match),
    }


@role_required(*TEAM_ROLES)
def match_detail(request, pk):
    match = get_object_or_404(LeagueMatch.objects.select_related("team__saison"), pk=pk)
    kontext = _lineup_kontext(request, match)
    kontext["offene_bretter"] = sum(1 for e in match.aufstellung.all() if not e.ergebnis)
    kontext["tabelle"] = tabelle(match.team.liga)
    kontext["gegner_tabelle"] = [zeile for zeile in kontext["tabelle"] if zeile["name"] == match.gegner]
    return render(request, "teams/match_detail.html", kontext)


@role_required(*TEAM_ROLES)
def match_print(request, pk):
    """Offizielle A4-Druckansicht des Spielberichts (Hebel F2 & D3)."""
    match = get_object_or_404(
        LeagueMatch.objects.select_related("team", "team__kapitaen", "team__saison"), pk=pk
    )
    eintraege = {
        eintrag.brett: eintrag
        for eintrag in match.aufstellung.select_related("member").all()
    }
    bretter = []
    for brett_nr in range(1, match.brettanzahl + 1):
        bretter.append({
            "brett": brett_nr,
            "eintrag": eintraege.get(brett_nr),
        })

    kontext = {
        "match": match,
        "bretter": bretter,
        "club_name": getattr(settings, "CLUB_NAME", "Schachverein"),
        "heute": timezone.localdate(),
    }
    return render(request, "teams/match_print.html", kontext)



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
    match = get_object_or_404(LeagueMatch.objects.select_related("team__saison"), pk=pk)
    check_match_edit_allowed(match)
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
    match = get_object_or_404(LeagueMatch.objects.select_related("team__saison"), pk=pk)
    check_match_edit_allowed(match)
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


def ical_feed_team(request, pk, token):
    """Abonnierbarer Kalender-Feed für eine Mannschaft (PRD S4.6). Ohne Login, nur mit Token."""
    team = get_object_or_404(Team, pk=pk, ical_token=token)
    matches = list(team.matches.select_related("team").order_by("datum", "uhrzeit"))
    feed_content = generate_ical_feed(matches, kalender_name=f"{team.name} – Ligaspiele")
    response = HttpResponse(feed_content, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'inline; filename="ligaspiele_{team.pk}.ics"'
    return response


def ical_feed_gesamt(request, token):
    """Abonnierbarer Kalender-Feed für alle Ligaspiele (PRD S4.6). Ohne Login, nur mit Token."""
    feed = LeagueCalendarFeed.objects.filter(name="gesamt", token=token).first()
    if not feed or not token:
        raise Http404("Ungültiger Kalender-Token.")
    matches = list(LeagueMatch.objects.select_related("team").order_by("datum", "uhrzeit"))
    feed_content = generate_ical_feed(matches, kalender_name="Alle Ligaspiele")
    response = HttpResponse(feed_content, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = 'inline; filename="ligaspiele_gesamt.ics"'
    return response


@role_required(ADMIN_GROUP)
@require_POST
def team_renew_ical_token(request, pk):
    """Erneuert das Kalender-Token einer Mannschaft (PRD S4.6)."""
    team = get_object_or_404(Team, pk=pk)
    team.renew_ical_token()
    messages.success(
        request, f"Kalender-Token für „{team.name}“ wurde erneuert. Alte Abonnements sind ungültig."
    )
    return redirect("teams:team_detail", pk=team.pk)


@role_required(ADMIN_GROUP)
@require_POST
def gesamt_renew_ical_token(request):
    """Erneuert das globale Kalender-Token aller Ligaspiele (PRD S4.6)."""
    LeagueCalendarFeed.renew_token()
    messages.success(
        request, "Globaler Kalender-Token wurde erneuert. Alte Abonnements sind ungültig."
    )
    return redirect("teams:match_list")


@role_required(ADMIN_GROUP)
def season_list(request):
    """Übersicht aller Saisons mit Schnellaktionen für den Vorstand."""
    from django.db.models import Count
    saisons = list(
        Season.objects.annotate(
            teams_count=Count("teams", distinct=True),
            matches_count=Count("teams__matches", distinct=True),
        ).order_by("-startdatum")
    )
    aktive_saison = next((s for s in saisons if s.ist_aktiv), None)
    if not aktive_saison and saisons:
        aktive_saison = saisons[0]
    return render(
        request,
        "teams/season_list.html",
        {
            "saisons": saisons,
            "aktive_saison": aktive_saison,
            "titel": "Saisonverwaltung",
        },
    )


@role_required(ADMIN_GROUP)
def season_create(request):
    """Neue Saison mit Zeitraum und Vorbelegung anlegen."""
    from datetime import date
    if request.method == "POST":
        form = SeasonForm(request.POST)
        if form.is_valid():
            saison = create_season(
                name=form.cleaned_data["name"],
                startdatum=form.cleaned_data["startdatum"],
                enddatum=form.cleaned_data["enddatum"],
                notizen=form.cleaned_data.get("notizen", ""),
                als_aktiv_setzen=form.cleaned_data.get("als_aktiv_setzen", False),
                user=request.user,
            )
            messages.success(request, f"Saison {saison.name} erfolgreich angelegt.")
            return redirect("teams:season_list")
    else:
        latest = Season.objects.order_by("-enddatum").first()
        if latest:
            next_start = latest.enddatum + timedelta(days=1)
            next_end = date(next_start.year + 1, next_start.month, next_start.day) - timedelta(days=1)
            vorschlag_name = f"{next_start.year}/{next_end.year}"
        else:
            heute = timezone.localdate()
            if heute.month >= 7:
                next_start = date(heute.year, 8, 1)
                next_end = date(heute.year + 1, 7, 31)
                vorschlag_name = f"{heute.year}/{heute.year + 1}"
            else:
                next_start = date(heute.year - 1, 8, 1)
                next_end = date(heute.year, 7, 31)
                vorschlag_name = f"{heute.year - 1}/{heute.year}"

        form = SeasonForm(
            initial={
                "name": vorschlag_name,
                "startdatum": next_start,
                "enddatum": next_end,
                "status": Season.Status.VORBEREITUNG,
            }
        )
    return render(request, "teams/season_form.html", {"form": form, "titel": "Neue Saison anlegen"})


@role_required(ADMIN_GROUP)
def season_edit(request, pk):
    """Saison-Stammdaten und Zeitraum bearbeiten."""
    saison = get_object_or_404(Season, pk=pk)
    if request.method == "POST":
        form = SeasonForm(request.POST, instance=saison)
        if form.is_valid():
            saison = form.save()
            if form.cleaned_data.get("als_aktiv_setzen"):
                set_active_season(saison, user=request.user)
            messages.success(request, f"Saison {saison.name} erfolgreich gespeichert.")
            return redirect("teams:season_list")
    else:
        form = SeasonForm(instance=saison)
    return render(
        request,
        "teams/season_form.html",
        {"form": form, "saison": saison, "titel": f"Saison {saison.name} bearbeiten"},
    )


@role_required(ADMIN_GROUP)
@require_POST
def season_activate(request, pk):
    """Setzt eine Saison als aktive Hauptsaison."""
    saison = get_object_or_404(Season, pk=pk)
    set_active_season(saison, user=request.user)
    messages.success(request, f"Saison {saison.name} ist nun die aktive Hauptsaison.")
    return redirect("teams:season_list")


@role_required(ADMIN_GROUP)
@require_POST
def season_archive(request, pk):
    """Archiviert eine beendete Saison (Schreibschutz)."""
    saison = get_object_or_404(Season, pk=pk)
    force = request.POST.get("force") == "1"
    erfolg, warnungen = archive_season(saison, force=force, user=request.user)
    if not erfolg:
        spiele_str = ", ".join(warnungen[:3])
        if len(warnungen) > 3:
            spiele_str += f" und {len(warnungen) - 3} weitere"
        messages.warning(
            request,
            f"Saison {saison.name} enthält noch ungespielte Begegnungen ({spiele_str}). "
            f"Zum Erzwingen bitte Bestätigung aktivieren.",
        )
    else:
        messages.success(request, f"Saison {saison.name} wurde erfolgreich archiviert.")
    return redirect("teams:season_list")


@role_required(ADMIN_GROUP)
@require_POST
def season_reopen(request, pk):
    """Reaktiviert eine archivierte Saison."""
    saison = get_object_or_404(Season, pk=pk)
    reopen_season(saison, user=request.user)
    messages.success(request, f"Saison {saison.name} wurde reaktiviert.")
    return redirect("teams:season_list")


@role_required(ADMIN_GROUP)
@require_POST
def season_delete(request, pk):
    """Löscht eine ungenutzte Saison."""
    from django.core.exceptions import ValidationError
    saison = get_object_or_404(Season, pk=pk)
    try:
        delete_season(saison, user=request.user)
        messages.success(request, f"Saison {saison.name} wurde gelöscht.")
    except ValidationError as e:
        messages.error(request, str(e.message if hasattr(e, "message") else e))
    return redirect("teams:season_list")


@role_required(ADMIN_GROUP)
def season_rollover(request, pk):
    """Geführte Mannschaftsübernahme aus der Vorsaison."""
    target_season = get_object_or_404(Season, pk=pk)
    quelle_id = request.GET.get("quelle")
    if quelle_id:
        source_season = Season.objects.filter(pk=quelle_id).first()
    else:
        source_season = Season.objects.filter(startdatum__lt=target_season.startdatum).order_by("-startdatum").first()

    if request.method == "POST":
        source_season_id = request.POST.get("source_season_id")
        source_season = get_object_or_404(Season, pk=source_season_id)
        teams_payload = []
        for team in source_season.teams.all():
            prefix = f"team_{team.pk}"
            if request.POST.get(f"{prefix}_uebernehmen"):
                payload_entry = {
                    "source_team_id": team.pk,
                    "uebernehmen": True,
                    "liga": request.POST.get(f"{prefix}_liga", team.liga),
                    "altersklasse": team.altersklasse,
                    "brettanzahl": int(request.POST.get(f"{prefix}_brettanzahl", team.brettanzahl) or team.brettanzahl),
                }
                kap_val = request.POST.get(f"{prefix}_kapitaen")
                if kap_val:
                    try:
                        payload_entry["kapitaen_id"] = int(kap_val)
                    except (ValueError, TypeError):
                        pass
                else:
                    payload_entry["kapitaen_id"] = None
                teams_payload.append(payload_entry)

        created_teams = rollover_teams(
            source_season=source_season,
            target_season=target_season,
            teams_payload=teams_payload,
            user=request.user,
        )
        messages.success(
            request,
            f"{len(created_teams)} Mannschaften erfolgreich in Saison {target_season.name} übernommen.",
        )
        return redirect(f"{reverse('teams:team_list')}?saison={target_season.pk}")

    form = SeasonRolloverForm(source_season=source_season, target_season=target_season)
    moegliche_quellen = Season.objects.exclude(pk=target_season.pk).order_by("-startdatum")
    kontext = {
        "target_season": target_season,
        "source_season": source_season,
        "moegliche_quellen": moegliche_quellen,
        "form": form,
        "titel": f"Mannschaftsübernahme nach {target_season.name}",
    }
    return render(request, "teams/season_rollover.html", kontext)

