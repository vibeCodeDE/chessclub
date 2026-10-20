import csv
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from core.models import AuditLog
from core.roles import ADMIN_GROUP, role_required
from core.ui import fehler, is_ajax, ok, paginate, sanitize_csv
from dues.models import FeeCategory, MembershipFee, Payment
from teams.models import LineupEntry
from teams.services import escape_ical
from tournaments.models import Tournament

from .forms import ChangeRequestForm, MemberForm, MemberStatusForm, TrialInquiryForm
from .models import ChangeRequest, Member, clean_member_value

def get_personal_calendar_token(member):
    if not member.ical_token:
        member.renew_ical_token()
    return member.ical_token


def _parse_filters(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if status not in Member.Status.values:
        status = ""
    kategorie = request.GET.get("kategorie", "")
    filter_type = request.GET.get("filter", "").strip()
    return query, status, kategorie, filter_type


def _filtered_members(query, status, kategorie="", filter_type=""):
    members = Member.objects.select_related("beitragskategorie")
    heute = timezone.localdate()
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

    if filter_type == "u18":
        u18_cutoff = date(heute.year - 18, heute.month, heute.day)
        members = members.filter(geburtsdatum__gt=u18_cutoff, status=Member.Status.AKTIV)
    elif filter_type == "senioren":
        senioren_cutoff = date(heute.year - 60, heute.month, heute.day)
        members = members.filter(geburtsdatum__lte=senioren_cutoff, status=Member.Status.AKTIV)
    elif filter_type == "ohne_kategorie":
        members = members.filter(beitragskategorie__isnull=True, status=Member.Status.AKTIV)
    elif filter_type == "ohne_mandat":
        members = members.filter(status=Member.Status.AKTIV).exclude(sepa_mandat__status="aktiv")

    return members


@role_required(ADMIN_GROUP)
def member_list(request):
    query, status, kategorie, filter_type = _parse_filters(request)
    members = _filtered_members(query, status, kategorie, filter_type)
    heute = timezone.localdate()
    u18_cutoff = date(heute.year - 18, heute.month, heute.day)
    senioren_cutoff = date(heute.year - 60, heute.month, heute.day)

    smart_counts = {
        "gesamt": Member.objects.count(),
        "aktiv": Member.objects.filter(status=Member.Status.AKTIV).count(),
        "u18": Member.objects.filter(status=Member.Status.AKTIV, geburtsdatum__gt=u18_cutoff).count(),
        "senioren": Member.objects.filter(status=Member.Status.AKTIV, geburtsdatum__lte=senioren_cutoff).count(),
        "ohne_kategorie": Member.objects.filter(
            status=Member.Status.AKTIV, beitragskategorie__isnull=True
        ).count(),
        "ohne_mandat": Member.objects.filter(status=Member.Status.AKTIV).exclude(sepa_mandat__status="aktiv").count(),
    }

    kontext = {
        "members": members,
        "mitglieder": members,
        "page_obj": paginate(members, request, per_page=25),
        "q": query,
        "status": status,
        "status_choices": Member.Status.choices,
        "kategorie": kategorie,
        "kategorien": FeeCategory.objects.all(),
        "filter_type": filter_type,
        "smart_counts": smart_counts,
        "gesamt": smart_counts["gesamt"],
        "aktiv_count": smart_counts["aktiv"],
        "passiv_count": Member.objects.filter(status=Member.Status.PASSIV).count(),
        "ausgetreten_count": Member.objects.filter(status=Member.Status.AUSGETRETEN).count(),
        "ohne_kategorie_count": smart_counts["ohne_kategorie"],
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


@role_required(ADMIN_GROUP)
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
    query, status, kategorie, filter_type = _parse_filters(request)
    members = _filtered_members(query, status, kategorie, filter_type)
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
                sanitize_csv(member.nachname),
                sanitize_csv(member.vorname),
                member.geburtsdatum.strftime("%d.%m.%Y") if member.geburtsdatum else "",
                sanitize_csv(member.email),
                sanitize_csv(member.telefon),
                sanitize_csv(member.strasse),
                sanitize_csv(member.plz),
                sanitize_csv(member.ort),
                sanitize_csv(member.get_status_display()),
                sanitize_csv(member.beitragskategorie.name if member.beitragskategorie else ""),
                member.eintrittsdatum.strftime("%d.%m.%Y"),
                member.austrittsdatum.strftime("%d.%m.%Y") if member.austrittsdatum else "",
            ]
        )
    return response


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
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
        "calendar_url": request.build_absolute_uri(
            reverse("members:personal_calendar", kwargs={"token": get_personal_calendar_token(member)})
        ) if member else None,
        "has_2fa": hasattr(request.user, "zwei_faktor"),
        "is_admin": request.user.groups.filter(name=ADMIN_GROUP).exists(),
    }
    return render(request, "members/profil.html", kontext)


