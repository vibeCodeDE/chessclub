"""Beitragsverwaltung in der Oberfläche (PRD M2.2).

Die Rollenprüfung (nur Vorstand, PRD §3.8) und das Auslösen als POST liegen in
den Views; die Regelbasis des Laufs selbst in :mod:`dues.services`.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.roles import ADMIN_GROUP, role_required

from .models import FeeAmount, FeePost
from .services import eur, fuehre_lauf, plan_lauf

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
        "posts": FeePost.objects.filter(jahr=jahr).select_related(
            "member", "kategorie"
        ),
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
