"""Ankündigungen und Gruppen-E-Mails (PRD M5.1/M5.2)."""

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.roles import ADMIN_GROUP, role_required
from core.ui import fehler, is_ajax, ok

from .forms import MailForm, NewsForm
from .models import MailLog, NewsPost
from .services import empfaenger_und_uebersprungene, sende_gruppenmail


@role_required(ADMIN_GROUP)
def news_list(request):
    posts = NewsPost.objects.select_related("autor")
    status = request.GET.get("status", "")
    if status == "entwurf":
        posts = posts.filter(veroeffentlicht=False)
    elif status == "veroeffentlicht":
        posts = posts.filter(veroeffentlicht=True)
    kontext = {
        "posts": posts,
        "status": status,
        "anzahl_entwuerfe": NewsPost.objects.filter(veroeffentlicht=False).count(),
        "anzahl_veroeffentlicht": NewsPost.objects.filter(veroeffentlicht=True).count(),
    }
    return render(request, "comms/news_list.html", kontext)


@role_required(ADMIN_GROUP)
def news_create(request):
    if request.method == "POST":
        form = NewsForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.autor = request.user
            if post.veroeffentlicht:
                from django.utils import timezone

                post.veroeffentlicht_am = timezone.now()
            post.save()
            if is_ajax(request):
                return ok(message=f"„{post.titel}“ gespeichert.", redirect="/ankuendigungen/")
            messages.success(request, f"„{post.titel}“ gespeichert.")
            return redirect("comms:news_list")
        if is_ajax(request):
            return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    else:
        form = NewsForm(initial={"kategorie": "Verein"})
    return render(request, "comms/news_form.html", {"form": form, "post": None})


@role_required(ADMIN_GROUP)
def news_update(request, pk):
    post = get_object_or_404(NewsPost, pk=pk)
    if request.method == "POST":
        form = NewsForm(request.POST, instance=post)
        if form.is_valid():
            objekt = form.save(commit=False)
            if objekt.veroeffentlicht and not objekt.veroeffentlicht_am:
                from django.utils import timezone

                objekt.veroeffentlicht_am = timezone.now()
            objekt.save()
            if is_ajax(request):
                return ok(message=f"„{objekt.titel}“ aktualisiert.", redirect="/ankuendigungen/")
            messages.success(request, f"„{objekt.titel}“ aktualisiert.")
            return redirect("comms:news_list")
        if is_ajax(request):
            return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    else:
        form = NewsForm(instance=post)
    return render(request, "comms/news_form.html", {"form": form, "post": post})


@role_required(ADMIN_GROUP)
@require_POST
def news_delete(request, pk):
    post = get_object_or_404(NewsPost, pk=pk)
    titel = post.titel
    post.delete()
    return ok(message=f"„{titel}“ gelöscht.", remove_selector=f"[data-row='news-{pk}']")


@role_required(ADMIN_GROUP)
@require_POST
def news_toggle(request, pk):
    """Veröffentlichen oder zurückziehen – optimistisch im UI."""
    post = get_object_or_404(NewsPost, pk=pk)
    if post.veroeffentlicht:
        post.zurueckziehen()
        nachricht = f"„{post.titel}“ ist jetzt wieder Entwurf."
    else:
        post.veroeffentlichen()
        nachricht = f"„{post.titel}“ ist jetzt öffentlich sichtbar."
    return ok(
        message=nachricht,
        checked=post.veroeffentlicht,
        patch={
            f"[data-news-status='{post.pk}']": "Veröffentlicht" if post.veroeffentlicht else "Entwurf",
            "[data-entwurf-count]": str(NewsPost.objects.filter(veroeffentlicht=False).count()),
        },
        classes={
            f"[data-news-badge='{post.pk}']": {
                "add": ["badge-veroeffentlicht" if post.veroeffentlicht else "badge-entwurf"],
                "remove": ["badge-veroeffentlicht", "badge-entwurf"],
            }
        },
    )


@role_required(ADMIN_GROUP)
def mail_list(request):
    """Versandformular + Protokoll der letzten Sendungen (PRD M5.2)."""
    if request.method == "POST":
        form = MailForm(request.POST)
        if form.is_valid():
            log = sende_gruppenmail(
                betreff=form.cleaned_data["betreff"],
                text=form.cleaned_data["text"],
                zielgruppe=form.cleaned_data["zielgruppe"],
                benutzer=request.user,
                test_empfaenger=form.cleaned_data["test_empfaenger"],
            )
            hinweis = (
                f"Testversand an {log.anzahl_empfaenger} Adresse(n) durchgeführt."
                if log.status == MailLog.Status.TEST
                else f"{log.anzahl_empfaenger} E-Mail(s) versendet – "
                f"{log.anzahl_uebersprungen} ohne Opt-in übersprungen."
            )
            if is_ajax(request):
                return ok(message=hinweis, reload=True)
            messages.success(request, hinweis)
            return redirect("comms:mail_list")
        if is_ajax(request):
            return fehler("Bitte Eingaben prüfen.", errors=form.errors)
    else:
        form = MailForm()

    adressen, uebersprungen = empfaenger_und_uebersprungene(form["zielgruppe"].value() or MailLog.Zielgruppe.AKTIV)
    kontext = {
        "form": form,
        "logs": MailLog.objects.select_related("erstellt_von")[:25],
        "empfaenger_anzahl": len(adressen),
        "uebersprungen_anzahl": uebersprungen,
        "demo_modus": settings.EMAIL_BACKEND.endswith("console.EmailBackend"),
    }
    return render(request, "comms/mail_list.html", kontext)
