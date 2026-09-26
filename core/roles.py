ADMIN_GROUP = "admin"
KAPITAEN_GROUP = "kapitaen"
MITGLIED_GROUP = "mitglied"

ROLES = ("gast", "mitglied", "kapitaen", "admin")


def role_of(user):
    if not user.is_authenticated:
        return "gast"
    group_names = set(user.groups.values_list("name", flat=True))
    if ADMIN_GROUP in group_names:
        return "admin"
    if KAPITAEN_GROUP in group_names:
        return "kapitaen"
    return "mitglied"
