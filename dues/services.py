"""Fachlogik Beitragswesen: Beitragslauf, Zahlungen, Mahnwesen, SEPA-Export (PRD M2/S2.7)."""

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from cashbook.models import CashEntry, storniere_kassenbuchung

from .models import (
    DunningLetter,
    FeeAmount,
    MembershipFee,
    Payment,
    SepaMandate,
    normalize_iban,
)

STANDARD_FAELLIGKEIT = date(2000, 1, 31)  # Platzhalter; Jahr wird ersetzt
SEPA_XML_NS = "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02"


def _faelligkeit(jahr):
    return date(jahr, 1, 31)


@transaction.atomic
def beitragslauf(jahr, faellig_am=None, benutzer=None):
    """Erzeugt Beitragsposten für alle aktiven Mitglieder mit Kategorie (M2.2, ADR-004, ADR-005).

    Idempotent: ein zweiter Lauf für dasselbe Jahr legt nichts doppelt an.
    Bricht ab, wenn für eine Kategorie im angegebenen Jahr kein Beitragssatz hinterlegt ist.
    """
    from members.models import Member

    faellig_am = faellig_am or _faelligkeit(jahr)
    angelegt = []
    uebersprungen = 0
    mitglieder = (
        Member.objects.filter(status=Member.Status.AKTIV, beitragskategorie__isnull=False)
        .select_related("beitragskategorie")
        .order_by("nachname", "vorname")
    )
    vorhandene = set(
        MembershipFee.objects.filter(jahr=jahr).values_list("member_id", flat=True)
    )
    ohne_kategorie = Member.objects.filter(
        status=Member.Status.AKTIV, beitragskategorie__isnull=True
    ).count()

    zu_verarbeitende_kategorien = {
        member.beitragskategorie for member in mitglieder if member.pk not in vorhandene
    }
    saetze = {
        fa.kategorie_id: fa.betrag
        for fa in FeeAmount.objects.filter(
            kategorie__in=zu_verarbeitende_kategorien, jahr=jahr
        )
    }
    fehlende = [
        kat.name
        for kat in sorted(zu_verarbeitende_kategorien, key=lambda k: k.name)
        if kat.pk not in saetze
    ]
    if fehlende:
        namen = ", ".join(f"„{name}“" for name in fehlende)
        raise ValidationError(
            f"Für das Beitragsjahr {jahr} ist für folgende Beitragskategorie(n) kein Beitragssatz hinterlegt: {namen}."
        )

    for member in mitglieder:
        if member.pk in vorhandene:
            uebersprungen += 1
            continue
        kategorie = member.beitragskategorie
        angelegt.append(
            MembershipFee(
                member=member,
                jahr=jahr,
                kategorie_name=kategorie.name,
                betrag=saetze[kategorie.pk],
                faellig_am=faellig_am,
            )
        )
    MembershipFee.objects.bulk_create(angelegt)
    return {
        "angelegt": len(angelegt),
        "uebersprungen": uebersprungen,
        "ohne_kategorie": ohne_kategorie,
        "summe": sum((fee.betrag for fee in angelegt), Decimal("0.00")),
        "jahr": jahr,
    }


@transaction.atomic
def zahlung_erfassen(fee, betrag, datum=None, art=Payment.Art.UEBERWEISUNG, notiz="", benutzer=None):
    """Bucht eine Zahlung und gleicht Status + Kassenbuch ab (M2.3b/M2.5)."""
    betrag = Decimal(str(betrag)).quantize(Decimal("0.01"))
    zahlungsdatum = datum or timezone.localdate()
    kassenbuchung = CashEntry.objects.create(
        art=CashEntry.Art.EINNAHME,
        kategorie=CashEntry.Kategorie.BEITRAEGE,
        betrag=betrag,
        datum=zahlungsdatum,
        beschreibung=f"Beitrag {fee.jahr} – {fee.member}",
        belegnummer=f"BEITRAG-{fee.jahr}-{fee.member_id}",
        erfasst_von=benutzer,
    )
    zahlung = Payment.objects.create(
        fee=fee,
        betrag=betrag,
        datum=zahlungsdatum,
        art=art,
        notiz=notiz,
        kassenbuchung=kassenbuchung,
        erfasst_von=benutzer,
    )
    fee.status_aktualisieren()
    return zahlung


