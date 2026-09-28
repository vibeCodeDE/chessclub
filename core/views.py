from django.http import JsonResponse
from django.shortcuts import render

from members.models import ChangeRequest

from .roles import ADMIN_GROUP, role_required


def health(request):
    return JsonResponse({"status": "ok"})


def home(request):
    return render(request, "core/home.html")


@role_required(ADMIN_GROUP)
def dashboard(request):
    """Kachel-Übersicht für die Vorstand (PRD M7.1).

    Nur die Wunsch-Kachel liefert bis T6 echte Zahlen; Beiträge (T11),
    Termine (T16/T19) und Anmeldungen (T19) bleiben Platzhalter.
    """
    offene_wuensche = ChangeRequest.objects.filter(
        status=ChangeRequest.Status.EINGEREICHT
    ).count()
    tiles = [
        {
            "key": "beitraege",
            "titel": "Offene Beiträge",
            "wert": None,
            "placeholder": True,
            "hinweis": "Verfügbar nach dem Beitragslauf.",
            "url": None,
        },
        {
            "key": "termine",
            "titel": "Anstehende Termine",
            "wert": None,
            "placeholder": True,
            "hinweis": "Verfügbar ab Spielbetrieb und Turnieren.",
            "url": None,
        },
        {
            "key": "wuensche",
            "titel": "Offene Änderungswünsche",
            "wert": offene_wuensche,
            "placeholder": False,
            "hinweis": "Noch nicht freigegebene Wünsche auf Stammdaten.",
            "url": "members:change_request_list",
        },
        {
            "key": "anmeldungen",
            "titel": "Letzte Anmeldungen",
            "wert": None,
            "placeholder": True,
            "hinweis": "Verfügbar ab der öffentlichen Turnieranmeldung.",
            "url": None,
        },
    ]
    return render(request, "core/dashboard.html", {"tiles": tiles})
