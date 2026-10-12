"""Formulare für den Einrichtungs- und Onboarding-Bereich (PRD S7.5, ADR-020)."""

from django import forms

from core.models import ClubProfile
from dues.forms import FeeCategoryForm as QuickFeeCategoryForm
from dues.models import FeeCategory
from teams.models import Team


class ClubProfileForm(forms.ModelForm):
    class Meta:
        model = ClubProfile
        fields = [
            "name",
            "kurzname",
            "kontakt_email",
            "gruendungsjahr",
            "ort",
            "spiellokal",
            "spielabend_zeiten",
            "jugend_zeiten",
            "beschreibung",
            "sepa_glaeubiger_id",
            "sepa_glaeubiger_name",
            "sepa_iban",
            "sepa_bic",
        ]
        widgets = {
            "beschreibung": forms.Textarea(attrs={"rows": 3}),
            "spiellokal": forms.TextInput(attrs={"placeholder": "z. B. Bürgerhaus Musterstadt, Vereinsraum 2"}),
            "spielabend_zeiten": forms.TextInput(attrs={"placeholder": "z. B. Donnerstags ab 19:00 Uhr"}),
            "jugend_zeiten": forms.TextInput(attrs={"placeholder": "z. B. Donnerstags 17:30 – 19:00 Uhr"}),
            "sepa_glaeubiger_id": forms.TextInput(attrs={"placeholder": "z. B. DE98ZZZ09999999999"}),
            "sepa_iban": forms.TextInput(attrs={"placeholder": "z. B. DE89 3704 0044 0532 0130 00"}),
        }


class MemberCsvUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV-Datei mit Mitgliedsdaten",
        help_text="Erlaubt sind UTF-8 oder Latin-1 kodierte Dateien mit Trennzeichen Semikolon (;) oder Komma (,).",
    )
    aktion = forms.ChoiceField(
        choices=[("pruefen", "Prüfen & Vorschau"), ("importieren", "Jetzt verbindlich importieren")],
        initial="pruefen",
        widget=forms.HiddenInput(),
        required=False,
    )


class QuickTeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "liga", "altersklasse", "brettanzahl", "aktiv"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "z. B. 1. Mannschaft"}),
            "liga": forms.TextInput(attrs={"placeholder": "z. B. Bezirksliga Staffel Süd"}),
        }