@transaction.atomic
def zahlung_stornieren(zahlung, *, grund="", datum=None, benutzer=None):
    """Storniert eine Beitragszahlung per Gegenbuchung inkl. Kassenbuch und Audit-Log."""
    from core.models import AuditLog

    if zahlung.ist_storno:
        raise ValidationError("Eine Storno-Gegenbuchung kann nicht erneut storniert werden.")
    if zahlung.ist_storniert:
        raise ValidationError("Diese Zahlung wurde bereits storniert.")

    fee = zahlung.fee
    storno_datum = datum or zahlung.datum
    zusatz = f": {grund}" if grund else ""
    notiz = f"Storno zu Zahlung #{zahlung.pk}{zusatz}"[:200]

    kassen_storno = None
    ursprungs_kasse = zahlung.kassenbuchung
    if ursprungs_kasse is None:
        ursprungs_kasse = (
            CashEntry.objects.filter(
                art=CashEntry.Art.EINNAHME,
                kategorie=CashEntry.Kategorie.BEITRAEGE,
                betrag=zahlung.betrag,
                belegnummer=f"BEITRAG-{fee.jahr}-{fee.member_id}",
                storno_von__isnull=True,
                storno_buchung__isnull=True,
            )
            .order_by("-pk")
            .first()
        )
    if ursprungs_kasse is not None and not ursprungs_kasse.ist_storniert:
        kassen_grund = grund or f"Storno Beitragszahlung #{zahlung.pk}"
        kassen_storno = storniere_kassenbuchung(
            ursprungs_kasse, benutzer=benutzer, grund=kassen_grund, datum=storno_datum
        )

    gegenbuchung = Payment.objects.create(
        fee=fee,
        betrag=-zahlung.betrag,
        datum=storno_datum,
        art=zahlung.art,
        notiz=notiz,
        storno_von=zahlung,
        kassenbuchung=kassen_storno,
        erfasst_von=benutzer,
    )
    fee.status_aktualisieren()
    AuditLog.objects.create(
        benutzer=benutzer,
        aktion="Zahlung storniert",
        text=f"Storno zu Zahlung #{zahlung.pk} ({zahlung.betrag:.2f} €) für {fee.member} ({fee.jahr}){zusatz}",
        member=fee.member,
    )
    return gegenbuchung


@transaction.atomic
def mahnung_erstellen(fee, gebuehr=Decimal("0.00"), notiz="", benutzer=None):
    """Erhöht die Mahnstufe (max. 2) und protokolliert die Mahnung (M2.4)."""
    stufe = min(fee.mahnstufe + 1, 2)
    fee.mahnstufe = stufe
    fee.letzte_mahnung_am = timezone.localdate()
    fee.save(update_fields=["mahnstufe", "letzte_mahnung_am"])
    return DunningLetter.objects.create(
        fee=fee,
        stufe=stufe,
        gebuehr=Decimal(str(gebuehr or "0.00")),
        notiz=notiz,
        erstellt_von=benutzer,
    )


def mahntext(dunning):
    """Textbausteine für den Mahnbrief – abhängig von der Mahnstufe."""
    if dunning.stufe >= 2:
        return (
            "trotz unserer ersten Mahnung konnten wir keinen Zahlungseingang "
            "feststellen. Wir bitten Sie letztmalig, den offenen Betrag zu begleichen."
        )
    return (
        "sicherlich haben Sie unsere Zahlungsbitte übersehen. Wir bitten Sie "
        "freundlich, den offenen Betrag innerhalb von 14 Tagen zu überweisen."
    )


