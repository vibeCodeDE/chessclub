"""Fachlogik der Beitragsverwaltung (PRD M2.2).

Der Beitragslauf ist bewusst als Service und nicht als View-Logik umgesetzt:
Planung (:func:`plan_lauf`) und Ausführung (:func:`fuehre_lauf`) brauchen
dieselbe Regelbasis, und die Ausführung muss auch aus Tests und späteren
Tasks (Export T10, Kassenbericht T11b) ohne HTTP-Kontext nutzbar sein.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import AuditLog
from members.models import Member

from .models import FeeAmount, FeePost


@dataclass
class BeitragslaufPlan:
    """Ergebnis einer Laufplanung — schreibt nichts, bucht nichts."""

    jahr: int
    passiv_einbezogen: bool = False
    # Ungespeicherte FeePost-Objekte: so sähen die neuen Posten aus.
    posten: list = field(default_factory=list)
    uebersprungen: list = field(default_factory=list)
    # Nur gefüllt, wenn passiv_einbezogen=False ist: sonst wäre im Lauf-Ergebnis
    # nicht sichtbar, dass diese Mitglieder gar nicht zur Wahl standen.
    passiv_ausgenommen: list = field(default_factory=list)
    fehlende_saetze: list = field(default_factory=list)
    anzahl_vorhanden: int = 0
    summe_neu: Decimal = Decimal("0.00")
    summe_gesamt: Decimal = Decimal("0.00")

    @property
    def anzahl_neu(self):
        return len(self.posten)

    @property
    def lauf_moeglich(self):
        """Ein Lauf ist blockiert, wenn eine Kategorie keinen Satz für das Jahr hat."""
        return not self.fehlende_saetze


def eur(betrag):
    """Deutsches Zahlenformat — die App ist durchgängig deutschsprachig."""
    return f"{betrag:.2f}".replace(".", ",") + " €"


def _statuse(passiv_einbezogen):
    statuse = [Member.Status.AKTIV]
    if passiv_einbezogen:
        # „passiv" ist im PRD nicht als beitragspflichtig definiert (M1.3/M1.6),
        # deshalb entscheidet der Lauf-Dialog darüber — Default: nicht buchen.
        statuse.append(Member.Status.PASSIV)
    return statuse


def _mitglieder(statuse):
    return (
        Member.objects.filter(status__in=statuse)
        .select_related("beitragskategorie")
        .order_by("nachname", "vorname")
    )


def plan_lauf(jahr, passiv_einbezogen=False):
    """Berechnet, was ein Beitragslauf für ``jahr`` erzeugen würde.

    Idempotenz-Zentrale: Mitglieder, die für ``jahr`` bereits einen Posten
    haben, tauchen nicht in :attr:`BeitragslaufPlan.posten` auf. Ein zweiter
    Lauf ergänzt daher nur, was fehlt (z. B. ein im Jahresverlauf
    beigetretenes Mitglied) und erzeugt keine Dubletten.
    """
    statuse = _statuse(passiv_einbezogen)
    saetze = {
        satz.kategorie_id: satz.betrag
        for satz in FeeAmount.objects.filter(jahr=jahr)
    }
    vorhandene = list(
        FeePost.objects.filter(jahr=jahr).values_list("member_id", "betrag")
    )
    vorhandene_ids = {member_id for member_id, _ in vorhandene}

    posten, fehlende_saetze, uebersprungen = [], [], []
    for member in _mitglieder(statuse):
        kategorie = member.beitragskategorie
        if kategorie is None:
            # Ohne Kategorie wird übersprungen — nie mit 0 € gebucht.
            uebersprungen.append(member)
            continue
        if member.pk in vorhandene_ids:
            continue
        betrag = saetze.get(kategorie.pk)
        if betrag is None:
            if kategorie not in fehlende_saetze:
                fehlende_saetze.append(kategorie)
            continue
        posten.append(
            FeePost(member=member, jahr=jahr, kategorie=kategorie, betrag=betrag)
        )

    passiv_ausgenommen = []
    if not passiv_einbezogen:
        passiv_ausgenommen = list(
            Member.objects.filter(status=Member.Status.PASSIV)
            .order_by("nachname", "vorname")
        )

    fehlende_saetze.sort(key=lambda kategorie: kategorie.bezeichnung)
    return BeitragslaufPlan(
        jahr=jahr,
        passiv_einbezogen=passiv_einbezogen,
        posten=posten,
        uebersprungen=uebersprungen,
        passiv_ausgenommen=passiv_ausgenommen,
        fehlende_saetze=fehlende_saetze,
        anzahl_vorhanden=len(vorhandene_ids),
        summe_neu=sum((posten_.betrag for posten_ in posten), Decimal("0.00")),
        summe_gesamt=sum((betrag for _, betrag in vorhandene), Decimal("0.00"))
        + sum((posten_.betrag for posten_ in posten), Decimal("0.00")),
    )


def _fehlermeldung(plan):
    return ValidationError(
        [
            f"Für die Kategorie „{kategorie.bezeichnung}“ fehlt der Beitragssatz "
            f"für {plan.jahr}. Der Lauf wurde abgebrochen, damit keine 0-€-Posten "
            "entstehen — bitte den Satz im Django-Admin nachtragen."
            for kategorie in plan.fehlende_saetze
        ]
    )


def fuehre_lauf(jahr, benutzer=None, passiv_einbezogen=False):
    """Legt je Mitglied einen Beitragsposten für ``jahr`` an (PRD M2.2).

    Bricht mit :class:`~django.core.exceptions.ValidationError` ab, wenn eine
    beteiligte Kategorie keinen Satz für ``jahr`` hat. In dem Fall wird
    **nichts** gebucht — auch nicht teilweise.
    """
    with transaction.atomic():
        plan = plan_lauf(jahr, passiv_einbezogen=passiv_einbezogen)
        if not plan.lauf_moeglich:
            raise _fehlermeldung(plan)

        erzeugte = [
            FeePost.objects.create(
                member=posten_.member,
                jahr=jahr,
                kategorie=posten_.kategorie,
                betrag=posten_.betrag,
            )
            for posten_ in plan.posten
        ]
        plan.posten = erzeugte

        if erzeugte:
            # Sammelaktion: eine Zeile im Audit-Log statt einer je Mitglied
            # (vgl. „Stammdaten geändert" in core/signals.py).
            AuditLog.objects.create(
                benutzer=benutzer,
                aktion="Beitragslauf ausgeführt",
                text=(
                    f"Jahr {jahr}: {len(erzeugte)} Posten über "
                    f"{eur(plan.summe_neu)} erzeugt, "
                    f"{len(plan.uebersprungen)} übersprungen (ohne Kategorie), "
                    f"{len(plan.passiv_ausgenommen)} passiv nicht einbezogen, "
                    f"{plan.anzahl_vorhanden} bereits vorhanden."
                ),
            )
    return plan
