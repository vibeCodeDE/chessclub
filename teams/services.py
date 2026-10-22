"""Spielbetrieb-Services: Tabellenberechnung (S4.5) und iCal-Feed (S4.6)."""

import datetime
from collections import defaultdict
from decimal import Decimal

from django.conf import settings
from django.utils import timezone


def escape_ical(text):
    """Maskiert Sonderzeichen für iCalendar Textwerte nach RFC 5545."""
    if not text:
        return ""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def generate_ical_feed(matches, kalender_name="Ligaspiele", verein_name=None):
    """Erzeugt einen RFC 5545 konformen iCalendar-Feed für eine Liste von Ligaspielen.

    Reine Funktion ohne HTTP-Kontext oder Datenbankabfragen (PRD S4.6).
    Enthält keine Aufstellungs- und keine Personendaten.
    Abgesagte Spiele werden mit STATUS:CANCELLED ausgegeben.
    """
    verein = verein_name or getattr(settings, "CLUB_NAME", "Schachverein")
    now_utc = timezone.now().strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{escape_ical(verein)}//Ligakalender//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ical(kalender_name)}",
        "X-WR-TIMEZONE:Europe/Berlin",
    ]

    for match in matches:
        uid = f"ligamatch-{match.pk}@{getattr(settings, 'CLUB_SHORT', 'schach')}.local"
        heim_label = "Heimspiel" if match.heimspiel else "Auswärtsspiel"
        summary = f"{match.team.name} – {match.gegner} ({heim_label})"

        if match.uhrzeit:
            start_dt = datetime.datetime.combine(match.datum, match.uhrzeit)
            end_dt = start_dt + datetime.timedelta(hours=4)
            dtstart = f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}"
            dtend = f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}"
        else:
            dtstart = f"DTSTART;VALUE=DATE:{match.datum.strftime('%Y%m%d')}"
            dtend = f"DTEND;VALUE=DATE:{match.datum.strftime('%Y%m%d')}"

        from .models import LeagueMatch

        status = "CANCELLED" if match.status == LeagueMatch.Status.ABGESAGT else "CONFIRMED"

        description_parts = []
        if match.team.liga:
            description_parts.append(f"Liga: {match.team.liga}")
        if match.runde:
            description_parts.append(f"Runde: {match.runde}")
        description_parts.append(f"Heimspiel: {'Ja' if match.heimspiel else 'Nein'}")
        if match.bemerkung:
            description_parts.append(f"Hinweis: {match.bemerkung}")
        description = "\\n".join(escape_ical(p) for p in description_parts)

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            dtstart,
            dtend,
            f"SUMMARY:{escape_ical(summary)}",
            f"STATUS:{status}",
        ])
        if match.ort:
            lines.append(f"LOCATION:{escape_ical(match.ort)}")
        if description:
            lines.append(f"DESCRIPTION:{description}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"



def tabelle(liga, ausschluss_team=None):
    """Berechnet die Liga-Tabelle aus allen gespielten Ligaspielen.

    Berücksichtigt Mannschaftspunkte (2/1/0), Brettpunkte aller Teams
    sowie die Buchholz-Wertung (Summe der Mannschaftspunkte aller gespielten Gegner)
    als Tiebreak (PRD S4.5).
    """
    from .models import LeagueMatch, Team

    zeilen = defaultdict(
        lambda: {
            "name": "",
            "spiele": 0,
            "mannschaftspunkte": 0,
            "brettpunkte": Decimal("0.0"),
            "gegner_brettpunkte": Decimal("0.0"),
            "eigene_mannschaft": False,
        }
    )
    gegner_pro_team = defaultdict(list)

    teams = Team.objects.filter(liga=liga) if liga else Team.objects.none()
    for team in teams:
        zeile = zeilen[team.name]
        zeile["name"] = team.name
        zeile["eigene_mannschaft"] = True

    matches = LeagueMatch.objects.filter(status=LeagueMatch.Status.GESPIELT).select_related("team")
    if liga:
        matches = matches.filter(team__liga=liga)

    for match in matches:
        eigen, gegner = match.brettpunkte
        if eigen is None:
            continue
        mannschaftspunkte = match.mannschaftspunkte
        if mannschaftspunkte is None:
            continue

        zeile_eigen = zeilen[match.team.name]
        zeile_eigen["name"] = match.team.name
        zeile_eigen["eigene_mannschaft"] = True
        zeile_eigen["spiele"] += 1
        zeile_eigen["mannschaftspunkte"] += mannschaftspunkte
        zeile_eigen["brettpunkte"] += eigen
        zeile_eigen["gegner_brettpunkte"] += gegner
        gegner_pro_team[match.team.name].append(match.gegner)

        zeile_gegner = zeilen[match.gegner]
        zeile_gegner["name"] = match.gegner
        zeile_gegner["spiele"] += 1
        zeile_gegner["mannschaftspunkte"] += 2 - mannschaftspunkte
        zeile_gegner["brettpunkte"] += gegner
        zeile_gegner["gegner_brettpunkte"] += eigen
        gegner_pro_team[match.gegner].append(match.team.name)

    for team_name, data in zeilen.items():
        data["buchholz"] = sum(zeilen[g]["mannschaftspunkte"] for g in gegner_pro_team[team_name])

    tabelle_liste = sorted(
        zeilen.values(),
        key=lambda z: (
            -z["mannschaftspunkte"],
            -z["brettpunkte"],
            -z["buchholz"],
            z["name"],
        ),
    )
    if ausschluss_team:
        tabelle_liste = [z for z in tabelle_liste if z["name"] != ausschluss_team]

    for index, zeile in enumerate(tabelle_liste, start=1):
        zeile["platz"] = index
        zeile["brettdifferenz"] = zeile["brettpunkte"] - zeile["gegner_brettpunkte"]
    return tabelle_liste


def create_season(
    *,
    name: str,
    startdatum: datetime.date,
    enddatum: datetime.date,
    notizen: str = "",
    als_aktiv_setzen: bool = False,
    user=None,
):
    """Erstellt eine neue Saison und setzt sie optional als aktive Hauptsaison."""
    from django.db import transaction

    from core.models import AuditLog

    from .models import Season

    with transaction.atomic():
        if als_aktiv_setzen:
            Season.objects.filter(ist_aktiv=True).update(ist_aktiv=False)

        status = Season.Status.AKTIV if als_aktiv_setzen else Season.Status.VORBEREITUNG
        saison = Season(
            name=name,
            startdatum=startdatum,
            enddatum=enddatum,
            status=status,
            ist_aktiv=als_aktiv_setzen,
            notizen=notizen,
        )
        saison.full_clean()
        saison.save()

        AuditLog.objects.create(
            benutzer=user,
            aktion="Saison angelegt",
            text=f"Saison {saison.name} angelegt ({startdatum:%d.%m.%Y} bis {enddatum:%d.%m.%Y}).",
            feld="name",
            neu_wert=saison.name,
        )
        return saison


def set_active_season(season, user=None):
    """Setzt die übergebene Saison atomar als einzige aktive Hauptsaison."""
    from django.db import transaction

    from core.models import AuditLog

    from .models import Season

    with transaction.atomic():
        Season.objects.exclude(pk=season.pk).filter(ist_aktiv=True).update(ist_aktiv=False)
        season.ist_aktiv = True
        if season.status == Season.Status.VORBEREITUNG:
            season.status = Season.Status.AKTIV
        season.save(update_fields=["ist_aktiv", "status", "aktualisiert_am"])

        AuditLog.objects.create(
            benutzer=user,
            aktion="Saison aktiviert",
            text=f"Saison {season.name} als aktive Hauptsaison festgelegt.",
            feld="ist_aktiv",
            alt_wert="False",
            neu_wert=season.name,
        )
        return season


def archive_season(season, *, force: bool = False, user=None):
    """Versetzt eine Saison in den Status ARCHIVIERT und aktiviert den Schreibschutz."""
    from core.models import AuditLog

    from .models import LeagueMatch, Season

    open_matches = LeagueMatch.objects.filter(team__saison=season).exclude(
        status__in=[LeagueMatch.Status.GESPIELT, LeagueMatch.Status.ABGESAGT]
    )
    if open_matches.exists() and not force:
        warnings = [f"{m.team.name} – {m.gegner} ({m.datum:%d.%m.%Y})" for m in open_matches]
        return False, warnings

    season.status = Season.Status.ARCHIVIERT
    if season.ist_aktiv:
        season.ist_aktiv = False
    season.save(update_fields=["status", "ist_aktiv", "aktualisiert_am"])

    AuditLog.objects.create(
        benutzer=user,
        aktion="Saison archiviert",
        text=f"Saison {season.name} archiviert.",
        feld="status",
        alt_wert="aktiv",
        neu_wert="archiviert",
    )
    return True, []


def reopen_season(season, user=None):
    """Reaktiviert eine archivierte Saison."""
    from core.models import AuditLog

    from .models import Season

    season.status = Season.Status.AKTIV
    season.save(update_fields=["status", "aktualisiert_am"])

    AuditLog.objects.create(
        benutzer=user,
        aktion="Saison reaktiviert",
        text=f"Saison {season.name} reaktiviert.",
        feld="status",
        alt_wert="archiviert",
        neu_wert="aktiv",
    )
    return season


def delete_season(season, user=None):
    """Löscht eine Saison, sofern keine Teams oder Turniere zugeordnet sind."""
    from django.core.exceptions import ValidationError

    from core.models import AuditLog

    if season.teams.exists():
        raise ValidationError("Saison kann nicht gelöscht werden, da ihr noch Mannschaften zugeordnet sind.")
    if hasattr(season, "turniere") and season.turniere.exists():
        raise ValidationError("Saison kann nicht gelöscht werden, da ihr noch Turniere zugeordnet sind.")

    name = season.name
    season.delete()

    AuditLog.objects.create(
        benutzer=user,
        aktion="Saison gelöscht",
        text=f"Saison {name} gelöscht.",
        feld="name",
        alt_wert=name,
    )


def rollover_teams(*, source_season, target_season, teams_payload: list[dict], user=None):
    """Übernimmt ausgewählte Mannschaften aus der Quell- in die Ziel-Saison."""
    from django.db import transaction

    from core.models import AuditLog

    from .models import Team

    created_teams = []
    with transaction.atomic():
        for item in teams_payload:
            if not item.get("uebernehmen"):
                continue
            source_team = Team.objects.get(pk=item["source_team_id"])
            team_name = item.get("name") or source_team.name
            new_team = Team.objects.create(
                saison=target_season,
                name=team_name,
                liga=item.get("liga") if item.get("liga") is not None else source_team.liga,
                altersklasse=item.get("altersklasse", source_team.altersklasse),
                brettanzahl=item.get("brettanzahl") or source_team.brettanzahl,
                kapitaen_id=item.get("kapitaen_id") if "kapitaen_id" in item else source_team.kapitaen_id,
                aktiv=True,
            )
            created_teams.append(new_team)

        AuditLog.objects.create(
            benutzer=user,
            aktion="Mannschaftsübernahme",
            text=f"{len(created_teams)} Mannschaften von {source_season.name} nach {target_season.name} übernommen.",
            feld="saison",
            alt_wert=source_season.name,
            neu_wert=target_season.name,
        )
    return created_teams


def validate_match_season_bounds(match):
    """Validiert, dass match.datum innerhalb des Zeitfensters der Saison liegt."""
    from django.core.exceptions import ValidationError

    team = getattr(match, "team", None)
    if team and match.datum:
        saison = getattr(team, "saison", None)
        if saison and (match.datum < saison.startdatum or match.datum > saison.enddatum):
            raise ValidationError(
                {"datum": f"Das Spieldatum ({match.datum:%d.%m.%Y}) liegt außerhalb der Saison {saison.name} ({saison.startdatum:%d.%m.%Y} bis {saison.enddatum:%d.%m.%Y})."}
            )


def check_match_edit_allowed(match):
    """Prüft, ob ein Ligaspiel bearbeitet werden darf (Schreibschutz bei Archivierung)."""
    from django.core.exceptions import PermissionDenied

    if match.team_id and match.team.saison.ist_archiviert:
        raise PermissionDenied(f"Die Saison {match.team.saison.name} ist archiviert und schreibgeschützt.")
