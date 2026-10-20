"""Public-Website, Dashboard, Audit-Protokoll und globale Suche."""

import csv
import json
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from cashbook.models import jahresabschluss
from comms.models import NewsPost
from core import produkt
from core.dsgvo import datenauskunft, verarbeitungstaetigkeiten
from core.models import AuditLog
from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, role_of, role_required
from core.services import is_marketing_site, is_module_active
from core.ui import sanitize_csv
from dues.models import MembershipFee, Payment, jahres_uebersicht
from members.models import ChangeRequest, Member
from teams.models import LeagueMatch, Team
from tournaments.models import Tournament


@login_required
def dsgvo_auskunft(request, pk):
    """Druckbare Datenauskunft für ein Mitglied (PRD N1.2, Berechtigungsmatrix §3.8)."""
    member = get_object_or_404(Member, pk=pk)
    rolle = role_of(request.user)
    if rolle != ADMIN_GROUP and member.user != request.user:
        raise PermissionDenied
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


@login_required
def dsgvo_pdf(request, pk):
    """Vollständige Datenauskunft als PDF (PRD N1.2, Berechtigungsmatrix §3.8)."""
    from core.pdf import datenauskunft_pdf

    member = get_object_or_404(Member, pk=pk)
    rolle = role_of(request.user)
    if rolle != ADMIN_GROUP and member.user != request.user:
        raise PermissionDenied
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


@login_required
def dsgvo_export(request, pk):
    """Maschinenlesbare Auskunft (JSON) zum Herunterladen (PRD N1.2/N1.4, Berechtigungsmatrix §3.8)."""
    member = get_object_or_404(Member, pk=pk)
    rolle = role_of(request.user)
    if rolle != ADMIN_GROUP and member.user != request.user:
        raise PermissionDenied
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
            [
                sanitize_csv(zeile["kategorie"]),
                sanitize_csv(zeile["zweck"]),
                sanitize_csv(zeile["felder"]),
                sanitize_csv(zeile["rechtsgrundlage"]),
                sanitize_csv(zeile["speicherfrist"]),
            ]
        )
    return antwort


