"""Tabellenberechnung je Liga (PRD S4.5)."""

from collections import defaultdict
from decimal import Decimal


def tabelle(liga, ausschluss_team=None):
    """Berechnet die Liga-Tabelle aus allen gespielten Ligaspielen.

    Berücksichtigt Mannschaftspunkte (2/1/0) und Brettpunkte aller Teams,
    die in dieser Liga gegen uns gespielt haben.
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

        zeile_gegner = zeilen[match.gegner]
        zeile_gegner["name"] = match.gegner
        zeile_gegner["spiele"] += 1
        zeile_gegner["mannschaftspunkte"] += 2 - mannschaftspunkte
        zeile_gegner["brettpunkte"] += gegner
        zeile_gegner["gegner_brettpunkte"] += eigen

    tabelle = sorted(
        zeilen.values(),
        key=lambda z: (-z["mannschaftspunkte"], -z["brettpunkte"], z["name"]),
    )
    for index, zeile in enumerate(tabelle, start=1):
        zeile["platz"] = index
        zeile["brettdifferenz"] = zeile["brettpunkte"] - zeile["gegner_brettpunkte"]
    return tabelle
