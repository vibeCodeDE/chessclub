"""Mahnwesen (PRD M2.5): offene Beiträge sehen, 1./2. Mahnung setzen, Brief.

Die Stufenregel steht hier und nicht im View, damit Übersicht, Brief und Tests
dieselbe Antwort bekommen. Grundlage ist :func:`dues.services.offen` — es gibt
im ganzen Mahnwesen keine zweite Berechnung des offenen Betrags.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.models import AuditLog

from .models import Mahnung
from .services import offen


def mahnstufe_text(stufe):
    """„1. Mahnung“ / „2. Mahnung“ / „ausgeschöpft“ — eine Quelle für alle Anzeigen."""
    if stufe is None:
        return "ausgeschöpft"
    return f"{stufe}. Mahnung"


def naechste_stufe(post):
    """Die Stufe, die als Nächstes gesetzt werden darf; ``None`` ist „keine mehr“.

    Stufen werden nicht übersprungen: ohne Mahnung beginnt es bei 1.
    """
    gesetzt = set(post.mahnungen.values_list("stufe", flat=True))
    for stufe in (Mahnung.Stufe.MAHNUNG_1, Mahnung.Stufe.MAHNUNG_2):
        if stufe not in gesetzt:
            return stufe
    return None


def _doppelte_stufe_meldung(post, stufe):
    return ValidationError(
        f"Die {mahnstufe_text(stufe)} für {post} existiert bereits — "
        "bitte die nächste Stufe setzen."
    )


def mahnungen_setzen(post, stufe, datum, frist=None, benutzer=None, notiz=""):
    """Setzt die nächste Mahnung für ``post`` (PRD M2.5).

    Drei Regeln, alle mit verständlicher Meldung statt Datenbankfehler:

    1. der Posten muss noch offen sein (Zahlung macht ihn unmahnbare),
    2. die Stufe muss genau :func:`naechste_stufe` sein — weder überspringen
       noch doppeln,
    3. ein Datum muss angegeben sein.

    Rückdatierte Daten sind erlaubt (der Vorstand mahnt im Voraus). ``frist``
    ist optional — ohne Frist gilt schlicht „keine Zahlungsfrist" —, ``datum``
    ist dagegen Pflicht und wird nie leer angenommen. Die Frist wird bewusst
    nicht gegen das Mahndatum geprüft: sie ist ein Textfeld für den Brief, kein
    abgeleitetes Datum.
    """
    if datum is None:
        raise ValidationError("Bitte ein gültiges Mahndatum angeben.")

    erwartet = naechste_stufe(post)
    if erwartet is None:
        raise ValidationError(
            f"Für {post} sind beide Mahnstufen ausgeschöpft — "
            "es ist keine weitere Mahnung möglich."
        )
    if stufe != erwartet:
        if stufe in (Mahnung.Stufe.MAHNUNG_1, Mahnung.Stufe.MAHNUNG_2):
            if stufe < erwartet:
                raise _doppelte_stufe_meldung(post, stufe)
            raise ValidationError(
                f"Die {mahnstufe_text(stufe)} kann nicht gesetzt werden — "
                f"es fehlt die {mahnstufe_text(erwartet)}."
            )
        raise ValidationError("Unbekannte Mahnstufe.")

    if offen(post) <= Decimal("0.00"):
        raise ValidationError(
            f"Der Beitragsposten {post} ist bereits bezahlt — "
            "für ihn kann keine Mahnung gesetzt werden."
        )

    with transaction.atomic():
        try:
            # Der innere Block ist ein Savepoint. Nur dadurch lässt sich die
            # IntegrityError der Constraint überhaupt abfangen, ohne dass die
            # äußere Transaktion als unbrauchbar markiert wird — ein „fangen
            # und weitermachen" wäre sonst ein TransactionManagementError.
            with transaction.atomic():
                mahnung = Mahnung.objects.create(
                    post=post,
                    stufe=stufe,
                    datum=datum,
                    frist=frist,
                    notiz=notiz,
                    erstellt_von=benutzer,
                )
        except IntegrityError:
            # Zwei gleichzeitige Klicks: die DB-Constraint fängt ab, der
            # Vorstand soll trotzdem eine Meldung statt eines 500 sehen.
            raise _doppelte_stufe_meldung(post, stufe)

        # Der Audit-Eintrag gehört in dieselbe Transaktion wie die Mahnung: eine
        # gemahnte Buchung ohne Protokollzeile wäre hinterher nicht von einer
        # nie gemahnten zu unterscheiden. Steht er außerhalb, bliebe die Mahnung
        # bei einem Audit-Ausfall ohne jede Spur stehen.
        AuditLog.objects.create(
            benutzer=benutzer,
            aktion="Mahnung gesetzt",
            text=(
                f"{post.jahr} · {post.member}: {mahnstufe_text(stufe)} vom "
                f"{datum.isoformat()}"
                + (f", Frist {frist.isoformat()}" if frist else "")
            ),
            member=post.member,
        )
    return mahnung
