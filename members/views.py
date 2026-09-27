import csv

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from core.roles import ADMIN_GROUP, role_required

from .models import Member


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
