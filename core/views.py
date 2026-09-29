"""Public-Website, Dashboard, Audit-Protokoll und globale Suche."""

import csv
import json
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from cashbook.models import CashEntry, jahresabschluss
from comms.models import NewsPost
from core.dsgvo import datenauskunft, verarbeitungstaetigkeiten
from core.models import AuditLog
from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, role_of, role_required
from dues.models import MembershipFee, Payment, jahres_uebersicht
from members.models import ChangeRequest, Member
from teams.models import LeagueMatch, Team
from teams.services import tabelle
from tournaments.models import Tournament


@role_required(ADMIN_GROUP)
def dsgvo_auskunft(request, pk):
    """Druckbare Datenauskunft für ein Mitglied (PRD N1.2)."""
    member = get_object_or_404(Member, pk=pk)
    daten = datenauskunft(member)
    AuditLog.objects.create(
        benutzer=request.user,
        aktion="Datenauskunft erstellt",
        text=f"Auskunft nach Art. 15 DSGVO für Mitglied {member.pk}.",
        member=member,
    )
    return render(
        request,
        "core/dsgvo_auskunft.html",
        {"member": member, "daten": daten, "erstellt_am": timezone.now()},
    )


@role_required(ADMIN_GROUP)
def dsgvo_pdf(request, pk):
    """Vollständige Datenauskunft als PDF (PRD N1.2, ein Klick)."""
    from core.pdf import datenauskunft_pdf

    member = get_object_or_404(Member, pk=pk)
    daten = datenauskunft(member)
    AuditLog.objects.create(
        benutzer=request.user,
        aktion="Datenauskunft erstellt",
        text=f"Datenauskunft als PDF (Art. 15 DSGVO) für Mitglied {member.pk}.",
        member=member,
    )
    antwort = HttpResponse(datenauskunft_pdf(member, daten), content_type="application/pdf")
    antwort["Content-Disposition"] = (
        f'attachment; filename="datenauskunft-{member.pk}-{timezone.localdate():%Y-%m-%d}.pdf"'
    )
    return antwort


@role_required(ADMIN_GROUP)
def dsgvo_export(request, pk):
    """Maschinenlesbare Auskunft (JSON) zum Herunterladen (PRD N1.2/N1.4)."""
    member = get_object_or_404(Member, pk=pk)
    daten = datenauskunft(member)
    AuditLog.objects.create(
        benutzer=request.user,
        aktion="Datenauskunft erstellt",
        text=f"Datenauskunft als JSON (Art. 15 DSGVO) für Mitglied {member.pk}.",
        member=member,
    )
    inhalt = json.dumps(
        {"mitglied_id": member.pk, "erstellt_am": timezone.now().isoformat(), "daten": daten},
        ensure_ascii=False,
        indent=2,
        default=str,
    )
    antwort = HttpResponse(inhalt, content_type="application/json; charset=utf-8")
    antwort["Content-Disposition"] = (
        f'attachment; filename="datenauskunft-{member.pk}.json"'
    )
    return antwort


@role_required(ADMIN_GROUP)
def dsgvo_verzeichnis(request):
    """Verzeichnis der Verarbeitungstätigkeiten als CSV (PRD N1.4)."""
    antwort = HttpResponse(content_type="text/csv; charset=utf-8")
    antwort["Content-Disposition"] = 'attachment; filename="verzeichnis-verarbeitungstaetigkeiten.csv"'
    antwort.write("\ufeff")
    writer = csv.writer(antwort, delimiter=";")
    writer.writerow(["Kategorie", "Zweck", "Datenfelder", "Rechtsgrundlage", "Speicherfrist"])
    for zeile in verarbeitungstaetigkeiten():
        writer.writerow(
            [zeile["kategorie"], zeile["zweck"], zeile["felder"], zeile["rechtsgrundlage"], zeile["speicherfrist"]]
        )
    return antwort


def service_worker(request):
    """Liefert den Service Worker unter /sw.js aus (Wurzel-Scope für die PWA)."""
    datei = settings.BASE_DIR / "static" / "sw.js"
    antwort = HttpResponse(datei.read_text(encoding="utf-8"), content_type="application/javascript; charset=utf-8")
    antwort["Service-Worker-Allowed"] = "/"
    antwort["Cache-Control"] = "no-cache"
    return antwort


