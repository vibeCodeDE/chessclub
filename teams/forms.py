from django import forms

from members.forms import StyledFormMixin
from members.models import Member

from .models import LeagueMatch, LineupEntry, Team


class TeamForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "liga", "altersklasse", "brettanzahl", "kapitaen", "aktiv"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kapitaen"].queryset = Member.objects.exclude(status=Member.Status.AUSGETRETEN)
        self.fields["kapitaen"].help_text = "Darf die Aufstellung pflegen."
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
