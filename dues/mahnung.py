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
from .services import offen, posten_mit_status


def mahnstufe_text(stufe):
    """„1. Mahnung“ / „2. Mahnung“ / „ausgeschöpft“ — eine Quelle für alle Anzeigen."""
    if stufe is None:
        return "ausgeschöpft"
    return f"{stufe}. Mahnung"


def naechste_stufe_fuer(mahnungen):
    """:func:`naechste_stufe` für eine bereits geladene Liste von Mahnungen."""
    gesetzt = {mahnung.stufe for mahnung in mahnungen}
    for stufe in (Mahnung.Stufe.MAHNUNG_1, Mahnung.Stufe.MAHNUNG_2):
        if stufe not in gesetzt:
            return stufe
    return None


def naechste_stufe(post):
    """Die Stufe, die als Nächstes gesetzt werden darf; ``None`` ist „keine mehr“.

    Stufen werden nicht übersprungen: ohne Mahnung beginnt es bei 1.
    """
    return naechste_stufe_fuer(post.mahnungen.all())


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


def offene_posten(jahr):
    """Beitragsposten des Jahres, die noch offen sind — eine Abfrage, keine N+1.

    Basis ist :func:`dues.services.posten_mit_status` (Posten, Kategorie, Mit-
    glied und Zahlungsstand in einer Abfrage). Danach wird nur ausgefiltert:
    ``offen <= 0`` fällt heraus — dazu gehören bezahlte Posten und Gutschriften,
    denn auf beides schreibt man keinen Mahnbrief. ``offen`` stammt aus der
    Annotation dieser Abfrage; :func:`dues.services.offen` wird hier bewusst
    **nicht** je Zeile aufgerufen, weil es ohne Annotation je Aufruf selbst
    nachsummieren würde.

    Die Mahnungen kommen in **einer** Abfrage über ``post_id__in`` — erst nach
    dem Filtern, auf die IDs der übrig gebliebenen Posten. Ein Jahr mit tausend
    bezahlten Posten lädt so nicht deren Mahnverläufe mit und wirft sie wieder
    weg. Über ``post_id`` indiziert kostet die Stufe je Zeile keine
    Zusatzabfrage.
    """
    zeilen = [
        zeile for zeile in posten_mit_status(jahr) if zeile["offen"] > Decimal("0.00")
    ]

    mahnungen_pro_post = {}
    for mahnung in Mahnung.objects.filter(
        post_id__in=[zeile["post"].pk for zeile in zeilen]
    ).order_by("datum", "pk"):
        mahnungen_pro_post.setdefault(mahnung.post_id, []).append(mahnung)

    for zeile in zeilen:
        mahnungen = mahnungen_pro_post.get(zeile["post"].pk, [])
        stufe = naechste_stufe_fuer(mahnungen)
        zeile.update(
            mahnungen=mahnungen,
            stufe=stufe,
            stufe_text=mahnstufe_text(stufe),
        )
    return zeilen


def posten_fuer_brief(jahr, member):
    """Offene Posten eines Mitglieds plus Summe — Grundlage des Mahnbriefs.

    Schneidet bewusst aus :func:`offene_posten`, damit Brief und Übersicht nie
    auseinanderlaufen können. Ist die Liste leer (inzwischen bezahlt), gibt es
    keinen Brief — die View gibt dann 404.
    """
    posten = [z for z in offene_posten(jahr) if z["post"].member_id == member.pk]
    summe = sum((z["offen"] for z in posten), Decimal("0.00"))
    return posten, summe
