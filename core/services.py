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


def get_demo_data_status() -> dict:
    """Ermittelt den aktuellen Zustand der Demo-Daten und prüft auf Schutz vor Datenverlust."""
    from django.contrib.auth import get_user_model
    from cashbook.models import CashEntry
    from comms.models import NewsPost
    from dues.models import MembershipFee
    from members.models import Member
    from teams.models import Team
    from tournaments.models import Tournament

    User = get_user_model()
    demo_usernames = {"vorstand", "kassenwart", "kapitaen", "mitglied"}
    demo_users_count = User.objects.filter(username__in=demo_usernames).count()

    total_members = Member.objects.count()
    total_fees = MembershipFee.objects.count()
    total_teams = Team.objects.count()
    total_tournaments = Tournament.objects.count()
    total_cash = CashEntry.objects.count()
    total_news = NewsPost.objects.count()

    is_active = (demo_users_count > 0 or total_members > 0)

    # Schutz vor Datenverlust: Prüfen, ob echte/individuelle Mitglieder vorhanden sind
    has_real_data = False
    if total_members > 0:
        for m in Member.objects.select_related("user"):
            # 1. Mitglied mit anderem Benutzerkonto verknüpft
            if m.user and m.user.username not in demo_usernames:
                has_real_data = True
                break
            # 2. Mitglied mit realer E-Mail-Adresse (nicht @example.org oder @koenigsspringer-musterstadt.de)
            email = (m.email or "").strip().lower()
            if email and not (email.endswith("@example.org") or email.endswith("@koenigsspringer-musterstadt.de")):
                has_real_data = True
                break

    return {
        "is_active": is_active,
        "demo_users_count": demo_users_count,
        "total_members": total_members,
        "total_fees": total_fees,
        "total_teams": total_teams,
        "total_tournaments": total_tournaments,
        "total_cash": total_cash,
        "total_news": total_news,
        "has_real_data": has_real_data,
        "can_load": total_members == 0,
        "can_remove": is_active and not has_real_data,
    }


def install_demo_data(user=None) -> tuple[bool, str]:
    """Lädt die realistischen Demo-Daten über das Management-Kommando atomar."""
    from django.core.management import call_command
    from members.models import Member

    if Member.objects.exists():
        return False, "Es sind bereits Mitglieder vorhanden. Bitte entfernen Sie diese vor dem Laden neuer Demo-Daten."

    call_command("seed_demo", verbosity=0)

    AuditLog.objects.create(
        benutzer=user,
        aktion="Demo-Daten geladen",
        text="Demo-Daten wurden über das Django Admin Panel geladen.",
    )
    return True, "Demo-Daten wurden erfolgreich angelegt (48 Mitglieder, Mannschaften, Turniere, Finanzen, News)."


def remove_demo_data(user=None, confirm: bool = False) -> tuple[bool, str]:
    """Entfernt Demo-Daten sicher und atomar, sofern keine echten Daten vorliegen."""
    if not confirm:
        return False, "Bitte bestätigen Sie das Entfernen der Demo-Daten über die Bestätigungs-Checkbox."

    status = get_demo_data_status()
    if status["has_real_data"]:
        return (
            False,
            "Abbruch zum Schutz vor Datenverlust: Es wurden echte Mitglieder oder Benutzer gefunden, "
            "die nicht zum Standard-Demo-Bestand gehören.",
        )

    from django.contrib.auth import get_user_model
    from django.db import transaction
    from cashbook.models import CashEntry
    from comms.models import MailLog, NewsPost
    from dues.models import (
        DunningLetter,
        FeeCategory,
        MembershipFee,
        Payment,
        SepaMandate,
    )
    from members.models import ChangeRequest, Member
    from teams.models import LeagueMatch, LineupEntry, Team
    from tournaments.models import Pairing, Participant, Tournament, TournamentRound

    User = get_user_model()

    with transaction.atomic():
        Pairing.objects.all().delete()
        TournamentRound.objects.all().delete()
        Participant.objects.all().delete()
        Tournament.objects.all().delete()
        LineupEntry.objects.all().delete()
        LeagueMatch.objects.all().delete()
        Team.objects.all().delete()
        DunningLetter.objects.all().delete()
        Payment.objects.all().delete()
        MembershipFee.objects.all().delete()
        SepaMandate.objects.all().delete()
        FeeCategory.objects.all().delete()
        MailLog.objects.all().delete()
        NewsPost.objects.all().delete()
        CashEntry.objects.all().delete()
        ChangeRequest.objects.all().delete()
        Member.objects.all().delete()
        User.objects.filter(username__in=["vorstand", "kassenwart", "kapitaen", "mitglied"]).delete()
        AuditLog.objects.create(
            benutzer=user,
            aktion="Demo-Daten entfernt",
            text="Demo-Daten wurden sicher über das Django Admin Panel entfernt.",
        )

    return True, "Demo-Daten wurden erfolgreich und sicher entfernt."