def sepa_sanitize(text: str, max_len: int | None = None) -> str:
    """Bereinigt Text gemäß dem EPC SEPA-Zeichensatz.

    Ersetzt deutsche Umlaute und Sonderzeichen durch standardkonforme Zeichen.
    """
    if not text:
        return ""
    ersetzungen = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
        "&": "+",
        "_": "-",
        '"': "'",
    }
    for k, v in ersetzungen.items():
        text = text.replace(k, v)
    erlaubt = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/-?:().,'+ ")
    gefiltert = "".join(c if c in erlaubt else " " for c in text)
    bereinigt = " ".join(gefiltert.split())
    if max_len:
        bereinigt = bereinigt[:max_len].strip()
    return bereinigt


def erstelle_sepa_xml(
    jahr: int,
    ausfuehrung_am: date | None = None,
    glaeubiger_id: str | None = None,
    glaeubiger_iban: str | None = None,
    glaeubiger_name: str | None = None,
    glaeubiger_bic: str | None = None,
    verwendungszweck: str | None = None,
) -> tuple[bytes, dict]:
    """Erzeugt eine SEPA-Lastschriftdatei (pain.008.001.02) für ein Beitragsjahr (PRD S2.7, ADR-017).

    Zieht alle offenen Beitragsposten mit aktivem SEPA-Mandat ein.
    Reine Standardbibliothek (xml.etree.ElementTree), keine Netzwerk-Imports (ADR-002),
    flüchtige Entschlüsselung der IBANs im Arbeitsspeicher (ADR-010).
    """
    # 1. Gläubigerdaten prüfen
    profil = None
    if not (glaeubiger_id and glaeubiger_iban and glaeubiger_name):
        from core.services import get_club_profile
        profil = get_club_profile()

    glaeubiger_id = (
        glaeubiger_id
        or (profil.sepa_glaeubiger_id if profil and profil.sepa_glaeubiger_id else "")
        or getattr(settings, "SEPA_CREDITOR_ID", "")
    ).strip()
    if not glaeubiger_id:
        raise ValidationError(
            "Keine Gläubiger-Identifikationsnummer (SEPA_CREDITOR_ID) konfiguriert."
        )

    glaeubiger_iban = normalize_iban(
        (
            glaeubiger_iban
            or (profil.sepa_iban if profil and profil.sepa_iban else "")
            or getattr(settings, "SEPA_CREDITOR_IBAN", "")
        ).strip()
    )
    if not glaeubiger_iban:
        raise ValidationError(
            "Keine Vereins-IBAN (SEPA_CREDITOR_IBAN) für Lastschriften konfiguriert."
        )

    glaeubiger_name = (
        glaeubiger_name
        or (profil.sepa_glaeubiger_name if profil and profil.sepa_glaeubiger_name else "")
        or (profil.name if profil and profil.name else "")
        or getattr(settings, "SEPA_CREDITOR_NAME", "")
        or getattr(settings, "CLUB_NAME", "Schachverein")
    ).strip()
    glaeubiger_name_bereinigt = sepa_sanitize(glaeubiger_name, max_len=70)

    glaeubiger_bic = (
        glaeubiger_bic
        or (profil.sepa_bic if profil and profil.sepa_bic else "")
        or getattr(settings, "SEPA_CREDITOR_BIC", "")
    ).strip()

    # 2. Einzuziehende Beitragsposten laden (O(1)-Query-Budget)
    posten = (
        MembershipFee.objects.filter(
            jahr=jahr,
            member__sepa_mandat__status=SepaMandate.Status.AKTIV,
        )
        .exclude(status__in=[MembershipFee.Status.BEZAHLT, MembershipFee.Status.ERLASSEN])
        .select_related("member", "member__sepa_mandat")
        .prefetch_related("zahlungen")
        .order_by("member__nachname", "member__vorname")
    )

    einzuege = []
    for fee in posten:
        if not fee.ist_offen:
            continue
        mandat = getattr(fee.member, "sepa_mandat", None)
        if not mandat or mandat.status != SepaMandate.Status.AKTIV:
            continue
        iban = normalize_iban(mandat.iban)
        if not iban:
            continue
        einzuege.append((fee, mandat, iban, fee.offener_betrag))

    if not einzuege:
        raise ValidationError(
            f"Für das Beitragsjahr {jahr} gibt es keine offenen Beitragsposten mit aktivem SEPA-Mandat."
        )

    anzahl = len(einzuege)
    summe = sum((betrag for _, _, _, betrag in einzuege), Decimal("0.00"))

    jetzt = timezone.now()
    cre_dt_tm = jetzt.strftime("%Y-%m-%dT%H:%M:%S")

    ausfuehrung_am = ausfuehrung_am or (timezone.localdate() + timezone.timedelta(days=2))
    reqd_colltn_dt = ausfuehrung_am.strftime("%Y-%m-%d")

    msg_id = sepa_sanitize(f"MSG-{jahr}-{jetzt.strftime('%Y%m%d%H%M%S')}", max_len=35)
    pmt_inf_id = sepa_sanitize(f"PMT-{jahr}-{jetzt.strftime('%Y%m%d%H%M%S')}", max_len=35)

    # 3. XML-Dokument aufbauen
    ET.register_namespace("", SEPA_XML_NS)
    ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")

    root = ET.Element(
        f"{{{SEPA_XML_NS}}}Document",
        attrib={"xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"},
    )
    cstmr = ET.SubElement(root, f"{{{SEPA_XML_NS}}}CstmrDrctDbtInitn")

    # Group Header (<GrpHdr>)
    grp_hdr = ET.SubElement(cstmr, f"{{{SEPA_XML_NS}}}GrpHdr")
    ET.SubElement(grp_hdr, f"{{{SEPA_XML_NS}}}MsgId").text = msg_id
    ET.SubElement(grp_hdr, f"{{{SEPA_XML_NS}}}CreDtTm").text = cre_dt_tm
    ET.SubElement(grp_hdr, f"{{{SEPA_XML_NS}}}NbOfTxs").text = str(anzahl)
    ET.SubElement(grp_hdr, f"{{{SEPA_XML_NS}}}CtrlSum").text = f"{summe:.2f}"
    initg_pty = ET.SubElement(grp_hdr, f"{{{SEPA_XML_NS}}}InitgPty")
    ET.SubElement(initg_pty, f"{{{SEPA_XML_NS}}}Nm").text = glaeubiger_name_bereinigt

    # Payment Information (<PmtInf>)
    pmt_inf = ET.SubElement(cstmr, f"{{{SEPA_XML_NS}}}PmtInf")
    ET.SubElement(pmt_inf, f"{{{SEPA_XML_NS}}}PmtInfId").text = pmt_inf_id
    ET.SubElement(pmt_inf, f"{{{SEPA_XML_NS}}}PmtMtd").text = "DD"
    ET.SubElement(pmt_inf, f"{{{SEPA_XML_NS}}}NbOfTxs").text = str(anzahl)
    ET.SubElement(pmt_inf, f"{{{SEPA_XML_NS}}}CtrlSum").text = f"{summe:.2f}"

    pmt_tp_inf = ET.SubElement(pmt_inf, f"{{{SEPA_XML_NS}}}PmtTpInf")
    svc_lvl = ET.SubElement(pmt_tp_inf, f"{{{SEPA_XML_NS}}}SvcLvl")
    ET.SubElement(svc_lvl, f"{{{SEPA_XML_NS}}}Cd").text = "SEPA"
    lcl_instrm = ET.SubElement(pmt_tp_inf, f"{{{SEPA_XML_NS}}}LclInstrm")
    ET.SubElement(lcl_instrm, f"{{{SEPA_XML_NS}}}Cd").text = "CORE"
    ET.SubElement(pmt_tp_inf, f"{{{SEPA_XML_NS}}}SeqTp").text = "RCUR"

    ET.SubElement(pmt_inf, f"{{{SEPA_XML_NS}}}ReqdColltnDt").text = reqd_colltn_dt

    cdtr = ET.SubElement(pmt_inf, f"{{{SEPA_XML_NS}}}Cdtr")
    ET.SubElement(cdtr, f"{{{SEPA_XML_NS}}}Nm").text = glaeubiger_name_bereinigt

    cdtr_acct = ET.SubElement(pmt_inf, f"{{{SEPA_XML_NS}}}CdtrAcct")
    id_elem = ET.SubElement(cdtr_acct, f"{{{SEPA_XML_NS}}}Id")
    ET.SubElement(id_elem, f"{{{SEPA_XML_NS}}}IBAN").text = glaeubiger_iban

    cdtr_agt = ET.SubElement(pmt_inf, f"{{{SEPA_XML_NS}}}CdtrAgt")
    fin_instn = ET.SubElement(cdtr_agt, f"{{{SEPA_XML_NS}}}FinInstnId")
    if glaeubiger_bic:
        ET.SubElement(fin_instn, f"{{{SEPA_XML_NS}}}BIC").text = glaeubiger_bic
    else:
        othr = ET.SubElement(fin_instn, f"{{{SEPA_XML_NS}}}Othr")
        ET.SubElement(othr, f"{{{SEPA_XML_NS}}}Id").text = "NOTPROVIDED"

    ET.SubElement(pmt_inf, f"{{{SEPA_XML_NS}}}ChrgBr").text = "SLEV"

    cdtr_schme = ET.SubElement(pmt_inf, f"{{{SEPA_XML_NS}}}CdtrSchmeId")
    cs_id = ET.SubElement(cdtr_schme, f"{{{SEPA_XML_NS}}}Id")
    org_id = ET.SubElement(cs_id, f"{{{SEPA_XML_NS}}}OrgId")
    cs_othr = ET.SubElement(org_id, f"{{{SEPA_XML_NS}}}Othr")
    ET.SubElement(cs_othr, f"{{{SEPA_XML_NS}}}Id").text = glaeubiger_id
    schme_nm = ET.SubElement(cs_othr, f"{{{SEPA_XML_NS}}}SchmeNm")
    ET.SubElement(schme_nm, f"{{{SEPA_XML_NS}}}Prtry").text = "SEPA"

    # Transaktionen (<DrctDbtTxInf>)
    for fee, mandat, iban, betrag in einzuege:
        tx = ET.SubElement(pmt_inf, f"{{{SEPA_XML_NS}}}DrctDbtTxInf")

        pmt_id = ET.SubElement(tx, f"{{{SEPA_XML_NS}}}PmtId")
        end_to_end_id = sepa_sanitize(f"BEITRAG-{fee.jahr}-{fee.member_id}", max_len=35)
        ET.SubElement(pmt_id, f"{{{SEPA_XML_NS}}}EndToEndId").text = end_to_end_id

        instd_amt = ET.SubElement(tx, f"{{{SEPA_XML_NS}}}InstdAmt", attrib={"Ccy": "EUR"})
        instd_amt.text = f"{betrag:.2f}"

        drct_dbt_tx = ET.SubElement(tx, f"{{{SEPA_XML_NS}}}DrctDbtTx")
        mndt_rltd = ET.SubElement(drct_dbt_tx, f"{{{SEPA_XML_NS}}}MndtRltdInf")
        mndt_id = sepa_sanitize(mandat.referenz, max_len=35)
        ET.SubElement(mndt_rltd, f"{{{SEPA_XML_NS}}}MndtId").text = mndt_id
        ET.SubElement(mndt_rltd, f"{{{SEPA_XML_NS}}}DtOfSgntr").text = mandat.erteilt_am.strftime("%Y-%m-%d")
        ET.SubElement(mndt_rltd, f"{{{SEPA_XML_NS}}}AmdmntInd").text = "false"

        dbtr_agt = ET.SubElement(tx, f"{{{SEPA_XML_NS}}}DbtrAgt")
        fin_instn_dbtr = ET.SubElement(dbtr_agt, f"{{{SEPA_XML_NS}}}FinInstnId")
        othr_dbtr = ET.SubElement(fin_instn_dbtr, f"{{{SEPA_XML_NS}}}Othr")
        ET.SubElement(othr_dbtr, f"{{{SEPA_XML_NS}}}Id").text = "NOTPROVIDED"

        dbtr = ET.SubElement(tx, f"{{{SEPA_XML_NS}}}Dbtr")
        inhaber = mandat.kontoinhaber or f"{fee.member.vorname} {fee.member.nachname}"
        ET.SubElement(dbtr, f"{{{SEPA_XML_NS}}}Nm").text = sepa_sanitize(inhaber, max_len=70)

        dbtr_acct = ET.SubElement(tx, f"{{{SEPA_XML_NS}}}DbtrAcct")
        id_dbtr = ET.SubElement(dbtr_acct, f"{{{SEPA_XML_NS}}}Id")
        ET.SubElement(id_dbtr, f"{{{SEPA_XML_NS}}}IBAN").text = iban

        rmt_inf = ET.SubElement(tx, f"{{{SEPA_XML_NS}}}RmtInf")
        zweck = verwendungszweck or f"Mitgliedsbeitrag {fee.jahr} - {fee.member.vorname} {fee.member.nachname}"
        ET.SubElement(rmt_inf, f"{{{SEPA_XML_NS}}}Ustrd").text = sepa_sanitize(zweck, max_len=140)

    ET.indent(root, space="  ")
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    metadaten = {
        "jahr": jahr,
        "anzahl_posten": anzahl,
        "gesamtsumme": summe,
        "ausfuehrung_am": ausfuehrung_am,
        "msg_id": msg_id,
    }
    return xml_bytes, metadaten


