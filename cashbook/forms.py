from django import forms
from django.utils import timezone

from members.forms import StyledFormMixin

from .models import CashEntry


class CashEntryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CashEntry
        fields = ["art", "kategorie", "betrag", "datum", "beschreibung", "belegnummer"]
        widgets = {"datum": forms.DateInput(format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["datum"].initial = timezone.localdate()
        self.fields["beschreibung"].widget.attrs["placeholder"] = "z. B. Startgeld Jugendturnier"
        self._style()
