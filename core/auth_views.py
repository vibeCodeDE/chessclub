"""Anmeldung mit Zwei-Faktor-Schritt für die Vorstandschaft (PRD N1.6)."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.models import TwoFactorDevice
from core.roles import ADMIN_GROUP
from core.twofa import code_pruefen, neues_secret, otpauth_uri

SESSION_SCHLUESSEL = "_2fa_user_id"
SESSION_SECRET = "_2fa_secret"


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


def anmelden(request):
    """LoginView-Ersatz: Passwort prüfen, danach ggf. TOTP abfragen."""
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        ziel = request.POST.get("next") or request.GET.get("next") or ""
        if _braucht_zwei_faktor(user):
            request.session[SESSION_SCHLUESSEL] = user.pk
            request.session["_2fa_backend"] = getattr(
                user, "backend", "django.contrib.auth.backends.ModelBackend"
            )
            request.session["_2fa_next"] = ziel
            return redirect("core:zwei_faktor")
        login(request, user)
        return redirect(ziel or "core:dashboard")

    return render(request, "registration/login.html", {"form": form})


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
    fehler = None

    if request.method == "POST":
        if device is None:
            secret = request.session.get(SESSION_SECRET) or neues_secret()
            request.session[SESSION_SECRET] = secret
            if code_pruefen(secret, request.POST.get("code", "")):
                device = TwoFactorDevice.objects.create(user=user, secret=secret, bestaetigt=True)
                request.session.pop(SESSION_SECRET, None)
            else:
                fehler = "Der Code stimmt nicht. Bitte den aktuellen Code aus der App eingeben."
        elif code_pruefen(device.secret, request.POST.get("code", "")):
            from django.utils import timezone

            device.letzte_nutzung = timezone.now()
            device.save(update_fields=["letzte_nutzung"])
        else:
            fehler = "Der Code stimmt nicht. Bitte den aktuellen Code aus der App eingeben."

        if fehler is None:
            backend = request.session.pop(
                "_2fa_backend", "django.contrib.auth.backends.ModelBackend"
            ) or "django.contrib.auth.backends.ModelBackend"
            login(request, user, backend=backend)
            request.session.pop(SESSION_SCHLUESSEL, None)
            ziel = request.session.pop("_2fa_next", "")
            messages.success(request, "Anmeldung bestätigt.")
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
            "form_fehler": fehler,
            "braucht_einrichtung": device is None,
            "secret": secret,
            "uri": otpauth_uri(secret, user.get_username()),
            "konto": user.get_username(),
        },
    )


@require_POST
@login_required
def zwei_faktor_neu(request):
    """Gerätewechsel: altes Geheimnis verwerfen und neu einrichten."""
    TwoFactorDevice.objects.filter(user=request.user).delete()
    request.session[SESSION_SCHLUESSEL] = request.user.pk
    request.session.pop(SESSION_SECRET, None)
    messages.info(request, "Bitte richten Sie das neue Gerät ein.")
    return redirect("core:zwei_faktor")