@transaction.atomic
def sepa_sammelverbuchung(jahr, benutzer=None, buchungsdatum=None, notiz=None):
    """Verbucht alle offenen Beitragsposten eines Jahres mit aktivem SEPA-Mandat als eingezogen (Hebel F1).

    Atomar, idempotent bezüglich bereits bezahlter Posten, erzeugt Kassenbuchungen
    und protokolliert die Aktion im AuditLog.
    """
    from core.models import AuditLog

    posten = MembershipFee.objects.filter(
        jahr=jahr,
        status__in=[MembershipFee.Status.OFFEN, MembershipFee.Status.TEILWEISE],
        member__sepa_mandat__status=SepaMandate.Status.AKTIV,
    ).select_related("member", "member__sepa_mandat")

    if not posten.exists():
        raise ValidationError(f"Keine offenen Posten mit aktivem SEPA-Mandat für das Beitragsjahr {jahr} gefunden.")

    datum = buchungsdatum or timezone.localdate()
    notiz_text = notiz or f"SEPA-Sammellastschrift Beitragsjahr {jahr}"
    erfasste = []
    gesamtsumme = Decimal("0.00")

    for fee in posten:
        offen = fee.offener_betrag
        if offen > Decimal("0.00"):
            zahlung = zahlung_erfassen(
                fee=fee,
                betrag=offen,
                datum=datum,
                art=Payment.Art.SEPA,
                notiz=notiz_text,
                benutzer=benutzer,
            )
            erfasste.append(zahlung)
            gesamtsumme += offen

    AuditLog.objects.create(
        benutzer=benutzer,
        aktion="SEPA-Sammelverbuchung",
        text=f"SEPA-Sammelverbuchung für {jahr}: {len(erfasste)} Posten verbucht, Summe {gesamtsumme:.2f} €.",
    )
    return {"anzahl": len(erfasste), "summe": gesamtsumme, "zahlungen": erfasste}

