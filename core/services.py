"""Fachlogik für Modul-Einstellungen und Querschnittsfunktionen (T30 / ADR-019)."""


from django.conf import settings
from django.http import HttpRequest

from .models import AuditLog, ModuleSettings


def is_marketing_site(request: HttpRequest | None = None) -> bool:
    """Prüft, ob der Request auf der zentralen Marketing-Website (z. B. schachverwaltung.de)
    oder mit gesetztem IS_MARKETING_SITE=True läuft (ADR-024)."""
    if getattr(settings, "IS_MARKETING_SITE", False):
        return True
    if request is not None:
        try:
            host = request.get_host().split(":")[0].strip().lower()
        except Exception:
            host = ""
        product_hosts = getattr(
            settings,
            "PRODUCT_HOSTS",
            ["schachverwaltung.de", "www.schachverwaltung.de", "localhost", "127.0.0.1"],
        )
        if isinstance(product_hosts, str):
            product_hosts = [h.strip().lower() for h in product_hosts.split(",") if h.strip()]
        else:
            product_hosts = [str(h).strip().lower() for h in product_hosts if h]
        if host in product_hosts:
            return True
    return False

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
    "homepage": "homepage_aktiv",
    "vereinshomepage": "homepage_aktiv",
    "webseite": "homepage_aktiv",
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
            homepage_aktiv=True,
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


def apply_default_fee_categories(user=None) -> int:
    """Richtet schachspezifische Standard-Beitragskategorien im Onboarding ein."""
    from decimal import Decimal
    from django.db import transaction
    from django.utils import timezone
    from core.constants import DEFAULT_FEE_CATEGORIES
    from dues.models import FeeCategory, FeeAmount

    jahr = timezone.localdate().year
    created_count = 0
    with transaction.atomic():
        for cat_data in DEFAULT_FEE_CATEGORIES:
            cat, created = FeeCategory.objects.get_or_create(
                name=cat_data["name"],
                defaults={"beschreibung": cat_data["beschreibung"]},
            )
            FeeAmount.objects.update_or_create(
                kategorie=cat,
                jahr=jahr,
                defaults={"betrag": Decimal(str(cat_data["betrag"]))},
            )
            if created:
                created_count += 1

        AuditLog.objects.create(
            benutzer=user,
            aktion="Beitragskategorien initialisiert",
            text=f"{created_count} Standard-Beitragskategorien im Onboarding übernommen.",
        )
    return created_count


def complete_onboarding(user, cleanup_demodata: bool = False) -> bool:
    """Schließt den Onboarding-Assistenten final ab und bereinigt optional Demo-Daten."""
    from django.utils import timezone
    from .models import OnboardingProgress

    if cleanup_demodata:
        remove_demo_data(user=user, confirm=True)

    progress = OnboardingProgress.get_solo()
    progress.ist_abgeschlossen = True
    progress.abgeschlossen_am = timezone.now()
    progress.abgeschlossen_von = user
    progress.save()

    AuditLog.objects.create(
        benutzer=user,
        aktion="Onboarding abgeschlossen",
        text=f"Das Vereins-Onboarding wurde von '{user.get_username()}' erfolgreich abgeschlossen.",
    )
    return True


def get_onboarding_checklist_status(user=None) -> dict:
    """Ermittelt den Erledigungsstatus der Onboarding-Aufgaben für das Vorstandsdashboard."""
    from django.contrib.auth import get_user_model
    from django.urls import reverse
    from core.models import ClubProfile, OnboardingProgress, StaffInvitation
    from core.roles import ADMIN_GROUP
    from dues.models import FeeCategory
    from members.models import Member
    from teams.models import Team

    User = get_user_model()
    progress = OnboardingProgress.get_solo()

    if progress.checklist_ausgeblendet:
        return {
            "sichtbar": False,
            "aufgaben": [],
            "gesamt_schritte": 0,
            "erledigte_schritte": 0,
            "fortschritt_prozent": 0,
        }

    club = ClubProfile.get_solo()
    has_profile = bool(club.name and club.kontakt_email)
    has_dues = FeeCategory.objects.filter(aktiv=True).exists()
    has_members = Member.objects.filter(status="aktiv").exists()
    has_teams = Team.objects.exists()
    has_staff = (
        StaffInvitation.objects.exists()
        or User.objects.filter(groups__name=ADMIN_GROUP).count() > 1
    )

    aufgaben = [
        {
            "id": "profil",
            "titel": "Vereinsprofil & Spiellokal hinterlegen",
            "erledigt": has_profile,
            "url": reverse("core:club_setup_profile"),
        },
        {
            "id": "beitraege",
            "titel": "Beitragskategorien einrichten",
            "erledigt": has_dues,
            "url": reverse("core:club_setup_dues"),
        },
        {
            "id": "mitglieder",
            "titel": "Mitglieder importieren oder anlegen",
            "erledigt": has_members,
            "url": reverse("core:club_setup_members_import"),
        },
        {
            "id": "mannschaften",
            "titel": "Erste Mannschaft anlegen",
            "erledigt": has_teams,
            "url": reverse("core:club_setup_teams"),
        },
        {
            "id": "funktionaere",
            "titel": "Vorstandskollegen oder Kapitäne einladen",
            "erledigt": has_staff,
            "url": reverse("core:onboarding_step_5"),
        },
    ]

    erledigt_count = sum(1 for a in aufgaben if a["erledigt"])
    gesamt_count = len(aufgaben)
    prozent = int((erledigt_count / gesamt_count) * 100) if gesamt_count else 0

    return {
        "sichtbar": True,
        "aufgaben": aufgaben,
        "gesamt_schritte": gesamt_count,
        "erledigte_schritte": erledigt_count,
        "fortschritt_prozent": prozent,
    }