@login_required
@require_POST
def renew_personal_calendar_token(request):
    """Erneuert das persönliche Kalender-Token eines Mitglieds (DSGVO Access Revocation)."""
    member = Member.objects.filter(user=request.user).first()
    if not member:
        messages.error(request, "Für dieses Konto ist kein Mitgliedsprofil hinterlegt.")
        return redirect("members:profil")
    member.renew_ical_token()
    AuditLog.objects.create(
        benutzer=request.user,
        aktion="Kalender-Token erneuert",
        text=f"Persönlicher Kalender-Token für Mitglied {member} wurde erneuert.",
        member=member,
    )
    messages.success(
        request, "Persönlicher Kalender-Token wurde erneuert. Alte Abonnements sind ungültig."
    )
    return redirect("members:profil")


def personal_calendar_feed(request, token):
    """Abonnierbarer iCal-Feed für die persönlichen Einsätze eines Mitglieds (Hebel F4)."""
    member = get_object_or_404(Member, ical_token=token)
    if member.status == Member.Status.AUSGETRETEN:
        raise Http404("Kalender-Abonnement für ausgetretene Mitglieder nicht mehr aktiv.")
    heute = timezone.localdate()
    start_datum = heute - timedelta(days=60)

    # Persönliche Einsätze in Ligaspielen
    lineups = (
        LineupEntry.objects.filter(member=member, match__datum__gte=start_datum)
        .select_related("match", "match__team")
        .order_by("match__datum", "match__uhrzeit")
    )
    # Öffentliche Vereinsturniere
    tournaments = Tournament.objects.filter(
        datum__gte=start_datum, oeffentlich=True
    ).order_by("datum")

    verein = getattr(settings, "CLUB_NAME", "Schachverein")
    now_utc = timezone.now().strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{escape_ical(verein)}//PersoenlicherKalender//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ical(f'{member.vorname} {member.nachname}')} – Mein Schachkalender",
        "X-WR-TIMEZONE:Europe/Berlin",
    ]

    for entry in lineups:
        m = entry.match
        uid = f"pers-match-{m.pk}-{member.pk}@{getattr(settings, 'CLUB_SHORT', 'schach')}.local"
        summary = f"Ligaspiel: {m.team.name} vs. {m.gegner} (Brett {entry.brett})"
        desc = f"{member.vorname} {member.nachname} aufgestellt an Brett {entry.brett}. {m.get_status_display()}. Spielort: {m.ort or 'offen'}."
        if m.uhrzeit:
            start_dt = datetime.combine(m.datum, m.uhrzeit)
            end_dt = start_dt + timedelta(hours=4)
            dtstart = f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}"
            dtend = f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}"
        else:
            dtstart = f"DTSTART;VALUE=DATE:{m.datum.strftime('%Y%m%d')}"
            dtend = f"DTEND;VALUE=DATE:{m.datum.strftime('%Y%m%d')}"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            dtstart,
            dtend,
            f"SUMMARY:{escape_ical(summary)}",
            f"DESCRIPTION:{escape_ical(desc)}",
            f"LOCATION:{escape_ical(m.ort or '')}",
            "END:VEVENT",
        ])

    for t in tournaments:
        uid = f"pers-turnier-{t.pk}@{getattr(settings, 'CLUB_SHORT', 'schach')}.local"
        summary = f"Turnier: {t.name}"
        desc = f"{t.get_format_display()} mit {t.runden_anzahl} Runden. Ort: {t.ort or 'Vereinsheim'}."
        dtstart = f"DTSTART;VALUE=DATE:{t.datum.strftime('%Y%m%d')}"
        dtend = f"DTEND;VALUE=DATE:{t.datum.strftime('%Y%m%d')}"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            dtstart,
            dtend,
            f"SUMMARY:{escape_ical(summary)}",
            f"DESCRIPTION:{escape_ical(desc)}",
            f"LOCATION:{escape_ical(t.ort or 'Vereinsheim')}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return HttpResponse("\r\n".join(lines), content_type="text/calendar; charset=utf-8")



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


