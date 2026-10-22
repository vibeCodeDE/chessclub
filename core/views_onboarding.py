"""Views für den mehrstufigen Onboarding-Assistenten (PRD S7.5, US1-US5)."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.constants import DEFAULT_FEE_CATEGORIES
from core.forms_onboarding import (
    OnboardingModulesForm,
    OnboardingProfileForm,
    OnboardingQuickFeeForm,
)
from core.models import (
    AuditLog,
    ClubProfile,
    ModuleSettings,
    OnboardingProgress,
    StaffInvitation,
)
from core.roles import ADMIN_GROUP, role_required
from core.services import (
    apply_default_fee_categories,
    complete_onboarding,
    create_staff_invitation,
    get_demo_data_status,
)
from dues.models import FeeCategory
from members.models import Member
from teams.models import Team

User = get_user_model()


def _get_stepper_context(schritt: int, titel: str) -> dict:
    alle_schritte = [
        {"nummer": 1, "titel": "Stammdaten"},
        {"nummer": 2, "titel": "Module"},
        {"nummer": 3, "titel": "Beiträge"},
        {"nummer": 4, "titel": "Mitglieder"},
        {"nummer": 5, "titel": "Funktionäre"},
        {"nummer": 6, "titel": "Abschluss"},
    ]
    prozent = int((schritt / 6) * 100)
    return {
        "aktueller_schritt": schritt,
        "schritte_anzahl": 6,
        "schritt_titel": titel,
        "fortschritt_prozent": prozent,
        "alle_schritte": alle_schritte,
    }


@role_required(ADMIN_GROUP)
def onboarding_wizard_entry(request):
    """Einstiegspunkt für das Onboarding: leitet zum aktuellen Schritt weiter."""
    progress = OnboardingProgress.get_solo()
    schritt = progress.aktueller_schritt or 1
    if schritt < 1 or schritt > 6:
        schritt = 1
    return redirect(f"core:onboarding_step_{schritt}")


@role_required(ADMIN_GROUP)
def onboarding_step_back(request, schritt: int):
    """Erlaubt dem Administrator, zu einem vorherigen Schritt zurückzuspringen."""
    if 1 <= schritt <= 6:
        return redirect(f"core:onboarding_step_{schritt}")
    return redirect("core:onboarding_step_1")


@role_required(ADMIN_GROUP)
def onboarding_step_1_profile(request):
    """Schritt 1: Vereinsstammdaten & Verbandszugehörigkeit (ZPS)."""
    club = ClubProfile.get_solo()
    progress = OnboardingProgress.get_solo()

    if request.method == "POST":
        form = OnboardingProfileForm(request.POST, instance=club)
        if form.is_valid():
            form.save()
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Vereinsprofil im Onboarding aktualisiert",
                text=f"Stammdaten für '{club.name}' im Onboarding hinterlegt.",
            )
            progress.mark_step_completed("profil", next_step=2)
            messages.success(request, "Vereinsstammdaten erfolgreich gespeichert.")
            return redirect("core:onboarding_step_2")
    else:
        form = OnboardingProfileForm(instance=club)

    kontext = {
        **_get_stepper_context(1, "Vereinsidentität & Spielabend"),
        "form": form,
        "club": club,
    }
    return render(request, "core/onboarding/step_1_profile.html", kontext)


@role_required(ADMIN_GROUP)
def onboarding_step_2_modules(request):
    """Schritt 2: Modulauswahl (Satellitenmodule aktivieren/deaktivieren)."""
    modules = ModuleSettings.get_solo()
    progress = OnboardingProgress.get_solo()

    if request.method == "POST":
        form = OnboardingModulesForm(request.POST, instance=modules)
        if form.is_valid():
            form.save()
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Module im Onboarding konfiguriert",
                text="Satellitenmodule im Onboarding angepasst.",
            )
            progress.mark_step_completed("module", next_step=3)
            messages.success(request, "Modul-Einstellungen erfolgreich gespeichert.")
            return redirect("core:onboarding_step_3")
    else:
        form = OnboardingModulesForm(instance=modules)

    kontext = {
        **_get_stepper_context(2, "Module auswählen"),
        "form": form,
        "modules": modules,
    }
    return render(request, "core/onboarding/step_2_modules.html", kontext)


@role_required(ADMIN_GROUP)
def onboarding_step_3_dues(request):
    """Schritt 3: Beitragsstruktur & Standard-Kategorien."""
    progress = OnboardingProgress.get_solo()
    kategorien = FeeCategory.objects.all().order_by("name")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "apply_defaults":
            anzahl = apply_default_fee_categories(user=request.user)
            messages.success(request, f"{anzahl} Standard-Beitragskategorien wurden erfolgreich angelegt.")
            return redirect("core:onboarding_step_3")
        elif action == "create_fee":
            fee_form = OnboardingQuickFeeForm(request.POST)
            if fee_form.is_valid():
                fee_form.save()
                messages.success(request, f"Kategorie „{fee_form.cleaned_data['name']}“ angelegt.")
                return redirect("core:onboarding_step_3")
        elif action == "next":
            progress.mark_step_completed("beitraege", next_step=4)
            return redirect("core:onboarding_step_4")
    else:
        fee_form = OnboardingQuickFeeForm()

    kontext = {
        **_get_stepper_context(3, "Beitragskategorien einrichten"),
        "kategorien": kategorien,
        "fee_form": fee_form,
        "default_categories": DEFAULT_FEE_CATEGORIES,
    }
    return render(request, "core/onboarding/step_3_dues.html", kontext)


@role_required(ADMIN_GROUP)
def onboarding_step_4_members(request):
    """Schritt 4: Mitglieder-Datenübernahme (ZPS-Direktimport ODER CSV)."""
    progress = OnboardingProgress.get_solo()
    club = ClubProfile.get_solo()

    dry_run_ergebnis = None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "import_zps":
            from members.services.dsb_sync import import_dsb_initial

            vkz = request.POST.get("zps_nummer", club.zps_nummer or "").strip()
            if not vkz:
                messages.error(request, "Bitte eine gültige DSB-Vereinskennziffer angeben.")
            else:
                res = import_dsb_initial(vkz=vkz, user=request.user)
                if res.erfolg:
                    messages.success(
                        request,
                        f"Erfolg: {res.anzahl_neu} Mitglieder aus DSB-Portal importiert ({res.anzahl_uebersprungen} übersprungen).",
                    )
                    progress.mark_step_completed("mitglieder", next_step=5)
                    return redirect("core:onboarding_step_5")
                else:
                    messages.error(request, f"DSB-Abruf fehlgeschlagen: {'; '.join(res.fehler_meldungen)}")
        elif action in {"validate_csv", "execute_csv"}:
            from core.forms_setup import (
                MAX_MEMBER_CSV_SIZE_BYTES,
                MAX_MEMBER_CSV_SIZE_MB,
            )
            from members.services.import_service import (
                execute_members_import,
                parse_members_csv,
                validate_members_import,
            )

            csv_file = request.FILES.get("csv_datei")
            if not csv_file and action == "validate_csv":
                messages.error(request, "Bitte eine CSV-Datei auswählen.")
            elif csv_file and hasattr(csv_file, "size") and csv_file.size > MAX_MEMBER_CSV_SIZE_BYTES:
                messages.error(
                    request,
                    f"Die Datei ist zu groß ({csv_file.size / (1024 * 1024):.1f} MB). "
                    f"Erlaubt sind maximal {MAX_MEMBER_CSV_SIZE_MB} MB.",
                )
            else:
                if csv_file:
                    request.session["_onboarding_csv_content"] = csv_file.read().decode("utf-8", errors="replace")
                csv_content = request.session.get("_onboarding_csv_content", "")
                rows, err = parse_members_csv(csv_content)
                if err:
                    messages.error(request, err)
                else:
                    dry_run_ergebnis = validate_members_import(rows)
                    if action == "execute_csv" and dry_run_ergebnis.hat_fehler is False:
                        stats = execute_members_import(rows, actor=request.user)
                        messages.success(request, f"{stats['imported_members']} Mitglieder erfolgreich importiert.")
                        progress.mark_step_completed("mitglieder", next_step=5)
                        return redirect("core:onboarding_step_5")
        elif action in {"skip", "next"}:
            progress.mark_step_completed("mitglieder", next_step=5)
            return redirect("core:onboarding_step_5")

    mitglieder_anzahl = Member.objects.filter(status="aktiv").count()
    kontext = {
        **_get_stepper_context(4, "Mitglieder & Bestandsdaten"),
        "club": club,
        "mitglieder_anzahl": mitglieder_anzahl,
        "dry_run": dry_run_ergebnis,
    }
    return render(request, "core/onboarding/step_4_members.html", kontext)


@role_required(ADMIN_GROUP)
def onboarding_step_5_staff(request):
    """Schritt 5: Funktionäre & Vorstandskollegen per E-Mail einladen."""
    progress = OnboardingProgress.get_solo()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "invite":
            email = request.POST.get("email", "").strip()
            vorname = request.POST.get("vorname", "").strip()
            nachname = request.POST.get("nachname", "").strip()
            rolle = request.POST.get("rolle", "admin").strip()

            if not email or not vorname or not nachname:
                messages.error(request, "Bitte Name, Vorname und E-Mail-Adresse vollständig ausfüllen.")
            else:
                basis_url = request.build_absolute_uri("/").rstrip("/")
                invitation = create_staff_invitation(
                    email=email,
                    vorname=vorname,
                    nachname=nachname,
                    rolle=rolle,
                    invited_by=request.user,
                    send_mail=True,
                    basis_url=basis_url,
                )
                request.session["_onboarding_last_invitation_id"] = invitation.pk
                messages.success(request, f"Einladung an {email} ({rolle}) wurde erstellt.")
                return redirect("core:onboarding_step_5")
        elif action in {"skip", "next"}:
            progress.mark_step_completed("funktionaere", next_step=6)
            return redirect("core:onboarding_step_6")

    last_id = request.session.pop("_onboarding_last_invitation_id", None)
    letzte_einladung = StaffInvitation.objects.filter(pk=last_id).first() if last_id else None
    einladungen = StaffInvitation.objects.all().order_by("-erstellt_am")
    kontext = {
        **_get_stepper_context(5, "Funktionäre einladen"),
        "einladungen": einladungen,
        "letzte_einladung": letzte_einladung,
    }
    return render(request, "core/onboarding/step_5_staff.html", kontext)


@role_required(ADMIN_GROUP)
def onboarding_step_6_finish(request):
    """Schritt 6: Zusammenfassung, Demo-Daten-Bereinigung und Produktivstart."""
    club = ClubProfile.get_solo()
    modules = ModuleSettings.get_solo()
    kategorien_count = FeeCategory.objects.count()
    mitglieder_count = Member.objects.filter(status="aktiv").count()
    teams_count = Team.objects.count()
    einladungen_count = StaffInvitation.objects.count()
    demo_status = get_demo_data_status()

    if request.method == "POST":
        cleanup = request.POST.get("cleanup_demodata") == "1"
        complete_onboarding(user=request.user, cleanup_demodata=cleanup)
        messages.success(request, "🎉 Herzlichen Glückwunsch! Dein Schachverein ist jetzt startklar.")
        return redirect("core:dashboard")

    kontext = {
        **_get_stepper_context(6, "Zusammenfassung & Produktivstart"),
        "club": club,
        "modules": modules,
        "kategorien_count": kategorien_count,
        "mitglieder_count": mitglieder_count,
        "teams_count": teams_count,
        "einladungen_count": einladungen_count,
        "demo_status": demo_status,
    }
    return render(request, "core/onboarding/step_6_finish.html", kontext)


@require_POST
@role_required(ADMIN_GROUP)
def dismiss_onboarding_checklist(request):
    """Blendet das Dashboard-Widget 'Erste Schritte' dauerhaft aus."""
    progress = OnboardingProgress.get_solo()
    progress.checklist_ausgeblendet = True
    progress.save()

    AuditLog.objects.create(
        benutzer=request.user,
        aktion="Onboarding-Checkliste ausgeblendet",
        text="Die 'Erste Schritte'-Checkliste auf dem Dashboard wurde ausgeblendet.",
    )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"erfolg": True})
    messages.info(request, "Die 'Erste Schritte'-Checkliste wurde ausgeblendet.")
    return redirect("core:dashboard")
