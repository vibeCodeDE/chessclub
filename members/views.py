import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import AuditLog
from core.roles import ADMIN_GROUP, role_required

from .forms import ChangeRequestForm
from .models import ChangeRequest, Member, clean_member_value


def _parse_filters(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if status not in Member.Status.values:
        status = ""
    return query, status


def _filtered_members(query, status):
    members = Member.objects.all()
    if query:
        members = members.filter(
            Q(vorname__icontains=query)
            | Q(nachname__icontains=query)
            | Q(email__icontains=query)
            | Q(ort__icontains=query)
        )
    if status:
        members = members.filter(status=status)
    return members


@role_required(ADMIN_GROUP)
def member_list(request):
    query, status = _parse_filters(request)
    context = {
        "members": _filtered_members(query, status),
        "q": query,
        "status": status,
        "status_choices": Member.Status.choices,
    }
    return render(request, "members/member_list.html", context)


@role_required(ADMIN_GROUP)
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    context = {
        "member": member,
        "status_history": member.status_history.all(),
    }
    return render(request, "members/member_detail.html", context)


@role_required(ADMIN_GROUP)
def member_export(request):
    query, status = _parse_filters(request)
    members = _filtered_members(query, status)
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
            "Eintrittsdatum",
            "Austrittsdatum",
        ]
    )
    for member in members:
        writer.writerow(
            [
                member.nachname,
                member.vorname,
                member.geburtsdatum.isoformat() if member.geburtsdatum else "",
                member.email,
                member.telefon,
                member.strasse,
                member.plz,
                member.ort,
                member.get_status_display(),
                member.eintrittsdatum.isoformat(),
                member.austrittsdatum.isoformat() if member.austrittsdatum else "",
            ]
        )
    return response


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

    context = {
        "member": member,
        "form": form,
        "change_requests": member.change_requests.all() if member else [],
    }
    return render(request, "members/profil.html", context)


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
    context = {
        "open_requests": open_requests,
        "decided_requests": decided_requests,
        "open_count": open_requests.count(),
    }
    return render(request, "members/change_request_list.html", context)


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
        messages.error(
            request,
            "Der Wunschwert kann nicht übernommen werden: " + " ".join(exc.messages),
        )
        return redirect("members:change_request_list")

    messages.success(
        request,
        f"Änderungswunsch von {change_request.member} freigegeben und übernommen.",
    )
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
    messages.info(
        request, f"Änderungswunsch von {change_request.member} abgelehnt."
    )
    return redirect("members:change_request_list")