@role_required(ADMIN_GROUP)
def dsb_sync_view(request):
    """Verbandsabgleich mit dem DSB-Wertungsportal und Drift Detection (ADR-016 / K3.6)."""
    from django.conf import settings

    from members.services.dsb_sync import (
        DSBSyncError,
        detect_drift,
        fetch_dsb_vereinsliste,
        sync_dwz_for_member,
        sync_dwz_from_report,
    )

    vkz = getattr(settings, "DSB_VKZ", "").strip()
    token = getattr(settings, "DSB_API_TOKEN", "").strip()
    config_ok = bool(vkz and token)
    dsb_data = None
    from_cache = False
    error_message = None

    if request.method == "POST":
        action = request.POST.get("action", "")

        if not config_ok:
            messages.error(
                request,
                "DSB-Schnittstelle ist noch nicht konfiguriert (DSB_VKZ oder DSB_API_TOKEN fehlt).",
            )
            return redirect("members:dsb_sync")

        try:
            if action == "refresh":
                dsb_data, from_cache = fetch_dsb_vereinsliste(force=True)
                AuditLog.objects.create(
                    benutzer=request.user,
                    aktion="DSB-Daten aktualisiert",
                    text=f"Frische Verbandsdaten vom DSB-Wertungsportal abgerufen (VKZ: {vkz}).",
                )
                messages.success(request, "Verbandsdaten erfolgreich vom DSB-Portal aktualisiert.")
                return redirect("members:dsb_sync")

            elif action == "sync_all":
                dsb_data, from_cache = fetch_dsb_vereinsliste()
                report = detect_drift(dsb_data=dsb_data, from_cache=from_cache)
                count = sync_dwz_from_report(report, benutzer=request.user)
                messages.success(
                    request,
                    (
                        f"DWZ und Verbandskennungen für {count} Mitglied(er) erfolgreich übernommen."
                        if count > 0
                        else "Alle DWZ-Werte sind bereits aktuell."
                    ),
                )
                return redirect("members:dsb_sync")

            elif action == "sync_member":
                member_id = request.POST.get("member_id")
                member = get_object_or_404(Member, pk=member_id)
                dsb_data, from_cache = fetch_dsb_vereinsliste()
                report = detect_drift(dsb_data=dsb_data, from_cache=from_cache)
                target_drift = next(
                    (item for item in report.dwz_abweichungen if item["member"].id == member.id),
                    None,
                )
                if target_drift:
                    sync_dwz_for_member(member, target_drift["dsb_player"], benutzer=request.user)
                    AuditLog.objects.create(
                        benutzer=request.user,
                        aktion="DSB-Abgleich durchgeführt",
                        text=f"DWZ für {member} übernommen: {member.dwz_formatiert}.",
                        member=member,
                    )
                    messages.success(
                        request,
                        f"DWZ für {member} erfolgreich übernommen ({member.dwz_formatiert}).",
                    )
                else:
                    messages.info(request, f"Keine DWZ-Abweichung für {member} gefunden.")
                return redirect("members:dsb_sync")

        except DSBSyncError as exc:
            messages.error(request, f"Fehler beim DSB-Abgleich: {exc}")
            return redirect("members:dsb_sync")

    if config_ok:
        try:
            dsb_data, from_cache = fetch_dsb_vereinsliste()
        except DSBSyncError as exc:
            error_message = str(exc)

    report = detect_drift(dsb_data=dsb_data, from_cache=from_cache)

    context = {
        "report": report,
        "config_ok": config_ok,
        "vkz": vkz,
        "error_message": error_message,
    }
    return render(request, "members/dsb_sync.html", context)

