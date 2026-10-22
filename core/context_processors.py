"""Navigation, Badges und Vereinsdaten für alle Templates."""

from django.conf import settings
from django.urls import NoReverseMatch, reverse

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
            ("teams:season_list", "Saisonverwaltung", "calendar", {"admin"}, None),
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
            ("core:onboarding_wizard", "Onboarding-Assistent", "sparkle", {"admin"}, None),
            ("core:club_setup_profile", "Vereins-Setup & Daten", "sliders", {"admin"}, None),
            ("admin:index", "Verwaltung (Django-Admin)", "settings", {"admin"}, None),
            ("core:dsgvo_verzeichnis", "Verzeichnis Verarbeitungstätigkeiten", "shield", {"admin"}, None),
        ],
    ),
]

# Zuordnung von Unterseiten / Detail-Views zu ihrem Hauptnavigationspunkt
VIEW_FALLBACKS = {
    # Mitglieder
    "members:member_detail": "members:member_list",
    "members:member_update": "members:member_list",
    "members:member_create": "members:member_list",
    "members:member_status": "members:member_list",
    "members:member_delete": "members:member_list",
    "members:member_export": "members:member_list",
    "members:change_request_approve": "members:change_request_list",
    "members:change_request_reject": "members:change_request_list",
    # Finanzen & Beiträge
    "dues:run_lauf": "dues:overview",
    "dues:fee_detail": "dues:overview",
    "dues:payment_create": "dues:overview",
    "dues:payment_storno": "dues:overview",
    "dues:sepa_sammelverbuchung": "dues:overview",
    "dues:sepa_export": "dues:overview",
    "dues:export": "dues:overview",
    "dues:category_update": "dues:category_list",
    "dues:category_toggle": "dues:category_list",
    "dues:category_delete": "dues:category_list",
    "dues:mandate_create": "dues:mandate_list",
    "dues:mandate_update": "dues:mandate_list",
    "dues:dunning_create": "dues:dunning_list",
    "dues:dunning_letter": "dues:dunning_list",
    "dues:kassenbericht_export": "dues:kassenbericht",
    # Spielbetrieb
    "teams:season_create": "teams:season_list",
    "teams:season_edit": "teams:season_list",
    "teams:season_activate": "teams:season_list",
    "teams:season_archive": "teams:season_list",
    "teams:season_reopen": "teams:season_list",
    "teams:season_delete": "teams:season_list",
    "teams:season_rollover": "teams:season_list",
    "teams:team_create": "teams:team_list",
    "teams:team_detail": "teams:team_list",
    "teams:team_update": "teams:team_list",
    "teams:team_delete": "teams:team_list",
    "teams:match_create": "teams:match_list",
    "teams:match_detail": "teams:match_list",
    "teams:match_print": "teams:match_list",
    "teams:match_update": "teams:match_list",
    "teams:match_delete": "teams:match_list",
    "teams:lineup_board_save": "teams:match_list",
    "teams:lineup_save": "teams:match_list",
    # Turniere
    "tournaments:manage_create": "tournaments:manage_list",
    "tournaments:manage_detail": "tournaments:manage_list",
    "tournaments:manage_update": "tournaments:manage_list",
    "tournaments:manage_delete": "tournaments:manage_list",
    "tournaments:participant_create": "tournaments:manage_list",
    "tournaments:participant_toggle_startgeld": "tournaments:manage_list",
    "tournaments:participant_delete": "tournaments:manage_list",
    "tournaments:round_generate": "tournaments:manage_list",
    "tournaments:round_delete": "tournaments:manage_list",
    "tournaments:pairing_result": "tournaments:manage_list",
    "tournaments:tournament_finish": "tournaments:manage_list",
    "tournaments:export_csv": "tournaments:manage_list",
    "tournaments:print_results": "tournaments:manage_list",
    "tournaments:round_print": "tournaments:manage_list",
    "tournaments:public_detail": "tournaments:public_list",
    # Kommunikation
    "comms:news_create": "comms:news_list",
    "comms:news_update": "comms:news_list",
    "comms:news_delete": "comms:news_list",
    "comms:news_toggle": "comms:news_list",
    # Kassenbuch
    "cashbook:entry_create": "cashbook:entry_list",
    "cashbook:entry_update": "cashbook:entry_list",
    "cashbook:entry_storno": "cashbook:entry_list",
    "cashbook:jahresabschluss": "cashbook:entry_list",
    "cashbook:export": "cashbook:entry_list",
    # Vereins-Setup & System
    "core:club_setup": "core:club_setup_profile",
    "core:club_setup_dues": "core:club_setup_profile",
    "core:club_setup_teams": "core:club_setup_profile",
    "core:club_setup_members_import": "core:club_setup_profile",
    "core:club_setup_import_muster": "core:club_setup_profile",
    "core:onboarding_step_1": "core:onboarding_wizard",
    "core:onboarding_step_2": "core:onboarding_wizard",
    "core:onboarding_step_3": "core:onboarding_wizard",
    "core:onboarding_step_4": "core:onboarding_wizard",
    "core:onboarding_step_5": "core:onboarding_wizard",
    "core:onboarding_step_6": "core:onboarding_wizard",
}


