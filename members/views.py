import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import AuditLog
from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, role_required
from core.ui import fehler, is_ajax, ok, paginate
from dues.models import FeeCategory, MembershipFee, Payment

from .forms import ChangeRequestForm, MemberForm, MemberStatusForm, TrialInquiryForm
from .models import ChangeRequest, Member, clean_member_value


def _parse_filters(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if status not in Member.Status.values:
        status = ""
    kategorie = request.GET.get("kategorie", "")
    return query, status, kategorie


def _filtered_members(query, status, kategorie=""):
    members = Member.objects.select_related("beitragskategorie")
    if query:
        members = members.filter(
            Q(vorname__icontains=query)
            | Q(nachname__icontains=query)
            | Q(email__icontains=query)
            | Q(ort__icontains=query)
        )
    if status:
        members = members.filter(status=status)
    if kategorie == "keine":
        members = members.filter(beitragskategorie__isnull=True)
    elif kategorie.isdigit():
        members = members.filter(beitragskategorie_id=int(kategorie))
    return members


@role_required(ADMIN_GROUP)
def member_list(request):
    query, status, kategorie = _parse_filters(request)
    members = _filtered_members(query, status, kategorie)
    kontext = {
        "members": members,
        "page_obj": paginate(members, request, per_page=25),
        "q": query,
        "status": status,
        "status_choices": Member.Status.choices,
        "kategorie": kategorie,
        "kategorien": FeeCategory.objects.all(),
        "gesamt": Member.objects.count(),
        "aktiv_count": Member.objects.filter(status=Member.Status.AKTIV).count(),
        "passiv_count": Member.objects.filter(status=Member.Status.PASSIV).count(),
        "ausgetreten_count": Member.objects.filter(status=Member.Status.AUSGETRETEN).count(),
        "ohne_kategorie_count": Member.objects.filter(
            status=Member.Status.AKTIV, beitragskategorie__isnull=True
        ).count(),
        "status_form": MemberStatusForm(),
    }
    return render(request, "members/member_list.html", kontext)


@role_required(ADMIN_GROUP)
def member_detail(request, pk):
    member = get_object_or_404(
        Member.objects.select_related("beitragskategorie"), pk=pk
    )
    AuditLog.objects.create(
        benutzer=request.user,
        aktion="Mitgliedsakte eingesehen",
        text=f"Stammdaten und Akte von {member} aufgerufen.",
        member=member,
    )
    posten = (
        MembershipFee.objects.filter(member=member)
        .prefetch_related("zahlungen")
        .order_by("-jahr")
    )
    kontext = {
        "member": member,
        "status_history": member.status_history.select_related("geaendert_von"),
        "posten": posten,
        "offene_posten": [fee for fee in posten if fee.ist_offen],
        "bezahlt_summe": Payment.objects.filter(fee__member=member).aggregate(
            s=Sum("betrag")
        )["s"],
        "mandat": getattr(member, "sepa_mandat", None),
        "aufstellungen": member.lineups.select_related("match", "match__team").order_by(
            "-match__datum"
        )[:10],
        "wuensche": member.change_requests.select_related("eingereicht_von")[:8],
        "protokoll": AuditLog.objects.filter(member=member).select_related("benutzer")[:25],
        "turniere": member.turnierteilnahmen.select_related("tournament").order_by(
            "-tournament__datum"
        )[:8],
    }
    return render(request, "members/member_detail.html", kontext)


@role_required(ADMIN_GROUP)
def member_create(request):
    if request.method == "POST":
        form = MemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member._changed_by = request.user
            member.save()
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Mitglied angelegt",
                text=f"{member} neu aufgenommen",
                member=member,
            )
            if is_ajax(request):
                return ok(
                    message=f"{member} wurde angelegt.",
                    redirect=f"/mitglieder/{member.pk}/",
                )
            messages.success(request, f"{member} wurde angelegt.")
            return redirect("members:member_detail", pk=member.pk)
        if is_ajax(request):
            return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    else:
        form = MemberForm(initial={"eintrittsdatum": timezone.localdate()})
    return render(
        request,
        "members/member_form.html",
        {"form": form, "titel": "Mitglied aufnehmen", "member": None},
    )


