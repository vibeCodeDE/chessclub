from django.urls import NoReverseMatch, reverse

from .roles import role_of

NAV_ITEMS = [
    ("core:home", "Startseite", {"gast", "mitglied", "kapitaen", "admin"}),
    ("core:login", "Anmelden", {"gast"}),
    ("core:dashboard", "Dashboard", {"admin"}),
    ("members:profil", "Profil", {"mitglied", "kapitaen", "admin"}),
    ("members:member_list", "Mitglieder", {"admin"}),
    ("members:change_request_list", "Änderungswünsche", {"admin"}),
    ("dues:posten_liste", "Beiträge", {"admin"}),
    ("dues:zahlungsliste", "Zahlungen", {"admin"}),
    ("dues:mahnliste", "Mahnungen", {"admin"}),
    ("admin:index", "Verwaltung", {"admin"}),
]


def nav(request):
    role = role_of(request.user)
    links = []
    for name, label, roles in NAV_ITEMS:
        if role not in roles:
            continue
        try:
            links.append({"url": reverse(name), "label": label})
        except NoReverseMatch:
            continue
    return {"user_role": role, "nav_links": links}