def offline(request):
    """Offline-Fallback für die PWA (wird vom Service Worker gecacht)."""
    return render(request, "core/offline.html")


def health(request):
    """Health-Check für Deployment/Monitoring."""
    from django.http import JsonResponse

    return JsonResponse({"status": "ok"})


def home(request):
    """Öffentliche Startseite: News, Termine, Beitrittsinfo (PRD §2)."""
    heute = timezone.localdate()
    news = NewsPost.objects.filter(veroeffentlicht=True)[:6]
    turniere = (
        Tournament.objects.filter(oeffentlich=True, datum__gte=heute)
        .order_by("datum")[:5]
    )
    spiele = (
        LeagueMatch.objects.filter(datum__gte=heute, status__in=["geplant", "aufgestellt"])
        .select_related("team")
        .order_by("datum")[:5]
    )
    kontext = {
        "news": news,
        "turniere": turniere,
        "spiele": spiele,
        "mitglieder_aktiv": Member.objects.filter(status=Member.Status.AKTIV).count(),
        "mannschaften": Team.objects.filter(aktiv=True).count(),
        "naechstes_turnier": turniere[0] if turniere else None,
    }
    return render(request, "core/home.html", kontext)


def news_archiv(request):
    news = NewsPost.objects.filter(veroeffentlicht=True)
    return render(request, "core/news_archiv.html", {"news": news})


def news_detail(request, pk):
    neuigkeit = NewsPost.objects.filter(pk=pk, veroeffentlicht=True).first()
    if neuigkeit is None:
        from django.http import Http404

        raise Http404("Ankündigung nicht gefunden")
    weitere = NewsPost.objects.filter(veroeffentlicht=True).exclude(pk=pk)[:3]
    return render(request, "core/news_detail.html", {"post": neuigkeit, "weitere": weitere})


@login_required
def dashboard(request):
    """Rollenabhängige Übersicht (PRD M7.1)."""
    rolle = role_of(request.user)
    heute = timezone.localdate()
    jahr = heute.year

    if rolle in {ADMIN_GROUP, KAPITAEN_GROUP}:
        return _dashboard_vorstand(request, rolle, heute, jahr)
    return _dashboard_mitglied(request, heute)


