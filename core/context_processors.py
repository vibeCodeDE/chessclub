"""Navigation, Badges und Vereinsdaten für alle Templates."""

from django.conf import settings

from .roles import ADMIN_GROUP, role_of

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
            ("admin:index", "Verwaltung (Django-Admin)", "settings", {"admin"}, None),
            ("core:dsgvo_verzeichnis", "Verzeichnis Verarbeitungstätigkeiten", "shield", {"admin"}, None),
        ],
    ),
]


def _badges(role):
    """Zähler für die Navigation – nur laden, was die Rolle auch sieht."""
    if role != ADMIN_GROUP:
        return {}
    from comms.models import NewsPost
    from dues.models import MembershipFee
    from members.models import ChangeRequest
    from tournaments.models import Tournament

    offene_posten = sum(
        1
        for fee in MembershipFee.objects.prefetch_related("zahlungen").all()[:500]
        if fee.ist_offen
    )
    return {
        "wuensche": ChangeRequest.objects.filter(status=ChangeRequest.Status.EINGEREICHT).count(),
        "entwuerfe": NewsPost.objects.filter(veroeffentlicht=False).count(),
        "offene_posten": offene_posten,
        "mahnungen": MembershipFee.objects.filter(mahnstufe__gt=0).count(),
        "turniere": Tournament.objects.exclude(status=Tournament.Status.BEENDET).count(),
    }


def nav(request):
    user = getattr(request, "user", None)
    role = role_of(user)
    badges = _badges(role)
    sektionen = []
    for titel, eintraege in NAV_STRUKTUR:
        links = []
        for url_name, label, icon, rollen, badge_key in eintraege:
            if role not in rollen:
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

    return {
        "user_role": role,
        "nav_sektionen": sektionen,
        "nav_links": [
            {"url_name": link["url_name"], "label": link["label"]}
            for sektion in sektionen
            for link in sektion["links"]
        ],
        "club_name": settings.CLUB_NAME,
        "club_short": settings.CLUB_SHORT,
        "club_contact": settings.CLUB_CONTACT,
        # Profil der öffentlichen Vereinsseite (ADR-012) – leere Werte blenden
        # die betroffenen Zeilen im Template aus.
        "club_founded": settings.CLUB_FOUNDED,
        "club_location": settings.CLUB_LOCATION,
        "club_room": settings.CLUB_ROOM,
        "club_night_hours": settings.CLUB_NIGHT_HOURS,
        "club_youth_hours": settings.CLUB_YOUTH_HOURS,
        "club_description": settings.CLUB_DESCRIPTION,
    }