def _is_nav_item_allowed(url_name, request):
    if url_name == "core:home" and not is_module_active("homepage", request):
        return False
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


def _mark_active_nav_links(sektionen, request):
    """Ermittelt den aktiven Menüpunkt präzise anhand von Resolver, URL oder Pfad-Präfix."""
    if not request:
        return
    current_path = getattr(request, "path", "")
    resolver_match = getattr(request, "resolver_match", None)
    view_name = getattr(resolver_match, "view_name", "") if resolver_match else ""

    all_links = []
    for sektion in sektionen:
        sektion["is_active"] = False
        for link in sektion["links"]:
            if "url" not in link:
                try:
                    link["url"] = reverse(link["url_name"])
                except NoReverseMatch:
                    link["url"] = ""
            link["is_active"] = False
            all_links.append(link)

    matched_link = None

    # 1. Direkter Resolver-Match (z. B. "members:member_list")
    if view_name:
        for link in all_links:
            if link["url_name"] == view_name:
                matched_link = link
                break

    # 2. Bekannte Unterseiten-Zuordnung (z. B. "members:member_detail" -> "members:member_list")
    if not matched_link and view_name and view_name in VIEW_FALLBACKS:
        target_name = VIEW_FALLBACKS[view_name]
        for link in all_links:
            if link["url_name"] == target_name:
                matched_link = link
                break

    # 3. Exakter Pfadabgleich
    if not matched_link and current_path:
        for link in all_links:
            if link["url"] and link["url"] == current_path:
                matched_link = link
                break

    # 4. Längster Pfad-Präfix-Match (ohne Root '/' oder '/dashboard/', um Fehlmatches zu verhindern)
    if not matched_link and current_path:
        candidates = []
        for link in all_links:
            url = link["url"]
            if url and url not in ("/", "/dashboard/"):
                if current_path.startswith(url):
                    candidates.append((len(url), link))
        if candidates:
            candidates.sort(key=lambda c: c[0], reverse=True)
            matched_link = candidates[0][1]

    if matched_link:
        matched_link["is_active"] = True
        for sektion in sektionen:
            if matched_link in sektion["links"]:
                sektion["is_active"] = True
                break


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
            try:
                link_url = reverse(url_name)
            except NoReverseMatch:
                link_url = ""
            links.append(
                {
                    "url_name": url_name,
                    "label": label,
                    "icon": icon,
                    "badge": badges.get(badge_key) if badge_key else None,
                    "url": link_url,
                    "is_active": False,
                }
            )
        if links:
            sektionen.append({"titel": titel, "links": links, "is_active": False})

    _mark_active_nav_links(sektionen, request)

    from .services import get_club_profile

    profil = get_club_profile(request)

    return {
        "pwa_aktiv": getattr(settings, "PWA_AKTIV", False),
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
