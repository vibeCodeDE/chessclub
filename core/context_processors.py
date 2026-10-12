"""Navigation, Badges und Vereinsdaten für alle Templates."""

from django.conf import settings

from .roles import ADMIN_GROUP, role_of
from .services import get_module_settings, is_module_active

# Menü: (Sektion, [(URL-Name, Label, Icon, Rollen, Badge-Schlüssel)])
NAV_STRUKTUR = [
    (
        None,
        [
            ("core:dashboard", "Dashboard", "dashboard", {"mitglied", "kapitaen", "admin"}, None),
            ("core:home", "Vereinsseite", "globe", {"mitglied", "kapitaen", "admin"}, None),
        ],
    ),
    (
        "Mein Bereich",
        [
            ("members:profil", "Mein Profil", "user", {"mitglied", "kapitaen", "admin"}, None),
            ("dues:mein_konto", "Mein Beitragskonto", "wallet", {"mitglied", "kapitaen", "admin"}, None),
            ("teams:meine_aufstellungen", "Meine Einsätze", "swords", {"mitglied", "kapitaen", "admin"}, None),
        ],
    ),
    (
        "Verein",
        [
            ("members:member_list", "Mitglieder", "users", {"admin"}, None),
            ("members:dsb_sync", "DSB-Abgleich", "refresh", {"admin"}, None),
            ("members:change_request_list", "Änderungswünsche", "edit", {"admin"}, "wuensche"),
            ("comms:news_list", "Ankündigungen", "megaphone", {"admin"}, "entwuerfe"),
            ("comms:mail_list", "E-Mail-Versand", "mail", {"admin"}, None),
            ("core:audit_list", "Audit-Protokoll", "shield", {"admin"}, None),
        ],
    ),
    (
        "Spielbetrieb",
        [
            ("teams:team_list", "Mannschaften", "flag", {"kapitaen", "admin"}, None),
            ("teams:match_list", "Ligaspiele", "calendar", {"kapitaen", "admin"}, None),
            ("teams:tabelle_list", "Ligatabellen", "table", {"mitglied", "kapitaen", "admin"}, None),
        ],
    ),
    (
        "Turniere",
        [
            ("tournaments:manage_list", "Turnierverwaltung", "trophy", {"admin"}, "turniere"),
            ("tournaments:public_list", "Turnierkalender", "calendar", {"mitglied", "kapitaen", "admin", "gast"}, None),
        ],
    ),
    (
        "Finanzen",
        [
            ("dues:overview", "Beiträge", "wallet", {"admin"}, "offene_posten"),
            ("dues:kassenbericht", "Kassenbericht Beiträge", "chart", {"admin"}, None),
            ("dues:category_list", "Beitragskategorien", "tag", {"admin"}, None),
            ("dues:mandate_list", "SEPA-Mandate", "card", {"admin"}, None),
            ("dues:dunning_list", "Mahnwesen", "alert", {"admin"}, "mahnungen"),
            ("cashbook:entry_list", "Kassenbuch", "book", {"admin"}, None),
        ],
    ),
    (
        "System",
        [
            ("core:club_setup_profile", "Vereins-Setup & Daten", "sliders", {"admin"}, None),
            ("admin:index", "Verwaltung (Django-Admin)", "settings", {"admin"}, None),
            ("core:dsgvo_verzeichnis", "Verzeichnis Verarbeitungstätigkeiten", "shield", {"admin"}, None),
        ],
    ),
]


def _is_nav_item_allowed(url_name, request):
    prefix = url_name.split(":")[0]
    if prefix == "teams" and not is_module_active("teams", request):
        return False
    if prefix == "tournaments" and not is_module_active("tournaments", request):
        return False
    if prefix == "cashbook" and not is_module_active("cashbook", request):
        return False
    if prefix == "comms" and not is_module_active("comms", request):
        return False
    return True


def _badges(role, request=None):
    """Zähler für die Navigation – nur laden, was die Rolle auch sieht und was aktiv ist."""
    if role != ADMIN_GROUP:
        return {}
    from dues.models import MembershipFee
    from members.models import ChangeRequest

    offene_posten = sum(
        1
        for fee in MembershipFee.objects.prefetch_related("zahlungen").all()[:500]
        if fee.ist_offen
    )
    res = {
        "wuensche": ChangeRequest.objects.filter(status=ChangeRequest.Status.EINGEREICHT).count(),
        "entwuerfe": 0,
        "offene_posten": offene_posten,
        "mahnungen": MembershipFee.objects.filter(mahnstufe__gt=0).count(),
        "turniere": 0,
    }
    if is_module_active("comms", request):
        from comms.models import NewsPost

        res["entwuerfe"] = NewsPost.objects.filter(veroeffentlicht=False).count()
    if is_module_active("tournaments", request):
        from tournaments.models import Tournament

        res["turniere"] = Tournament.objects.exclude(status=Tournament.Status.BEENDET).count()
    return res


def nav(request):
    user = getattr(request, "user", None)
    role = role_of(user)
    badges = _badges(role, request)
    sektionen = []
    for titel, eintraege in NAV_STRUKTUR:
        links = []
        for url_name, label, icon, rollen, badge_key in eintraege:
            if role not in rollen:
                continue
            if not _is_nav_item_allowed(url_name, request):
                continue
            links.append(
                {
                    "url_name": url_name,
                    "label": label,
                    "icon": icon,
                    "badge": badges.get(badge_key) if badge_key else None,
                }
            )
        if links:
            sektionen.append({"titel": titel, "links": links})

    from .services import get_club_profile

    profil = get_club_profile(request)

    return {
        "module_settings": get_module_settings(request),
        "user_role": role,
        "nav_sektionen": sektionen,
        "nav_links": [
            {"url_name": link["url_name"], "label": link["label"]}
            for sektion in sektionen
            for link in sektion["links"]
        ],
        "club_name": (profil.name if profil and profil.name else settings.CLUB_NAME),
        "club_short": (profil.kurzname if profil and profil.kurzname else settings.CLUB_SHORT),
        "club_contact": (profil.kontakt_email if profil and profil.kontakt_email else settings.CLUB_CONTACT),
        "club_founded": (profil.gruendungsjahr if profil and profil.gruendungsjahr else settings.CLUB_FOUNDED),
        "club_location": (profil.ort if profil and profil.ort else settings.CLUB_LOCATION),
        "club_room": (profil.spiellokal if profil and profil.spiellokal else settings.CLUB_ROOM),
        "club_night_hours": (profil.spielabend_zeiten if profil and profil.spielabend_zeiten else settings.CLUB_NIGHT_HOURS),
        "club_youth_hours": (profil.jugend_zeiten if profil and profil.jugend_zeiten else settings.CLUB_YOUTH_HOURS),
        "club_description": (profil.beschreibung if profil and profil.beschreibung else settings.CLUB_DESCRIPTION),
    }

