from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

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


def role_required(*allowed_roles):
    """Login-Check zuerst, dann Rollen-Check (403 bei Fehlrolle)."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if role_of(request.user) not in allowed_roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
