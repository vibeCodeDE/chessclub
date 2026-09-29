from django import forms

from members.forms import StyledFormMixin

from .models import MailLog, NewsPost


class NewsForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = NewsPost
        fields = ["titel", "kategorie", "text", "veroeffentlicht"]
        widgets = {"text": forms.Textarea(attrs={"rows": 10})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["veroeffentlicht"].label = "Sofort veröffentlichen"
        self.fields["kategorie"].widget.attrs["placeholder"] = "z. B. Verein, Jugend, Turnier"
        self._style()


class MailForm(StyledFormMixin, forms.Form):
    """Formular „E-Mail an Gruppe“ (PRD M5.2)."""

    betreff = forms.CharField(label="Betreff", max_length=200)
    zielgruppe = forms.ChoiceField(label="Empfängergruppe", choices=MailLog.Zielgruppe.choices)
    text = forms.CharField(label="Nachricht", widget=forms.Textarea(attrs={"rows": 12}))
    test_empfaenger = forms.CharField(
        label="Nur Testversand an (optional)",
        required=False,
        help_text="Kommagetrennte Adressen – dann geht die Mail ausschließlich dorthin.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["zielgruppe"].initial = MailLog.Zielgruppe.AKTIV
        self._style()
