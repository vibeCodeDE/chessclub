"""Views für den zentralen Einrichtungs- und Onboarding-Bereich (PRD S7.5, ADR-020)."""

import csv

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

from core.forms_setup import (
    MAX_MEMBER_CSV_SIZE_BYTES,
    MAX_MEMBER_CSV_SIZE_MB,
    ClubProfileForm,
    MemberCsvUploadForm,
    QuickFeeCategoryForm,
    QuickTeamForm,
)
from core.models import AuditLog, ClubProfile
from core.roles import ADMIN_GROUP, role_required
from dues.models import FeeCategory
from members.services.import_service import (
    execute_members_import,
    parse_members_csv,
    validate_members_import,
)
from teams.models import Team


@role_required(ADMIN_GROUP)
def club_setup_profile(request):
    """Verwaltung der zentralen Vereinsstammdaten und SEPA-Gläubigerdaten (ADR-020)."""
    profil = ClubProfile.get_solo()

    if request.method == "POST":
        form = ClubProfileForm(request.POST, instance=profil)
        if form.is_valid():
            form.save()
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Vereinsprofil aktualisiert",
                text=f"Stammdaten für '{profil.name or 'Verein'}' wurden aktualisiert.",
            )
            messages.success(request, "Vereinsstammdaten erfolgreich gespeichert.")
            return redirect("core:club_setup_profile")
        else:
            messages.error(request, "Bitte Eingaben im Formular überprüfen.")
    else:
        form = ClubProfileForm(instance=profil)

    kontext = {
        "profil": profil,
        "form": form,
        "aktiver_reiter": "profil",
    }
    return render(request, "core/setup_profile.html", kontext)


@role_required(ADMIN_GROUP)
def club_setup_dues(request):
    """Schnellverwaltung der Beitragskategorien für das Vereins-Setup."""
    kategorien = FeeCategory.objects.all().order_by("name")

    if request.method == "POST":
        form = QuickFeeCategoryForm(request.POST)
        if form.is_valid():
            kat = form.save()
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Beitragskategorie angelegt",
                text=f"Kategorie '{kat.name}' ({kat.betrag} €) im Vereins-Setup angelegt.",
            )
            messages.success(request, f"Beitragskategorie „{kat.name}“ erfolgreich angelegt.")
            return redirect("core:club_setup_dues")
        else:
            messages.error(request, "Bitte Eingaben der Beitragskategorie prüfen.")
    else:
        form = QuickFeeCategoryForm()

    kontext = {
        "kategorien": kategorien,
        "form": form,
        "aktiver_reiter": "beitraege",
    }
    return render(request, "core/setup_dues.html", kontext)


@role_required(ADMIN_GROUP)
def club_setup_teams(request):
    """Schnellverwaltung der Mannschaften und Ligen für das Vereins-Setup."""
    teams = Team.objects.all().order_by("name")

    if request.method == "POST":
        form = QuickTeamForm(request.POST)
        if form.is_valid():
            team = form.save()
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Mannschaft angelegt",
                text=f"Mannschaft '{team.name}' im Vereins-Setup angelegt.",
            )
            messages.success(request, f"Mannschaft „{team.name}“ erfolgreich angelegt.")
            return redirect("core:club_setup_teams")
        else:
            messages.error(request, "Bitte Eingaben der Mannschaft prüfen.")
    else:
        form = QuickTeamForm()

    kontext = {
        "teams": teams,
        "form": form,
        "aktiver_reiter": "mannschaften",
    }
    return render(request, "core/setup_teams.html", kontext)


