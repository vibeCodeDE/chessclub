"""Saison-Kontext für alle Templates."""

from .models import Season


def season_context(request):
    """Stellt aktive Saison, gewählte Saison und alle Saisons bereit."""
    alle_saisons = Season.objects.all().order_by("-startdatum")
    aktive_saison = Season.get_aktive_saison()

    gewaehlte_saison_id = request.GET.get("saison") if hasattr(request, "GET") else None
    gewaehlte_saison = None

    if gewaehlte_saison_id:
        try:
            gewaehlte_saison = Season.objects.filter(pk=int(gewaehlte_saison_id)).first()
        except (ValueError, TypeError):
            gewaehlte_saison = Season.objects.filter(slug=str(gewaehlte_saison_id)).first()

    if not gewaehlte_saison:
        gewaehlte_saison = aktive_saison

    return {
        "aktive_saison": aktive_saison,
        "alle_saisons": alle_saisons,
        "gewaehlte_saison": gewaehlte_saison,
    }