def _dashboard_vorstand(request, rolle, heute, jahr):
    uebersicht = jahres_uebersicht(jahr)
    faellige = (
        MembershipFee.objects.filter(jahr=jahr)
        .select_related("member")
        .order_by("member__nachname")[:200]
    )
    offene_posten = [fee for fee in faellige if fee.ist_offen][:6]
    offene_wuensche = ChangeRequest.objects.filter(
        status=ChangeRequest.Status.EINGEREICHT
    ).select_related("member")[:5]
    kommende_spiele = (
        LeagueMatch.objects.filter(datum__gte=heute)
        .select_related("team")
        .order_by("datum", "uhrzeit")[:5]
    )
    kommende_turniere = Tournament.objects.filter(datum__gte=heute).order_by("datum")[:4]
    kasse = jahresabschluss(jahr)
    neue_mitglieder = Member.objects.filter(
        eintrittsdatum__gte=heute - timedelta(days=180)
    ).order_by("-eintrittsdatum")[:5]
    letzte_aktivitaeten = AuditLog.objects.select_related("benutzer", "member")[:8]
    mitglieder_gesamt = Member.objects.exclude(status=Member.Status.AUSGETRETEN).count()
    aktive = Member.objects.filter(status=Member.Status.AKTIV).count()
    passiv = Member.objects.filter(status=Member.Status.PASSIV).count()
    ohne_kategorie = Member.objects.filter(
        status=Member.Status.AKTIV, beitragskategorie__isnull=True
    ).count()

    monat_start = heute.replace(day=1)
    zahlungen_monat = Payment.objects.filter(datum__gte=monat_start).aggregate(
        s=Sum("betrag")
    )["s"] or Decimal("0.00")

    # Kleine Verlaufsreihe fürs Beitrags-Aufkommen (letzte 6 Monate)
    verlauf = []
    for i in range(5, -1, -1):
        monat = (heute.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        s = Payment.objects.filter(
            datum__year=monat.year, datum__month=monat.month
        ).aggregate(s=Sum("betrag"))["s"] or Decimal("0.00")
        verlauf.append({"label": monat.strftime("%b"), "wert": float(s)})
    max_wert = max([punkt["wert"] for punkt in verlauf] + [1.0])
    for punkt in verlauf:
        punkt["prozent"] = round(punkt["wert"] / max_wert * 100)

    kontext = {
        "rolle": rolle,
        "jahr": jahr,
        "uebersicht": uebersicht,
        "offene_posten": offene_posten,
        "offene_wuensche": offene_wuensche,
        "kommende_spiele": kommende_spiele,
        "kommende_turniere": kommende_turniere,
        "kasse": kasse,
        "neue_mitglieder": neue_mitglieder,
        "letzte_aktivitaeten": letzte_aktivitaeten,
        "mitglieder_gesamt": mitglieder_gesamt,
        "aktive_mitglieder": aktive,
        "passive_mitglieder": passiv,
        "ohne_kategorie": ohne_kategorie,
        "zahlungen_monat": zahlungen_monat,
        "verlauf": verlauf,
        "heute": heute,
    }
    return render(request, "core/dashboard.html", kontext)


def _dashboard_mitglied(request, heute):
    member = Member.objects.filter(user=request.user).first()
    posten = []
    if member:
        posten = (
            MembershipFee.objects.filter(member=member)
            .select_related("member")
            .order_by("-jahr")
        )
    kontext = {
        "member": member,
        "posten": posten,
        "offen": [fee for fee in posten if fee.ist_offen],
        "wuensche": member.change_requests.all()[:5] if member else [],
        "news": NewsPost.objects.filter(veroeffentlicht=True)[:4],
        "kommende_spiele": LeagueMatch.objects.filter(datum__gte=heute)
        .select_related("team")
        .order_by("datum")[:4],
        "kommende_turniere": Tournament.objects.filter(datum__gte=heute, oeffentlich=True)[:4],
        "meine_aufstellungen": member.lineups.select_related("match", "match__team")[:5]
        if member
        else [],
    }
    return render(request, "core/dashboard_mitglied.html", kontext)


@role_required(ADMIN_GROUP)
def audit_list(request):
    """Audit-Protokoll: wer hat wann was geändert (PRD M7.3)."""
    protokoll = AuditLog.objects.select_related("benutzer", "member")
    aktion = request.GET.get("aktion", "").strip()
    if aktion:
        protokoll = protokoll.filter(aktion=aktion)
    benutzer_id = request.GET.get("benutzer", "").strip()
    if benutzer_id.isdigit():
        protokoll = protokoll.filter(benutzer_id=benutzer_id)
    aktionen = (
        AuditLog.objects.values_list("aktion", flat=True).distinct().order_by("aktion")
    )
    from core.ui import paginate

    kontext = {
        "protokoll": paginate(protokoll, request, per_page=40),
        "aktion": aktion,
        "aktionen": aktionen,
        "benutzer_id": benutzer_id,
    }
    return render(request, "core/audit_list.html", kontext)


@login_required
def suche(request):
    """Globale Suche über Mitglieder, Turniere und News."""
    begriff = request.GET.get("q", "").strip()
    ergebnisse = {"mitglieder": [], "turniere": [], "news": []}
    if begriff:
        ergebnisse["mitglieder"] = Member.objects.filter(
            Q(vorname__icontains=begriff) | Q(nachname__icontains=begriff) | Q(email__icontains=begriff)
        )[:10]
        ergebnisse["turniere"] = Tournament.objects.filter(name__icontains=begriff)[:10]
        ergebnisse["news"] = NewsPost.objects.filter(titel__icontains=begriff)[:10]
    return render(
        request,
        "core/suche.html",
        {"begriff": begriff, "ergebnisse": ergebnisse, "treffer": sum(len(v) for v in ergebnisse.values())},
    )
