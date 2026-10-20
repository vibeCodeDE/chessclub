"""Anmeldung mit Zwei-Faktor-Schritt für die Vorstandschaft (PRD N1.6)."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from core.models import TwoFactorDevice
from core.roles import ADMIN_GROUP
from core.twofa import code_pruefen_schritt, neues_secret, otpauth_uri

SESSION_SCHLUESSEL = "_2fa_user_id"
SESSION_SECRET = "_2fa_secret"
SESSION_FEHLSCHLAEGE = "_2fa_fehlschlaege"
MAX_FEHLSCHLAEGE = 5


def zwei_faktor_pflicht():
    """2FA ist für die Admin-Gruppe verbindlich (abschaltbar nur über die Umgebung)."""
    return str(getattr(settings, "TWOFA_PFLICHT", True)).lower() not in {"0", "false", "off", "no"}


def _ist_vorstand(user):
    return user.groups.filter(name=ADMIN_GROUP).exists()


def _braucht_zwei_faktor(user):
    """Vorstand immer – wer ein Gerät eingerichtet hat, aber auch (Sicherheit)."""
    if _ist_vorstand(user) and zwei_faktor_pflicht():
        return True
    return TwoFactorDevice.objects.filter(user=user).exists()


def _sicheres_ziel(ziel, request):
    """Prüft, ob die Ziel-URL ein sicheres internes Weiterleitungsziel ist (CWE-601)."""
    if ziel and url_has_allowed_host_and_scheme(
        ziel,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return ziel
    return ""


def anmelden(request):
    """LoginView-Ersatz: Passwort prüfen, danach ggf. TOTP abfragen."""
    if request.user.is_authenticated:
        ziel = _sicheres_ziel(request.GET.get("next", ""), request)
        return redirect(ziel or "core:dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        ziel = _sicheres_ziel(
            request.POST.get("next") or request.GET.get("next") or "",
            request,
        )
        if _braucht_zwei_faktor(user):
            request.session[SESSION_SCHLUESSEL] = user.pk
            request.session["_2fa_backend"] = getattr(
                user, "backend", "django.contrib.auth.backends.ModelBackend"
            )
            request.session["_2fa_next"] = ziel
            request.session[SESSION_FEHLSCHLAEGE] = 0
            return redirect("core:zwei_faktor")
        login(request, user)
        if not ziel and _ist_vorstand(user):
            from core.models import OnboardingProgress
            if OnboardingProgress.is_onboarding_needed():
                return redirect("core:onboarding_wizard")
        return redirect(ziel or "core:dashboard")

    next_url = _sicheres_ziel(request.GET.get("next", ""), request)
    return render(request, "registration/login.html", {"form": form, "next": next_url})


def zwei_faktor(request):
    """TOTP-Code bestätigen – beim ersten Mal wird das Gerät eingerichtet."""
    user_id = request.session.get(SESSION_SCHLUESSEL)
    if not user_id:
        return redirect("core:login")

    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        request.session.pop(SESSION_SCHLUESSEL, None)
        return redirect("core:login")

    device = TwoFactorDevice.objects.filter(user=user).first()
    fehler = False
    form_fehler = None

    if request.method == "POST":
        fehlschlaege = request.session.get(SESSION_FEHLSCHLAEGE, 0)
        if fehlschlaege >= MAX_FEHLSCHLAEGE:
            request.session.pop(SESSION_SCHLUESSEL, None)
            request.session.pop(SESSION_SECRET, None)
            request.session.pop(SESSION_FEHLSCHLAEGE, None)
            messages.error(request, "Zu viele fehlgeschlagene 2FA-Versuche. Bitte erneut anmelden.")
            return redirect("core:login")

        from django.utils import timezone
        code_input = request.POST.get("code", "")

        if device is None:
            secret = request.session.get(SESSION_SECRET) or neues_secret()
            request.session[SESSION_SECRET] = secret
            schritt = code_pruefen_schritt(secret, code_input)
            if schritt is not None:
                device = TwoFactorDevice.objects.create(
                    user=user,
                    secret=secret,
                    bestaetigt=True,
                    letzte_nutzung=timezone.now(),
                    letzter_zeitschritt=schritt,
                )
                request.session.pop(SESSION_SECRET, None)
            else:
                fehler = True
        else:
            schritt = code_pruefen_schritt(
                device.secret, code_input, letzter_zeitschritt=device.letzter_zeitschritt
            )
            if schritt is not None:
                device.letzte_nutzung = timezone.now()
                device.letzter_zeitschritt = schritt
                device.save(update_fields=["letzte_nutzung", "letzter_zeitschritt"])
            else:
                fehler = True

        if fehler:
            fehlschlaege += 1
            request.session[SESSION_FEHLSCHLAEGE] = fehlschlaege
            from django.contrib.auth.signals import user_login_failed
            user_login_failed.send(
                sender=user.__class__,
                credentials={"username": user.get_username()},
                request=request,
            )
            verbleibend = MAX_FEHLSCHLAEGE - fehlschlaege
            if verbleibend <= 0:
                request.session.pop(SESSION_SCHLUESSEL, None)
                request.session.pop(SESSION_SECRET, None)
                request.session.pop(SESSION_FEHLSCHLAEGE, None)
                messages.error(
                    request,
                    "Zu viele fehlgeschlagene 2FA-Versuche. Der Zugang wurde gesperrt. Bitte erneut anmelden.",
                )
                return redirect("core:login")
            form_fehler = (
                f"Der Code stimmt nicht (noch {verbleibend} Versuch{'e' if verbleibend != 1 else ''}). "
                "Bitte den aktuellen Code aus der App eingeben."
            )
        else:
            request.session.pop(SESSION_FEHLSCHLAEGE, None)
            backend = request.session.pop(
                "_2fa_backend", "django.contrib.auth.backends.ModelBackend"
            ) or "django.contrib.auth.backends.ModelBackend"
            login(request, user, backend=backend)
            request.session.pop(SESSION_SCHLUESSEL, None)
            ziel = _sicheres_ziel(request.session.pop("_2fa_next", ""), request)
            messages.success(request, "Anmeldung bestätigt.")
            if not ziel and _ist_vorstand(user):
                from core.models import OnboardingProgress
                if OnboardingProgress.is_onboarding_needed():
                    return redirect("core:onboarding_wizard")
            return redirect(ziel or "core:dashboard")

    if device is None:
        secret = request.session.get(SESSION_SECRET) or neues_secret()
        request.session[SESSION_SECRET] = secret
    else:
        secret = device.secret

    return render(
        request,
        "registration/zwei_faktor.html",
        {
            "form_fehler": form_fehler,
            "braucht_einrichtung": device is None,
            "secret": secret,
            "uri": otpauth_uri(secret, user.get_username()),
            "konto": user.get_username(),
        },
    )


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
@login_required
def zwei_faktor_neu(request):
    """Gerätewechsel mit Re-Authentication (Step-Up Authentication, PRD N1.6).

    Vor dem Löschen/Neuregistrieren des 2FA-Geräts muss das aktuelle Passwort
    des Benutzers verifiziert werden, um Kontoübernahmen bei ungesperrten Sitzungen
    zu verhindern.
    """
    konto = request.user.get_username()
    form_fehler = None

    if request.method == "POST":
        password = request.POST.get("password", "")
        if not password or not request.user.check_password(password):
            from django.contrib.auth.signals import user_login_failed
            user_login_failed.send(
                sender=request.user.__class__,
                credentials={"username": konto},
                request=request,
            )
            form_fehler = (
                "Das Passwort ist nicht korrekt. Das 2FA-Gerät wurde nicht zurückgesetzt."
            )
            messages.error(request, form_fehler)
            return render(
                request,
                "registration/zwei_faktor_neu.html",
                {"konto": konto, "form_fehler": form_fehler},
                status=400,
            )

        from core.models import AuditLog
        TwoFactorDevice.objects.filter(user=request.user).delete()
        request.session[SESSION_SCHLUESSEL] = request.user.pk
        request.session.pop(SESSION_SECRET, None)
        AuditLog.objects.create(
            benutzer=request.user,
            aktion="2FA-Gerät zurückgesetzt",
            text=f"2FA-Gerät für Benutzer '{konto}' nach Passwortbestätigung zurückgesetzt.",
        )
        messages.info(request, "Bitte richten Sie das neue Gerät ein.")
        return redirect("core:zwei_faktor")

    return render(
        request,
        "registration/zwei_faktor_neu.html",
        {"konto": konto, "form_fehler": form_fehler},
    )


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def accept_invitation(request, token):
    """Annahme einer Funktionärseinladung mit eigenem Passwort (PRD §3.8, US5)."""
    from core.models import StaffInvitation
    from core.services import accept_staff_invitation

    try:
        invitation = StaffInvitation.objects.get(token=token)
    except StaffInvitation.DoesNotExist:
        messages.error(request, "Der Einladungslink ist ungültig oder existiert nicht.")
        return redirect("core:login")

    if not invitation.is_valid:
        if invitation.status == "angenommen":
            messages.info(request, "Diese Einladung wurde bereits angenommen. Bitte melde dich an.")
        else:
            messages.error(request, "Dieser Einladungslink ist abgelaufen oder wurde widerrufen.")
        return redirect("core:login")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")

        if not username:
            messages.error(request, "Bitte einen gewünschten Benutzernamen eingeben.")
        elif password != password_confirm:
            messages.error(request, "Die Passwörter stimmen nicht überein.")
        else:
            success, user, msg = accept_staff_invitation(
                token=token, username=username, password=password
            )
            if success:
                if request.user.is_authenticated:
                    logout(request)

                if _braucht_zwei_faktor(user):
                    request.session[SESSION_SCHLUESSEL] = user.pk
                    request.session["_2fa_backend"] = "django.contrib.auth.backends.ModelBackend"
                    request.session["_2fa_next"] = ""
                    request.session[SESSION_FEHLSCHLAEGE] = 0
                    messages.success(
                        request,
                        f"Willkommen, {user.first_name}! Dein Benutzerkonto wurde aktiviert. "
                        "Bitte richte nun die Zwei-Faktor-Authentifizierung ein.",
                    )
                    return redirect("core:zwei_faktor")

                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                messages.success(
                    request,
                    f"Willkommen, {user.first_name}! Dein Benutzerkonto wurde erfolgreich aktiviert.",
                )
                return redirect("core:dashboard")
            else:
                messages.error(request, msg)

    return render(
        request,
        "core/invitation_accept.html",
        {"invitation": invitation},
    )


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def password_reset(request):
    """Passwort-Reset mit Rate-Limiting gegen E-Mail-Spam (PRD N1.6, ADR-028)."""
    from django.contrib.auth import views as django_auth_views

    return django_auth_views.PasswordResetView.as_view(
        template_name="registration/password_reset_form.html",
        success_url="/passwort/aendern/fertig/",
    )(request)