@role_required(ADMIN_GROUP)
def member_update(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            objekt = form.save(commit=False)
            objekt._changed_by = request.user
            objekt.save()
            if is_ajax(request):
                return ok(message=f"Änderungen an {objekt} gespeichert.")
            messages.success(request, f"Änderungen an {objekt} gespeichert.")
            return redirect("members:member_detail", pk=member.pk)
        if is_ajax(request):
            return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    else:
        form = MemberForm(instance=member)
    return render(
        request,
        "members/member_form.html",
        {"form": form, "titel": f"{member} bearbeiten", "member": member},
    )


@role_required(ADMIN_GROUP)
@require_POST
def member_delete(request, pk):
    """Kein Hard-Delete (PRD M1.3): Mitglied wird auf „ausgetreten“ gesetzt."""
    member = get_object_or_404(Member, pk=pk)
    if member.status == Member.Status.AUSGETRETEN:
        messages.info(request, f"{member} ist bereits ausgetreten.")
        return redirect("members:member_detail", pk=member.pk)
    member._changed_by = request.user
    member.status = Member.Status.AUSGETRETEN
    member.austrittsdatum = member.austrittsdatum or timezone.localdate()
    member.save()
    AuditLog.objects.create(
        benutzer=request.user,
        aktion="Austritt erfasst",
        text=f"{member} ausgetreten zum {member.austrittsdatum:%d.%m.%Y}",
        member=member,
    )
    messages.success(
        request,
        f"{member} wurde als ausgetreten markiert – die Daten bleiben für die Fristen erhalten.",
    )
    return redirect("members:member_detail", pk=member.pk)


@role_required(ADMIN_GROUP, KAPITAEN_GROUP)
@require_POST
def member_status(request, pk):
    """Optimistischer Statuswechsel aus der Mitgliederliste."""
    member = get_object_or_404(Member, pk=pk)
    form = MemberStatusForm(request.POST)
    if not form.is_valid():
        return fehler("Statuswechsel nicht möglich.", errors=form.errors)
    neuer_status = form.cleaned_data["status"]
    member._changed_by = request.user
    member.status = neuer_status
    if neuer_status == Member.Status.AUSGETRETEN:
        member.austrittsdatum = form.cleaned_data["austrittsdatum"] or timezone.localdate()
    else:
        member.austrittsdatum = None
    try:
        member.full_clean(exclude=["user"])
    except ValidationError as exc:
        return fehler(" ".join(exc.messages))
    member.save()
    return ok(
        message=f"{member}: Status auf „{member.get_status_display()}“ gesetzt.",
        patch={f"[data-status-text='{member.pk}']": member.get_status_display()},
        classes={
            f"[data-status-badge='{member.pk}']": {
                "add": [f"badge-{member.status}"],
                "remove": [f"badge-{wert}" for wert in Member.Status.values],
            }
        },
    )


@role_required(ADMIN_GROUP)
def member_export(request):
    query, status, kategorie = _parse_filters(request)
    members = _filtered_members(query, status, kategorie)
    AuditLog.objects.create(
        benutzer=request.user,
        aktion="Mitgliederliste exportiert",
        text=f"CSV-Export der Mitgliederliste ({members.count()} Einträge).",
    )
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="mitglieder.csv"'
    response.write("\ufeff")  # BOM für Excel
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        [
            "Nachname",
            "Vorname",
            "Geburtsdatum",
            "E-Mail",
            "Telefon",
            "Straße",
            "PLZ",
            "Ort",
            "Status",
            "Beitragskategorie",
            "Eintrittsdatum",
            "Austrittsdatum",
        ]
    )
    for member in members:
        writer.writerow(
            [
                member.nachname,
                member.vorname,
                member.geburtsdatum.strftime("%d.%m.%Y") if member.geburtsdatum else "",
                member.email,
                member.telefon,
                member.strasse,
                member.plz,
                member.ort,
                member.get_status_display(),
                member.beitragskategorie.name if member.beitragskategorie else "",
                member.eintrittsdatum.strftime("%d.%m.%Y"),
                member.austrittsdatum.strftime("%d.%m.%Y") if member.austrittsdatum else "",
            ]
        )
    return response


def join_info(request):
    """Öffentliche Beitrittsinfo mit Beitragssätzen und Schnupper-Anfrage (PRD M1.6)."""
    kategorien = FeeCategory.objects.filter(aktiv=True)
    if request.method == "POST":
        form = TrialInquiryForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            interesse = dict(TrialInquiryForm.INTERESSE_CHOICES).get(
                form.cleaned_data["interesse"], ""
            )
            nachricht = form.cleaned_data.get("nachricht", "")
            subject = f"Neue Schnupper-Anfrage: {name} ({interesse})"
            body = (
                f"Name: {name}\nE-Mail: {email}\nInteresse: {interesse}\n\n"
                f"Nachricht:\n{nachricht}"
            )
            from django.conf import settings
            from django.core.mail import send_mail

            contact = getattr(settings, "CLUB_CONTACT", "vorstand@example.org")
            send_mail(subject, body, contact, [contact], fail_silently=True)
            messages.success(
                request,
                "Vielen Dank! Wir haben deine Schnupper-Anfrage erhalten und melden uns in Kürze per E-Mail bei dir.",
            )
            return redirect("members:join_info")
        else:
            messages.error(request, "Bitte überprüfe deine Eingaben im Formular.")
    else:
        form = TrialInquiryForm()

    return render(
        request,
        "members/join_info.html",
        {
            "kategorien": kategorien,
            "form": form,
            "aktive_mitglieder": Member.objects.filter(status=Member.Status.AKTIV).count(),
        },
    )