def service_worker(request):
    """Liefert den Service Worker unter /sw.js aus (Wurzel-Scope für die PWA)."""
    pwa_aktiv = getattr(settings, "PWA_AKTIV", False)
    if not pwa_aktiv:
        # PWA temporär deaktiviert: Service Worker deregistrieren und Caches leeren
        inhalt = (
            "/* PWA temporaer deaktiviert: Service Worker deregistrieren und Caches leeren */\n"
            "self.addEventListener('install', (e) => self.skipWaiting());\n"
            "self.addEventListener('activate', (e) => {\n"
            "  e.waitUntil(\n"
            "    caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))))\n"
            "      .then(() => self.registration.unregister())\n"
            "      .then(() => self.clients.matchAll())\n"
            "      .then((clients) => {\n"
            "        clients.forEach((c) => c.navigate(c.url));\n"
            "      })\n"
            "  );\n"
            "});\n"
        )
        antwort = HttpResponse(inhalt, content_type="application/javascript; charset=utf-8")
        antwort["Service-Worker-Allowed"] = "/"
        antwort["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return antwort

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
    """Startseite: Entweder Produkt-Landingpage (auf Marketing-Domain/Einstellung)
    oder öffentliche Vereinsseite bzw. Redirect zum internen Dashboard (ADR-023, ADR-024)."""
    if is_marketing_site(request):
        return produkt_seite(request)

    if not is_module_active("homepage", request):
        if request.user.is_authenticated:
            return redirect("core:dashboard")
        return redirect("core:login")

    heute = timezone.localdate()
    has_comms = is_module_active("comms", request)
    has_tournaments = is_module_active("tournaments", request)
    has_teams = is_module_active("teams", request)

    news = NewsPost.objects.filter(veroeffentlicht=True)[:6] if has_comms else []
    turniere = (
        list(Tournament.objects.filter(oeffentlich=True, datum__gte=heute).order_by("datum")[:5])
        if has_tournaments
        else []
    )
    spiele = (
        list(
            LeagueMatch.objects.filter(datum__gte=heute, status__in=["geplant", "aufgestellt"])
            .select_related("team")
            .order_by("datum")[:5]
        )
        if has_teams
        else []
    )
    letzte_spiele = (
        list(
            LeagueMatch.objects.filter(datum__lt=heute, status="gespielt")
            .select_related("team")
            .order_by("-datum", "-uhrzeit")[:3]
        )
        if has_teams
        else []
    )
    feed_token = None
    if has_teams:
        from teams.models import LeagueCalendarFeed

        feed_token = LeagueCalendarFeed.get_token()

    kontext = {
        "news": news,
        "turniere": turniere,
        "spiele": spiele,
        "letzte_spiele": letzte_spiele,
        "ical_token": feed_token,
        "mitglieder_aktiv": Member.objects.filter(status=Member.Status.AKTIV).count(),
        "mannschaften": Team.objects.filter(aktiv=True).count() if has_teams else 0,
        "naechstes_turnier": turniere[0] if turniere else None,
        # Zähler für die Übersichtsleiste: alle anstehenden Termine, nicht nur
        # die auf der Seite gezeigten fünf.
        "turniere_anzahl": (
            Tournament.objects.filter(oeffentlich=True, datum__gte=heute).count()
            if has_tournaments
            else 0
        ),
        "spiele_anzahl": (
            LeagueMatch.objects.filter(
                datum__gte=heute, status__in=["geplant", "aufgestellt"]
            ).count()
            if has_teams
            else 0
        ),
        "jahre_tradition": _jahre_seit_gruendung(heute),
    }
    return render(request, "core/home.html", kontext)


def _jahre_seit_gruendung(heute):
    """Jahre seit der Gründung – nur wenn `CLUB_FOUNDED` gepflegt ist."""
    gegruendet = (settings.CLUB_FOUNDED or "").strip()
    if not gegruendet.isdigit():
        return None
    jahre = heute.year - int(gegruendet)
    return jahre if jahre > 0 else None


def verein(request):
    """Öffentliche Vereinsseite: Selbstverständnis, Zeiten, Spielplan (PRD S2.2)."""
    heute = timezone.localdate()
    has_teams = is_module_active("teams", request)
    spiele = []
    letzte_spiele = []
    mannschaften = []
    ligen_tabellen = {}
    feed_token = None

    if has_teams:
        spiele = (
            LeagueMatch.objects.filter(datum__gte=heute)
            .select_related("team")
            .order_by("datum", "uhrzeit")[:8]
        )
        letzte_spiele = (
            LeagueMatch.objects.filter(datum__lt=heute, status="gespielt")
            .select_related("team")
            .order_by("-datum", "-uhrzeit")[:4]
        )
        mannschaften = (
            Team.objects.filter(aktiv=True)
            .select_related("kapitaen")
            .prefetch_related("matches")
        )

        from teams.services import tabelle

        for team in mannschaften:
            if team.liga and team.liga not in ligen_tabellen:
                tab = tabelle(team.liga)
                if tab:
                    ligen_tabellen[team.liga] = tab

        from teams.models import LeagueCalendarFeed

        feed_token = LeagueCalendarFeed.get_token()

    kontext = {
        "spiele": spiele,
        "letzte_spiele": letzte_spiele,
        "mannschaften": mannschaften,
        "ligen_tabellen": ligen_tabellen,
        "ical_token": feed_token,
        "mitglieder_aktiv": Member.objects.filter(status=Member.Status.AKTIV).count(),
        "jahre_tradition": _jahre_seit_gruendung(heute),
        "heute": heute,
    }
    return render(request, "core/verein.html", kontext)


def produkt_seite(request):
    """Marketing-Landingpage für den Verkauf der Software an andere Vereine."""
    kontext = {
        "product_name": settings.PRODUCT_NAME,
        "product_contact": settings.PRODUCT_CONTACT,
        "preisstufen": produkt.PREISSTUFEN,
        "preishinweis": produkt.PREISHINWEIS,
        "funktionen": produkt.FUNKTIONEN,
        "datenschutz_punkte": produkt.DATENSCHUTZ_PUNKTE,
        "schritte": produkt.SCHRITTE,
        "faq": produkt.FAQ,
        "rollen_schmerzpunkte": produkt.ROLLEN_SCHMERZPUNKTE,
    }
    return render(request, "core/produkt.html", kontext)


def produkt_redirect(request):
    """Permanenter 301-Redirect von /produkt/ zur Startseite / (ADR-024)."""
    return redirect("core:home", permanent=True)


def rechtliches(request, seite):
    """Platzhalter für Impressum und Datenschutzerklärung der Produktseite."""
    titel = {"impressum": "Impressum", "datenschutz": "Datenschutzerklärung"}[seite]
    return render(
        request,
        "core/rechtliches.html",
        {
            "product_name": settings.PRODUCT_NAME,
            "product_contact": settings.PRODUCT_CONTACT,
            "seite": seite,
            "titel": titel,
        },
    )


def news_archiv(request):
    """Öffentliches Archiv der Ankündigungen, filterbar nach Kategorie (PRD M5.1)."""
    news = NewsPost.objects.filter(veroeffentlicht=True)
    kategorien = list(
        NewsPost.objects.filter(veroeffentlicht=True)
        .exclude(kategorie="")
        .values_list("kategorie", flat=True)
        .distinct()
        .order_by("kategorie")
    )
    aktiv = (request.GET.get("kategorie") or "").strip()
    if aktiv and aktiv not in kategorien:
        aktiv = ""
    if aktiv:
        news = news.filter(kategorie=aktiv)
    return render(
        request,
        "core/news_archiv.html",
        {"news": news, "kategorien": kategorien, "aktiv": aktiv},
    )


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
    jahr_param = request.GET.get("jahr", "").strip()
    jahr = int(jahr_param) if jahr_param.isdigit() else heute.year

    if rolle in {ADMIN_GROUP, KAPITAEN_GROUP}:
        return _dashboard_vorstand(request, rolle, heute, jahr)
    return _dashboard_mitglied(request, heute)


def _dashboard_vorstand(request, rolle, heute, jahr):
    # PRD §3.8: Beiträge, Zahlungen, Mahnungen, Kassenbuch, Mitgliederliste und
    # Audit-Log sind Vorstandssache. Für den Kapitän werden diese Daten gar
    # erst nicht geladen – ein ausgeblendetes Kachel-Label ist kein Schutz.
    has_teams = is_module_active("teams", request)
    has_tournaments = is_module_active("tournaments", request)
    has_cashbook = is_module_active("cashbook", request)

    kommende_spiele = (
        list(
            LeagueMatch.objects.filter(datum__gte=heute)
            .select_related("team")
            .order_by("datum", "uhrzeit")[:5]
        )
        if has_teams
        else []
    )
    kommende_turniere = (
        list(Tournament.objects.filter(datum__gte=heute).order_by("datum")[:4])
        if has_tournaments
        else []
    )

    verfuegbare_jahre = sorted(
        set(MembershipFee.objects.values_list("jahr", flat=True)) | {heute.year},
        reverse=True,
    )

    kontext = {
        "rolle": rolle,
        "jahr": jahr,
        "verfuegbare_jahre": verfuegbare_jahre,
        "kommende_spiele": kommende_spiele,
        "kommende_turniere": kommende_turniere,
        "heute": heute,
    }

    if rolle != ADMIN_GROUP:
        kontext["eigene_mannschaften"] = (
            Team.objects.filter(kapitaen__user=request.user, aktiv=True).select_related("kapitaen")
            if has_teams
            else []
        )
        kontext["offene_aufgaben"] = (
            _kapitaen_aufgaben(request.user, heute) if has_teams else []
        )
        return render(request, "core/dashboard.html", kontext)

    uebersicht = jahres_uebersicht(jahr)
    offene_posten = list(
        MembershipFee.objects.filter(
            jahr=jahr,
            status__in=[MembershipFee.Status.OFFEN, MembershipFee.Status.TEILWEISE],
        )
        .select_related("member")
        .prefetch_related("zahlungen")
        .order_by("member__nachname", "member__vorname")[:6]
    )
    offene_wuensche = ChangeRequest.objects.filter(
        status=ChangeRequest.Status.EINGEREICHT
    ).select_related("member")[:5]
    kasse = jahresabschluss(jahr) if has_cashbook else None
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

    # Optimierte Verlaufsreihe fürs Beitrags-Aufkommen (letzte 6 Monate in 1 Query)
    monat_start_verlauf = (heute.replace(day=1) - timedelta(days=160)).replace(day=1)
    monatssummen = {
        (e["datum__year"], e["datum__month"]): e["s"]
        for e in Payment.objects.filter(datum__gte=monat_start_verlauf)
        .values("datum__year", "datum__month")
        .annotate(s=Sum("betrag"))
    }
    verlauf = []
    for i in range(5, -1, -1):
        monat = (heute.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        s = monatssummen.get((monat.year, monat.month), Decimal("0.00"))
        verlauf.append({"label": monat.strftime("%b"), "wert": float(s)})
    max_wert = max([punkt["wert"] for punkt in verlauf] + [1.0])
    for punkt in verlauf:
        punkt["prozent"] = round(punkt["wert"] / max_wert * 100)

    kontext.update(
        {
            "uebersicht": uebersicht,
            "offene_posten": offene_posten,
            "offene_wuensche": offene_wuensche,
            "kasse": kasse,
            "neue_mitglieder": neue_mitglieder,
            "letzte_aktivitaeten": letzte_aktivitaeten,
            "mitglieder_gesamt": mitglieder_gesamt,
            "aktive_mitglieder": aktive,
            "passive_mitglieder": passiv,
            "ohne_kategorie": ohne_kategorie,
            "zahlungen_monat": zahlungen_monat,
            "verlauf": verlauf,
            "onboarding_widget": (
                from_services_onboarding_widget := __import__(
                    "core.services", fromlist=["get_onboarding_checklist_status"]
                ).get_onboarding_checklist_status(user=request.user)
            )
            if rolle == ADMIN_GROUP
            else None,
        }
    )
    return render(request, "core/dashboard.html", kontext)


def _kapitaen_aufgaben(benutzer, heute):
    """Eigene Aufgaben des Kapitäns: Aufstellungen und Ergebnisse (PRD M4.3/M4.4)."""
    eigene_mannschaften = Team.objects.filter(kapitaen__user=benutzer).values_list(
        "pk", flat=True
    )
    return (
        LeagueMatch.objects.filter(team__in=eigene_mannschaften)
        .filter(status=LeagueMatch.Status.GEPLANT, datum__gte=heute)
        .select_related("team")
        .order_by("datum", "uhrzeit")[:6]
    )


def _dashboard_mitglied(request, heute):
    has_teams = is_module_active("teams", request)
    has_tournaments = is_module_active("tournaments", request)
    has_comms = is_module_active("comms", request)

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
        "news": NewsPost.objects.filter(veroeffentlicht=True)[:4] if has_comms else [],
        "kommende_spiele": (
            list(
                LeagueMatch.objects.filter(datum__gte=heute)
                .select_related("team")
                .order_by("datum")[:4]
            )
            if has_teams
            else []
        ),
        "kommende_turniere": (
            list(Tournament.objects.filter(datum__gte=heute, oeffentlich=True)[:4])
            if has_tournaments
            else []
        ),
        "meine_aufstellungen": (
            list(member.lineups.select_related("match", "match__team")[:5])
            if (member and has_teams)
            else []
        ),
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
    suche = request.GET.get("q", "").strip()
    if suche:
        protokoll = protokoll.filter(
            Q(text__icontains=suche)
            | Q(member__nachname__icontains=suche)
            | Q(member__vorname__icontains=suche)
            | Q(feld__icontains=suche)
            | Q(alt_wert__icontains=suche)
            | Q(neu_wert__icontains=suche)
        )
    aktionen = (
        AuditLog.objects.values_list("aktion", flat=True).distinct().order_by("aktion")
    )
    from core.ui import paginate

    kontext = {
        "protokoll": paginate(protokoll, request, per_page=40),
        "aktion": aktion,
        "aktionen": aktionen,
        "benutzer_id": benutzer_id,
        "q": suche,
    }
    return render(request, "core/audit_list.html", kontext)


@login_required
def suche(request):
    """Globale Suche über Mitglieder, Turniere und News."""
    begriff = request.GET.get("q", "").strip()
    rolle = role_of(request.user)
    ergebnisse = {"mitglieder": [], "turniere": [], "news": []}
    if begriff:
        # Berechtigungsmatrix §3.8: Mitgliederliste (alle) ist Vorstandssache
        if rolle == ADMIN_GROUP:
            ergebnisse["mitglieder"] = Member.objects.filter(
                Q(vorname__icontains=begriff) | Q(nachname__icontains=begriff) | Q(email__icontains=begriff)
            )[:10]
        # Turniere: Nicht-Admins sehen nur öffentliche Turniere
        if is_module_active("tournaments", request):
            turnier_qs = (
                Tournament.objects.all()
                if rolle == ADMIN_GROUP
                else Tournament.objects.filter(oeffentlich=True)
            )
            ergebnisse["turniere"] = turnier_qs.filter(name__icontains=begriff)[:10]
        # News: Nicht-Admins sehen nur veröffentlichte News
        if is_module_active("comms", request):
            news_qs = (
                NewsPost.objects.all()
                if rolle == ADMIN_GROUP
                else NewsPost.objects.filter(veroeffentlicht=True)
            )
            ergebnisse["news"] = news_qs.filter(titel__icontains=begriff)[:10]
    return render(
        request,
        "core/suche.html",
        {"begriff": begriff, "ergebnisse": ergebnisse, "treffer": sum(len(v) for v in ergebnisse.values()), "user_role": rolle},
    )


def ratelimited_view(request, exception=None):
    """Fehleransicht bei Überschreitung des Rate-Limits (HTTP 429, PRD N1.1, N1.6, ADR-028)."""
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("accept", ""):
        from django.http import JsonResponse

        response = JsonResponse(
            {"detail": "Zu viele Anfragen. Bitte versuchen Sie es in wenigen Minuten erneut."},
            status=429,
        )
    else:
        response = render(
            request,
            "core/ratelimited.html",
            {
                "club_name": getattr(settings, "CLUB_NAME", "Schachverein"),
                "club_short": getattr(settings, "CLUB_SHORT", "Schach"),
                "club_contact": getattr(settings, "CLUB_CONTACT", "vorstand@example.org"),
            },
            status=429,
        )
    response["Retry-After"] = "60"
    return response