@role_required(ADMIN_GROUP)
def club_setup_members_import(request):
    """Geführter CSV-Import für echte Mitgliederdaten mit Vorschau und Validierung."""
    validation_results = None

    if request.method == "POST":
        aktion = request.POST.get("aktion", "pruefen")

        if aktion == "bestaetigen":
            csv_text = request.session.get("pending_import_csv", "")
            if not csv_text:
                messages.error(request, "Keine offenen Importdaten in der Sitzung gefunden. Bitte Datei erneut hochladen.")
                return redirect("core:club_setup_members_import")

            if len(csv_text.encode("utf-8")) > MAX_MEMBER_CSV_SIZE_BYTES:
                request.session.pop("pending_import_csv", None)
                messages.error(request, f"Die Importdaten überschreiten das Limit von {MAX_MEMBER_CSV_SIZE_MB} MB.")
                return redirect("core:club_setup_members_import")

            rows = parse_members_csv(csv_text)
            validation = validate_members_import(rows)
            if validation["valid_count"] == 0:
                messages.error(request, "Keine gültigen Datensätze zum Importieren vorhanden.")
                return redirect("core:club_setup_members_import")

            ergebnis = execute_members_import(validation["valid_rows"], actor=request.user)
            request.session.pop("pending_import_csv", None)
            messages.success(
                request,
                f"Import erfolgreich abgeschlossen: {ergebnis['created_members']} Mitglieder "
                f"und {ergebnis['created_mandates']} SEPA-Mandate angelegt.",
            )
            return redirect("members:member_list")

        form = MemberCsvUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["csv_file"]
            csv_raw = uploaded_file.read()
            rows = parse_members_csv(csv_raw)

            if not rows:
                messages.error(request, "Die hochgeladene Datei enthält keine lesbaren Datenzeilen.")
            else:
                validation_results = validate_members_import(rows)

                # CSV für Schritt 2 (Bestätigung) in Session merken
                if hasattr(csv_raw, "decode"):
                    try:
                        request.session["pending_import_csv"] = csv_raw.decode("utf-8")
                    except UnicodeDecodeError:
                        request.session["pending_import_csv"] = csv_raw.decode("latin-1", errors="replace")
                else:
                    request.session["pending_import_csv"] = str(csv_raw)

                if aktion == "importieren":
                    if validation_results["valid_count"] == 0:
                        messages.error(request, "Keine gültigen Datensätze zum Importieren vorhanden.")
                    else:
                        ergebnis = execute_members_import(
                            validation_results["valid_rows"],
                            actor=request.user,
                        )
                        request.session.pop("pending_import_csv", None)
                        messages.success(
                            request,
                            f"Import erfolgreich abgeschlossen: {ergebnis['created_members']} Mitglieder "
                            f"und {ergebnis['created_mandates']} SEPA-Mandate angelegt.",
                        )
                        return redirect("members:member_list")
        else:
            first_err = form.errors.get("csv_file")
            if first_err:
                messages.error(request, first_err[0])
            else:
                messages.error(request, "Bitte eine gültige CSV-Datei auswählen.")
    else:
        form = MemberCsvUploadForm()

    kontext = {
        "form": form,
        "validation": validation_results,
        "aktiver_reiter": "import",
    }
    return render(request, "core/setup_members_import.html", kontext)


@role_required(ADMIN_GROUP)
def club_setup_import_muster(request):
    """Bietet eine standardisierte Vorlage-CSV zum Download an."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="mitglieder_vorlage.csv"'

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Vorname",
        "Nachname",
        "E-Mail",
        "Telefon",
        "Geburtsdatum",
        "Strasse",
        "PLZ",
        "Ort",
        "Eintrittsdatum",
        "Status",
        "Beitragskategorie",
        "IBAN",
        "Kontoinhaber",
        "DWZ",
        "DWZ-Index",
        "FIDE-ID",
        "ZPS-Nummer",
    ])
    writer.writerow([
        "Max",
        "Mustermann",
        "max.mustermann@example.de",
        "0171 1234567",
        "15.03.1985",
        "Hauptstraße 12",
        "37073",
        "Göttingen",
        "01.01.2024",
        "aktiv",
        "Erwachsene",
        "DE89370400440532013000",
        "Max Mustermann",
        "1850",
        "42",
        "12345678",
        "C0101-042",
    ])
    writer.writerow([
        "Anna",
        "Schachner",
        "anna.schachner@example.de",
        "",
        "22.11.2008",
        "Bahnhofsweg 4",
        "37075",
        "Göttingen",
        "01.09.2025",
        "aktiv",
        "Jugendliche",
        "",
        "",
        "1420",
        "12",
        "",
        "",
    ])
    return response