def create_staff_invitation(
    email: str,
    vorname: str,
    nachname: str,
    rolle: str,
    invited_by,
    send_mail: bool = True,
    basis_url: str = "",
):
    """Erzeugt eine Einladung für einen Funktionär und verschickt optional die Einladungsmail."""
    import secrets
    from datetime import timedelta
    from django.conf import settings
    from django.core.mail import send_mail as django_send_mail
    from django.utils import timezone
    from core.models import ClubProfile, StaffInvitation

    token = secrets.token_urlsafe(32)
    gueltig_bis = timezone.now() + timedelta(days=7)

    StaffInvitation.objects.filter(email__iexact=email.strip(), status="offen").update(
        status="widerrufen"
    )

    invitation = StaffInvitation.objects.create(
        email=email.strip().lower(),
        vorname=vorname.strip(),
        nachname=nachname.strip(),
        rolle=rolle,
        token=token,
        gueltig_bis=gueltig_bis,
        eingeladen_von=invited_by,
        status="offen",
    )

    AuditLog.objects.create(
        benutzer=invited_by,
        aktion="Funktionärseinladung erstellt",
        text=f"Einladung für {vorname} {nachname} ({email}) mit Rolle '{rolle}' erstellt.",
    )

    if send_mail:
        club = ClubProfile.get_solo()
        verein_name = club.name or "Schachverein"
        link = f"{basis_url}/einladung/{token}/"
        betreff = f"Einladung zur Vereinsverwaltung – {verein_name}"
        nachricht = (
            f"Hallo {vorname},\n\n"
            f"du wurdest von {invited_by.get_full_name() or invited_by.username} eingeladen, "
            f"im Vorstand oder Spielbetrieb von '{verein_name}' mitzuwirken (Rolle: {invitation.get_rolle_display()}).\n\n"
            f"Bitte klicke auf den folgenden Link, um dein persönliches Passwort festzulegen:\n"
            f"{link}\n\n"
            f"Dieser Einladungslink ist 7 Tage lang gültig.\n\n"
            f"Viele Grüße,\n{verein_name}"
        )
        try:
            django_send_mail(
                subject=betreff,
                message=nachricht,
                from_email=club.kontakt_email
                or getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@schachverein.de"),
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception:
            pass

    return invitation


def accept_staff_invitation(token: str, username: str, password: str):
    """Löst ein Einladungstoken ein, legt den Benutzer an und weist die Rolle zu."""
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    from django.db import transaction
    from django.utils import timezone
    from core.models import StaffInvitation

    User = get_user_model()
    try:
        invitation = StaffInvitation.objects.get(token=token)
    except StaffInvitation.DoesNotExist:
        return False, None, "Der Einladungslink ist ungültig oder existiert nicht."

    if not invitation.is_valid:
        if invitation.status == "angenommen":
            return False, None, "Diese Einladung wurde bereits angenommen."
        return False, None, "Diese Einladung ist abgelaufen oder wurde widerrufen."

    if User.objects.filter(username__iexact=username.strip()).exists():
        return False, None, "Dieser Benutzername ist bereits vergeben."

    with transaction.atomic():
        user = User.objects.create_user(
            username=username.strip(),
            password=password,
            first_name=invitation.vorname,
            last_name=invitation.nachname,
            email=invitation.email,
            is_active=True,
            is_staff=(invitation.rolle == "admin"),
        )
        grp, _ = Group.objects.get_or_create(name=invitation.rolle)
        user.groups.add(grp)

        invitation.status = "angenommen"
        invitation.angenommen_am = timezone.now()
        invitation.benutzer = user
        invitation.save()

        AuditLog.objects.create(
            benutzer=user,
            aktion="Funktionärseinladung angenommen",
            text=f"Benutzer '{user.username}' ({invitation.email}) hat die Einladung als '{invitation.rolle}' angenommen.",
        )

    return True, user, "Einladung erfolgreich angenommen."