@login_required
def profil(request):
    """Selbstbedienung: eigene Daten ansehen, Änderungswunsch einreichen (PRD M1.4)."""
    member = Member.objects.filter(user=request.user).first()

    if request.method == "POST":
        form = ChangeRequestForm(request.POST, member=member)
        if member is None:
            messages.error(
                request, "Für dieses Konto ist kein Mitgliedsprofil hinterlegt."
            )
        elif form.is_valid():
            ChangeRequest.objects.create(
                member=member,
                feld=form.cleaned_data["feld"],
                wunschwert=form.cleaned_data["wunschwert"],
                eingereicht_von=request.user,
            )
            messages.success(
                request,
                "Änderungswunsch eingereicht – die Vorstandschaft prüft ihn.",
            )
            return redirect("members:profil")
    else:
        form = ChangeRequestForm(member=member)

    kontext = {
        "member": member,
        "form": form,
        "change_requests": member.change_requests.all() if member else [],
        "posten": (
            MembershipFee.objects.filter(member=member).prefetch_related("zahlungen").order_by("-jahr")
            if member
            else []
        ),
        "mandat": getattr(member, "sepa_mandat", None) if member else None,
        "aufstellungen": (
            member.lineups.select_related("match", "match__team").order_by("-match__datum")[:6]
            if member
            else []
        ),
    }
    return render(request, "members/profil.html", kontext)


@role_required(ADMIN_GROUP)
def change_request_list(request):
    open_requests = (
        ChangeRequest.objects.filter(status=ChangeRequest.Status.EINGEREICHT)
        .select_related("member", "eingereicht_von")
        .order_by("eingereicht_am")
    )
    decided_requests = (
        ChangeRequest.objects.exclude(status=ChangeRequest.Status.EINGEREICHT)
        .select_related("member", "eingereicht_von", "entschieden_von")
        .order_by("-eingereicht_am")
    )
    kontext = {
        "open_requests": open_requests,
        "decided_requests": decided_requests,
        "open_count": open_requests.count(),
    }
    return render(request, "members/change_request_list.html", kontext)


def _finish_decision(request, change_request, status, aktion, text):
    change_request.status = status
    change_request.entschieden_von = request.user
    change_request.entschieden_am = timezone.now()
    change_request.save()
    AuditLog.objects.create(
        benutzer=request.user,
        aktion=aktion,
        text=text,
        member=change_request.member,
    )


@role_required(ADMIN_GROUP)
@require_POST
def change_request_approve(request, pk):
    # Atomar: Zeilensperre, Wertübertrag, Entscheidung und Audit-Log
    # entstehen nur zusammen oder gar nicht.
    try:
        with transaction.atomic():
            change_request = get_object_or_404(
                ChangeRequest.objects.select_for_update(),
                pk=pk,
                status=ChangeRequest.Status.EINGEREICHT,
            )
            member = change_request.member
            value = clean_member_value(
                change_request.feld, change_request.wunschwert
            )
            label = change_request.get_feld_display()
            old_value = str(getattr(member, change_request.feld) or "")
            member._changed_by = request.user
            setattr(member, change_request.feld, value)
            member.save()

            _finish_decision(
                request,
                change_request,
                ChangeRequest.Status.FREIGEGEBEN,
                "Änderungswunsch freigegeben",
                f"{member}: {label}: „{old_value}“ → „{value}“",
            )
    except ValidationError as exc:
        nachricht = (
            "Der Wunschwert kann nicht übernommen werden: " + " ".join(exc.messages)
        )
        if is_ajax(request):
            return fehler(nachricht)
        messages.error(request, nachricht)
        return redirect("members:change_request_list")

    nachricht = f"Änderungswunsch von {change_request.member} freigegeben und übernommen."
    if is_ajax(request):
        return ok(message=nachricht, remove_selector=f"[data-row='wunsch-{pk}']")
    messages.success(request, nachricht)
    return redirect("members:change_request_list")


@role_required(ADMIN_GROUP)
@require_POST
def change_request_reject(request, pk):
    with transaction.atomic():
        change_request = get_object_or_404(
            ChangeRequest.objects.select_for_update(),
            pk=pk,
            status=ChangeRequest.Status.EINGEREICHT,
        )
        change_request.kommentar = request.POST.get("kommentar", "").strip()[:500]

        _finish_decision(
            request,
            change_request,
            ChangeRequest.Status.ABGELEHNT,
            "Änderungswunsch abgelehnt",
            f"{change_request.member}: {change_request.get_feld_display()} → "
            f"„{change_request.wunschwert}“ (keine Übernahme)",
        )
    nachricht = f"Änderungswunsch von {change_request.member} abgelehnt."
    if is_ajax(request):
        return ok(message=nachricht, remove_selector=f"[data-row='wunsch-{pk}']")
    messages.info(request, nachricht)
    return redirect("members:change_request_list")
