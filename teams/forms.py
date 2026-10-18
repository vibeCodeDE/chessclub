from django import forms

from members.forms import StyledFormMixin
from members.models import Member

from .models import LeagueMatch, LineupEntry, Season, Team


class SeasonForm(StyledFormMixin, forms.ModelForm):
    als_aktiv_setzen = forms.BooleanField(
        required=False,
        label="Als aktive Hauptsaison festlegen",
        help_text="Wird nach dem Speichern als aktuelle Spielzeit im gesamten Verein verwendet.",
    )

    class Meta:
        model = Season
        fields = ["name", "startdatum", "enddatum", "status", "notizen"]
        widgets = {
            "startdatum": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "enddatum": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "notizen": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["als_aktiv_setzen"].initial = self.instance.ist_aktiv
        self._style()

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("startdatum")
        end = cleaned_data.get("enddatum")
        if start and end and start >= end:
            self.add_error("enddatum", "Das Enddatum muss nach dem Startdatum liegen.")
        return cleaned_data


class SeasonRolloverForm(forms.Form):
    """Dynamisches Formular zur Übernahme von Mannschaften aus der Vorsaison."""

    def __init__(self, *args, source_season=None, target_season=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_season = source_season
        self.target_season = target_season
        mitglieder = Member.objects.exclude(status=Member.Status.AUSGETRETEN)

        if source_season:
            for team in source_season.teams.filter(aktiv=True).order_by("name"):
                prefix = f"team_{team.pk}"
                self.fields[f"{prefix}_uebernehmen"] = forms.BooleanField(
                    required=False,
                    initial=True,
                    label=f"{team.name} übernehmen",
                )
                self.fields[f"{prefix}_liga"] = forms.CharField(
                    required=False,
                    initial=team.liga,
                    label="Liga / Staffel",
                    widget=forms.TextInput(attrs={"class": "input", "placeholder": "z. B. Verbandsliga"}),
                )
                self.fields[f"{prefix}_brettanzahl"] = forms.IntegerField(
                    required=False,
                    initial=team.brettanzahl,
                    min_value=1,
                    max_value=20,
                    label="Bretter",
                    widget=forms.NumberInput(attrs={"class": "input"}),
                )
                self.fields[f"{prefix}_kapitaen"] = forms.ModelChoiceField(
                    queryset=mitglieder,
                    required=False,
                    initial=team.kapitaen_id,
                    label="Mannschaftsführer:in",
                    empty_label="– kein/e –",
                    widget=forms.Select(attrs={"class": "input"}),
                )

    @property
    def team_rows(self):
        rows = []
        if self.source_season:
            for team in self.source_season.teams.filter(aktiv=True).order_by("name"):
                prefix = f"team_{team.pk}"
                rows.append({
                    "team": team,
                    "uebernehmen": self[f"{prefix}_uebernehmen"],
                    "liga": self[f"{prefix}_liga"],
                    "brettanzahl": self[f"{prefix}_brettanzahl"],
                    "kapitaen": self[f"{prefix}_kapitaen"],
                })
        return rows


class TeamForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "saison", "liga", "altersklasse", "brettanzahl", "kapitaen", "aktiv"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kapitaen"].queryset = Member.objects.exclude(status=Member.Status.AUSGETRETEN)
        self.fields["kapitaen"].help_text = "Darf die Aufstellung pflegen."
        self.fields["saison"].queryset = Season.objects.all().order_by("-startdatum")
        aktive = Season.get_aktive_saison()
        if aktive and not self.initial.get("saison") and not (self.instance and self.instance.pk and self.instance.saison_id):
            self.fields["saison"].initial = aktive
        self._style()


class MatchForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = LeagueMatch
        fields = [
            "team",
            "runde",
            "datum",
            "uhrzeit",
            "gegner",
            "heimspiel",
            "ort",
            "brettanzahl",
            "status",
            "bemerkung",
        ]
        widgets = {
            "datum": forms.DateInput(format="%Y-%m-%d"),
            "uhrzeit": forms.TimeInput(format="%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["team"].queryset = Team.objects.all()
        self._style()


class LineupRowForm(forms.ModelForm):
    """Eine Brettzeile – speichert Einzel- oder Gesamtaufstellung."""

    class Meta:
        model = LineupEntry
        fields = ["member", "ersatz_name", "gegner_name", "ergebnis"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["member"].queryset = Member.objects.exclude(
            status=Member.Status.AUSGETRETEN
        )
        self.fields["member"].empty_label = "– nicht benannt –"
        for feld in self.fields.values():
            feld.widget.attrs["class"] = "input"


class LineupBoardForm(forms.Form):
    """Bulk-Speicherung der gesamten Aufstellung."""

    def __init__(self, *args, match=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.match = match
        mitglieder = Member.objects.exclude(status=Member.Status.AUSGETRETEN)
        vorhandene = {eintrag.brett: eintrag for eintrag in match.aufstellung.all()}
        for brett in range(1, match.brettanzahl + 1):
            eintrag = vorhandene.get(brett)
            self.fields[f"member_{brett}"] = forms.ModelChoiceField(
                queryset=mitglieder,
                required=False,
                initial=eintrag.member_id if eintrag else None,
                label=f"Brett {brett}",
                empty_label="– nicht benannt –",
                widget=forms.Select(attrs={"class": "input"}),
            )
            self.fields[f"gegner_{brett}"] = forms.CharField(
                required=False,
                initial=eintrag.gegner_name if eintrag else "",
                max_length=120,
                widget=forms.TextInput(attrs={"class": "input", "placeholder": "Gegner am Brett"}),
            )
            self.fields[f"ergebnis_{brett}"] = forms.ChoiceField(
                required=False,
                choices=LineupEntry.Ergebnis.choices,
                initial=eintrag.ergebnis if eintrag else "",
                widget=forms.Select(attrs={"class": "input"}),
            )

    def speichern(self):
        for brett in range(1, self.match.brettanzahl + 1):
            member = self.cleaned_data.get(f"member_{brett}")
            gegner = self.cleaned_data.get(f"gegner_{brett}", "")
            ergebnis = self.cleaned_data.get(f"ergebnis_{brett}", "")
            if member is None and not gegner and not ergebnis:
                LineupEntry.objects.filter(match=self.match, brett=brett).delete()
                continue
            LineupEntry.objects.update_or_create(
                match=self.match,
                brett=brett,
                defaults={"member": member, "gegner_name": gegner or "", "ergebnis": ergebnis or ""},
            )
        return self.match
