from django import forms
from django.core.exceptions import ValidationError

from .models import EDITABLE_FIELDS, ChangeRequest, clean_member_value


class ChangeRequestForm(forms.Form):
    """Einreichung eines Änderungswunschs durch das Mitglied selbst."""

    feld = forms.ChoiceField(label="Feld", choices=list(EDITABLE_FIELDS.items()))
    wunschwert = forms.CharField(label="Neuer Wert", max_length=200)

    def __init__(self, *args, member=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.member = member

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
