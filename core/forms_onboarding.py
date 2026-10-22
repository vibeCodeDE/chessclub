"""Formulare für den mehrstufigen Onboarding-Assistenten (PRD S7.5, US1)."""

from django import forms

from core.models import ClubProfile, ModuleSettings
from dues.forms import FeeCategoryForm as OnboardingQuickFeeForm

__all__ = [
    "OnboardingModulesForm",
    "OnboardingProfileForm",
    "OnboardingQuickFeeForm",
]


class OnboardingProfileForm(forms.ModelForm):
    """Schritt 1: Vereinsidentität und Spielbetriebszeiten."""

    class Meta:
        model = ClubProfile
        fields = [
            "name",
            "kurzname",
            "zps_nummer",
            "kontakt_email",
            "gruendungsjahr",
            "ort",
            "spiellokal",
            "spielabend_zeiten",
            "jugend_zeiten",
            "beschreibung",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "z. B. Schachclub Königsspringer Musterstadt e.V."}),
            "kurzname": forms.TextInput(attrs={"placeholder": "z. B. SC Königsspringer"}),
            "zps_nummer": forms.TextInput(attrs={"placeholder": "z. B. C0101 (5-stellige Verbandskennziffer)", "maxlength": "10"}),
            "kontakt_email": forms.EmailInput(attrs={"placeholder": "kontakt@schachverein-musterstadt.de"}),
            "gruendungsjahr": forms.TextInput(attrs={"placeholder": "z. B. 1924"}),
            "ort": forms.TextInput(attrs={"placeholder": "z. B. Musterstadt"}),
            "spiellokal": forms.TextInput(attrs={"placeholder": "z. B. Bürgerhaus Musterstadt, Raum 3, Hauptstraße 12"}),
            "spielabend_zeiten": forms.TextInput(attrs={"placeholder": "z. B. Freitags ab 19:30 Uhr"}),
            "jugend_zeiten": forms.TextInput(attrs={"placeholder": "z. B. Freitags 17:30 - 19:00 Uhr"}),
            "beschreibung": forms.Textarea(attrs={"rows": 3, "placeholder": "Kurze Beschreibung des Vereins für die Startseite..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = True
        self.fields["kurzname"].required = True
        self.fields["kontakt_email"].required = True


class OnboardingModulesForm(forms.ModelForm):
    """Schritt 2: Auswahl aktiver Satellitenmodule."""

    class Meta:
        model = ModuleSettings
        fields = [
            "homepage_aktiv",
            "spielbetrieb_aktiv",
            "turniere_aktiv",
            "kassenbuch_aktiv",
            "nachrichten_aktiv",
        ]


