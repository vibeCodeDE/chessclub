from django import forms
from django.core.exceptions import ValidationError

from dues.models import FeeCategory

from .models import EDITABLE_FIELDS, ChangeRequest, Member, clean_member_value


class StyledFormMixin:
    """Einheitliche Widget-Klassen und Datumsfelder für das Design-System."""

    def _style(self):
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                continue
            css = widget.attrs.get("class", "")
            widget.attrs["class"] = (css + " input").strip()
            if isinstance(widget, forms.DateInput):
                widget.input_type = "date"
                widget.format = "%Y-%m-%d"
            if isinstance(widget, forms.TimeInput):
                widget.input_type = "time"
                widget.format = "%H:%M"
            if field.required:
                widget.attrs.setdefault("required", "required")


class MemberForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "vorname",
            "nachname",
            "geburtsdatum",
            "strasse",
            "plz",
            "ort",
            "email",
            "telefon",
            "eintrittsdatum",
            "status",
            "austrittsdatum",
            "beitragskategorie",
            "email_opt_in",
        ]
        widgets = {
            "eintrittsdatum": forms.DateInput(format="%Y-%m-%d"),
            "austrittsdatum": forms.DateInput(format="%Y-%m-%d"),
            "geburtsdatum": forms.DateInput(format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["geburtsdatum"].required = False
        self.fields["austrittsdatum"].required = False
        self.fields["beitragskategorie"].queryset = FeeCategory.objects.all()
        self.fields["beitragskategorie"].empty_label = "– keine Kategorie –"
        self.fields["beitragskategorie"].label = "Beitragskategorie"
        self._style()


class MemberStatusForm(forms.Form):
    """Schneller Statuswechsel aus der Liste (optimistisches Update)."""

    status = forms.ChoiceField(choices=Member.Status.choices)
    austrittsdatum = forms.DateField(required=False, input_formats=["%Y-%m-%d"])

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        austrittsdatum = cleaned.get("austrittsdatum")
        if status == Member.Status.AUSGETRETEN and not austrittsdatum:
            from django.utils import timezone

            cleaned["austrittsdatum"] = timezone.localdate()
        if status != Member.Status.AUSGETRETEN and austrittsdatum:
            raise ValidationError("Ein Austrittsdatum ist nur beim Status „ausgetreten“ erlaubt.")
        return cleaned


class ChangeRequestForm(forms.Form):
    """Einreichung eines Änderungswunschs durch das Mitglied selbst."""

    feld = forms.ChoiceField(label="Feld", choices=list(EDITABLE_FIELDS.items()))
    wunschwert = forms.CharField(label="Neuer Wert", max_length=200)

    def __init__(self, *args, member=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.member = member
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "input"

    def clean(self):
        cleaned = super().clean()
        feld = cleaned.get("feld")
        wunschwert = cleaned.get("wunschwert")
        if self.member is None or feld is None or wunschwert is None:
            return cleaned

        wunschwert = wunschwert.strip()
        cleaned["wunschwert"] = wunschwert

        try:
            clean_member_value(feld, wunschwert)
        except ValidationError as exc:
            self.add_error("wunschwert", exc.messages)
            return cleaned

        if str(getattr(self.member, feld) or "") == wunschwert:
            self.add_error("wunschwert", "Der Wunschwert entspricht dem aktuellen Wert.")
            return cleaned

        offen = self.member.change_requests.filter(
            feld=feld, status=ChangeRequest.Status.EINGEREICHT
        ).exists()
        if offen:
            self.add_error(
                "feld", "Für dieses Feld besteht bereits ein offener Änderungswunsch."
            )
        return cleaned
