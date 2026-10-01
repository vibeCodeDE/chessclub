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
