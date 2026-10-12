"""Fachlogik für Modul-Einstellungen und Querschnittsfunktionen (T30 / ADR-019)."""


from django.http import HttpRequest

from .models import AuditLog, ModuleSettings

MODUL_SCHLUESSEL = {
    "teams": "spielbetrieb_aktiv",
    "spielbetrieb": "spielbetrieb_aktiv",
    "tournaments": "turniere_aktiv",
    "turniere": "turniere_aktiv",
    "cashbook": "kassenbuch_aktiv",
    "kassenbuch": "kassenbuch_aktiv",
    "comms": "nachrichten_aktiv",
    "nachrichten": "nachrichten_aktiv",
    "news": "nachrichten_aktiv",
}


def get_club_profile(request: HttpRequest | None = None):
    """Liefert die Singleton-Vereinsstammdaten (mit Request-Caching)."""
    if request is not None and hasattr(request, "_club_profile"):
        return request._club_profile

    from .models import ClubProfile

    try:
        profil = ClubProfile.objects.filter(pk=1).first()
    except Exception:
        profil = None

    if request is not None:
        request._club_profile = profil
    return profil


def get_module_settings(request: HttpRequest | None = None) -> ModuleSettings:
    """Liefert die Singleton-Einstellungen der Module (mit Request-Caching)."""
    if request is not None and hasattr(request, "_module_settings"):
        return request._module_settings
    try:
        settings_obj = ModuleSettings.get_solo()
    except Exception:
        # Fallback vor Migrationen oder während Test-Scaffolds
        settings_obj = ModuleSettings(
            spielbetrieb_aktiv=True,
            turniere_aktiv=True,
            kassenbuch_aktiv=True,
            nachrichten_aktiv=True,
        )
    if request is not None:
        request._module_settings = settings_obj
    return settings_obj


def is_module_active(module_key: str, request: HttpRequest | None = None) -> bool:
    """Reine Fachfunktion: Prüft, ob das angefragte Satellitenmodul aktiv ist.

    Kernmodule ('core', 'members', 'dues') sind immer aktiv (True).
    Unbekannte Module werden standardmäßig als aktiv betrachtet.
    """
    attr = MODUL_SCHLUESSEL.get(module_key.lower())
    if not attr:
        return True
    settings_obj = get_module_settings(request)
    return bool(getattr(settings_obj, attr, True))


def set_module_status(module_key: str, aktiv: bool, user=None) -> ModuleSettings:
    """Ändert den Status eines Moduls und protokolliert dies im AuditLog."""
    attr = MODUL_SCHLUESSEL.get(module_key.lower())
    if not attr:
        raise ValueError(f"Unbekanntes Modul: {module_key}")
    settings_obj = ModuleSettings.get_solo()
    alter_wert = getattr(settings_obj, attr)
    if alter_wert != aktiv:
        setattr(settings_obj, attr, aktiv)
        settings_obj.save()
        AuditLog.objects.create(
            benutzer=user,
            aktion="Modul-Einstellungen geändert",
            feld=attr,
            alt_wert=str(alter_wert),
            neu_wert=str(aktiv),
            text=f"Modul '{module_key}' auf {'aktiv' if aktiv else 'inaktiv'} gesetzt.",
        )
    return settings_obj
