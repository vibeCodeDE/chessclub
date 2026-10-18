from django import forms

from members.forms import StyledFormMixin

from .models import Participant, Tournament


class TournamentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Tournament
        fields = [
            "name",
            "saison",
            "datum",
            "anmeldeschluss",
            "ort",
            "format",
            "runden_anzahl",
            "startgeld",
            "status",
            "oeffentlich",
            "beschreibung",
        ]
        widgets = {
            "datum": forms.DateInput(format="%Y-%m-%d"),
            "anmeldeschluss": forms.DateInput(format="%Y-%m-%d"),
            "beschreibung": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from teams.models import Season
        self.fields["saison"].queryset = Season.objects.all().order_by("-startdatum")
        self.fields["saison"].required = False
        self.fields["saison"].empty_label = "– Ohne Saison / Unabhängig –"
        if not (self.instance and self.instance.pk):
            aktive = Season.get_aktive_saison()
            if aktive and not self.initial.get("saison"):
                self.fields["saison"].initial = aktive
        self._style()


class ParticipantForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Participant
        fields = ["member", "name", "verein", "twz", "geburtsjahr", "email", "startgeld_bezahlt", "notiz"]

    def __init__(self, *args, tournament=None, **kwargs):
        super().__init__(*args, **kwargs)
        from members.models import Member

        self.fields["member"].queryset = Member.objects.exclude(status=Member.Status.AUSGETRETEN)
        self.fields["member"].required = False
        self.fields["member"].empty_label = "– Gast / kein Mitglied –"
        self.fields["name"].help_text = "Bei Gästen bitte Vor- und Nachnamen angeben."
        self.tournament = tournament
        self._style()

    def clean(self):
        cleaned = super().clean()
        member = cleaned.get("member")
        name = (cleaned.get("name") or "").strip()
        if member and not name:
            cleaned["name"] = f"{member.vorname} {member.nachname}"
        if not cleaned.get("name"):
            self.add_error("name", "Bitte einen Namen angeben.")
        if self.tournament and cleaned.get("name"):
            doppelt = self.tournament.teilnehmer.filter(name__iexact=cleaned["name"])
            if self.instance.pk:
                doppelt = doppelt.exclude(pk=self.instance.pk)
            if doppelt.exists():
                self.add_error("name", "Diese Person ist bereits angemeldet.")
        return cleaned


class PublicRegistrationForm(StyledFormMixin, forms.ModelForm):
    """Gastanmeldung ohne Konto (PRD M3.2)."""

    class Meta:
        model = Participant
        fields = ["name", "verein", "twz", "geburtsjahr", "email"]

    def __init__(self, *args, tournament=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tournament = tournament
        self.fields["name"].label = "Vor- und Nachname"
        self.fields["verein"].label = "Verein (optional)"
        self.fields["twz"].label = "DWZ / TWZ (falls vorhanden)"
        self.fields["geburtsjahr"].label = "Geburtsjahr (optional)"
        self._style()

    def clean_name(self):
        """Doppelte Anmeldungen verhindern (DB-Constraint plus freundliche Meldung)."""
        name = (self.cleaned_data.get("name") or "").strip()
        if name and self.tournament:
            bereits = self.tournament.teilnehmer.filter(name__iexact=name).exists()
            if bereits:
                raise forms.ValidationError("Für dieses Turnier ist dieser Name bereits angemeldet.")
        return name
