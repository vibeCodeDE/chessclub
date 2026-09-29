from django import forms
from django.utils import timezone

from members.forms import StyledFormMixin

from .models import FeeCategory, MembershipFee, Payment, SepaMandate


class FeeCategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = FeeCategory
        fields = ["name", "beschreibung", "betrag", "aktiv"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class SepaMandateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SepaMandate
        fields = ["member", "referenz", "iban", "kontoinhaber", "erteilt_am", "status", "widerrufen_am", "notiz"]
        widgets = {
            "erteilt_am": forms.DateInput(format="%Y-%m-%d"),
            "widerrufen_am": forms.DateInput(format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from members.models import Member

        self.fields["member"].queryset = Member.objects.exclude(status=Member.Status.AUSGETRETEN)
        self.fields["erteilt_am"].initial = timezone.localdate()
        self._style()


class PaymentForm(StyledFormMixin, forms.Form):
    betrag = forms.DecimalField(label="Betrag (€)", max_digits=8, decimal_places=2, min_value=0.01)
    datum = forms.DateField(label="Zahlungsdatum", initial=timezone.localdate)
    art = forms.ChoiceField(label="Zahlungsart", choices=Payment.Art.choices, initial=Payment.Art.UEBERWEISUNG)
    notiz = forms.CharField(label="Notiz", max_length=200, required=False)

    def __init__(self, *args, fee=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fee = fee
        if fee is not None and not self.is_bound:
            self.fields["betrag"].initial = fee.offener_betrag
        for feld in self.fields.values():
            if isinstance(feld.widget, forms.DateInput):
                feld.widget.input_type = "date"
                feld.widget.format = "%Y-%m-%d"
        self._style()


class DunningForm(StyledFormMixin, forms.Form):
    gebuehr = forms.DecimalField(label="Mahngebühr (€)", max_digits=6, decimal_places=2, required=False, initial=0)
    notiz = forms.CharField(label="Notiz", max_length=200, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class BeitragslaufForm(StyledFormMixin, forms.Form):
    jahr = forms.IntegerField(
        label="Beitragsjahr",
        min_value=2000,
        max_value=2100,
        initial=timezone.localdate().year,
    )
    faellig_am = forms.DateField(
        label="Fällig am", required=False, widget=forms.DateInput(format="%Y-%m-%d")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["faellig_am"].widget.input_type = "date"
        self.fields["faellig_am"].widget.format = "%Y-%m-%d"
        self._style()

    def clean_faellig_am(self):
        datum = self.cleaned_data.get("faellig_am")
        if not datum:
            jahr = self.cleaned_data.get("jahr") or timezone.localdate().year
            return timezone.datetime(jahr, 1, 31).date()
        return datum


class FeeFilterForm(forms.Form):
    jahr = forms.IntegerField(required=False)
    status = forms.ChoiceField(required=False, choices=[("", "Alle Status"), *MembershipFee.Status.choices])
