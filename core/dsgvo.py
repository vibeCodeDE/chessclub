"""DSGVO-Werkzeuge: Datenauskunft, Verzeichnis von Verarbeitungstätigkeiten,
Anonymisierung nach Frist (PRD N1.2–N1.5).
"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.models import AuditLog
from dues.models import MembershipFee, Payment, SepaMandate
from members.models import ChangeRequest, Member

#: Aufbewahrungsfrist nach Austritt, danach werden Kontaktdaten anonymisiert.
#: Finanzdaten bleiben für steuerliche Aufbewahrungsfristen (10 Jahre) erhalten.
ANONYMISIERUNGS_FRIST_TAGE = int(getattr(settings, "DSGVO_ANONYMISIERUNGS_FRIST_TAGE", 730))

ANONYMISIERT_VORNAME = "Ehemaliges"
ANONYMISIERT_NACHNAME = "Mitglied"


def personenbezogene_daten(member):
    """Sammelt alle zu einem Mitglied gespeicherten Datenkategorien."""
    fees = (
        MembershipFee.objects.filter(member=member)
        .select_related("member")
        .prefetch_related("zahlungen", "mahnungen")
        .order_by("-jahr")
    )
    return {
        "stammdaten": {
            "vorname": member.vorname,
            "nachname": member.nachname,
            "geburtsdatum": member.geburtsdatum,
            "strasse": member.strasse,
            "plz": member.plz,
            "ort": member.ort,
            "email": member.email,
            "telefon": member.telefon,
            "eintrittsdatum": member.eintrittsdatum,
            "austrittsdatum": member.austrittsdatum,
            "status": member.get_status_display(),
            "beitragskategorie": getattr(member.beitragskategorie, "name", ""),
            "email_opt_in": member.email_opt_in,
            "benutzerkonto": member.user.get_username() if member.user else "",
            "anonymisiert_am": member.anonymisiert_am,
        },
        "statusverlauf": [
            {
                "von": wechsel.alt_status,
                "nach": wechsel.neu_status,
                "am": wechsel.geaendert_am,
                "durch": wechsel.geaendert_von.get_username() if wechsel.geaendert_von else "",
                "notiz": wechsel.notiz,
            }
            for wechsel in member.status_history.select_related("geaendert_von")
        ],
        "beitraege": [
            {
                "jahr": fee.jahr,
                "kategorie": fee.kategorie_name,
                "betrag": fee.betrag,
                "status": fee.get_status_display(),
                "faellig_am": fee.faellig_am,
                "mahnstufe": fee.mahnstufe,
                "zahlungen": [
                    {"betrag": z.betrag, "datum": z.datum, "art": z.get_art_display()}
                    for z in fee.zahlungen.all()
                ],
            }
            for fee in fees
        ],
        "sepa_mandat": None,
        "aenderungswuensche": [
            {
                "feld": wunsch.feld,
                "wunschwert": wunsch.wunschwert,
                "status": wunsch.get_status_display(),
                "eingereicht_am": wunsch.eingereicht_am,
                "entschieden_am": wunsch.entschieden_am,
                "kommentar": wunsch.kommentar,
            }
            for wunsch in member.change_requests.select_related("entschieden_von")
        ],
        "turnierteilnahmen": [
            {
                "turnier": teilnahme.tournament.name,
                "datum": teilnahme.tournament.datum,
                "twz": teilnahme.twz,
                "startgeld_bezahlt": teilnahme.startgeld_bezahlt,
            }
            for teilnahme in member.turnierteilnahmen.select_related("tournament")
        ],
        "mannschaftseinsaetze": [
            {
                "spiel": f"{einsatz.match.team.name} gegen {einsatz.match.gegner}",
                "datum": einsatz.match.datum,
                "brett": einsatz.brett,
                "ergebnis": einsatz.ergebnis,
            }
            for einsatz in member.lineups.select_related("match", "match__team")
        ],
        "protokollierung": [
            {
                "zeitpunkt": eintrag.zeitpunkt,
                "aktion": eintrag.aktion,
                "feld": eintrag.feld,
                "alt_wert": eintrag.alt_wert,
                "neu_wert": eintrag.neu_wert,
                "benutzer": eintrag.benutzer.get_username() if eintrag.benutzer else "",
            }
            for eintrag in AuditLog.objects.filter(member=member).select_related("benutzer")[:200]
        ],
        "zahlungen_gesamt": sum(p.betrag for p in Payment.objects.filter(fee__member=member)),
    }


def _mandat(member):
    mandat = SepaMandate.objects.filter(member=member).first()
    if mandat is None:
        return None
    return {
        "referenz": mandat.referenz,
        "iban": mandat.iban,
        "kontoinhaber": mandat.kontoinhaber or f"{member.vorname} {member.nachname}",
        "erteilt_am": mandat.erteilt_am,
        "status": mandat.get_status_display(),
        "widerrufen_am": mandat.widerrufen_am,
    }


def datenauskunft(member):
    """Vollständige Auskunft nach Art. 15 DSGVO (maschinenlesbar)."""
    daten = personenbezogene_daten(member)
    daten["sepa_mandat"] = _mandat(member)
    return daten


def verarbeitungstaetigkeiten():
    """Verzeichnis der Verarbeitungstätigkeiten als Zeilen (PRD N1.4)."""
    return [
        {"kategorie": "Stammdaten", "zweck": "Mitgliederverwaltung, Kontakt", "felder": "Name, Geburtsdatum, Anschrift, E-Mail, Telefon", "rechtsgrundlage": "Vertrag (Art. 6 Abs. 1 lit. b)", "speicherfrist": "Mitgliedschaft + 2 Jahre"},
        {"kategorie": "Beitragsdaten", "zweck": "Beitragseinzug, Buchhaltung", "felder": "Beitragsposten, Zahlungen, Mahnstufen", "rechtsgrundlage": "Vertrag, rechtliche Verpflichtung (AO)", "speicherfrist": "10 Jahre (steuerlich)"},
        {"kategorie": "SEPA-Mandat", "zweck": "Lastschrift (bankseitig manuell)", "felder": "IBAN, Mandatsreferenz, Kontoinhaber", "rechtsgrundlage": "Einwilligung (Art. 6 Abs. 1 lit. a)", "speicherfrist": "Mandat + 2 Jahre nach Widerruf"},
        {"kategorie": "Spielbetrieb", "zweck": "Mannschaftsaufstellung, Turniere", "felder": "Einsätze, Brettergebnisse, Turnierteilnahmen", "rechtsgrundlage": "Vereinszweck (Art. 6 Abs. 1 lit. b)", "speicherfrist": "Mitgliedschaft + 2 Jahre"},
        {"kategorie": "Kommunikation", "zweck": "Rundbriefe", "felder": "E-Mail-Adresse, Opt-in-Status", "rechtsgrundlage": "Einwilligung (Art. 6 Abs. 1 lit. a)", "speicherfrist": "Bis Widerruf"},
        {"kategorie": "Protokolle", "zweck": "Nachweis von Änderungen und Zugriffen", "felder": "Benutzer, Zeitpunkt, geänderte Felder", "rechtsgrundlage": "Rechtliche Verpflichtung (Art. 32)", "speicherfrist": "mindestens 12 Monate"},
    ]


@transaction.atomic
def anonymisiere_member(member, *, benutzer=None):
    """Entfernt Kontaktdaten, behält Finanz- und Spielhistorie (PRD N1.3)."""
    vorher = f"{member.vorname} {member.nachname}"
    member.vorname = ANONYMISIERT_VORNAME
    member.nachname = ANONYMISIERT_NACHNAME
    member.geburtsdatum = None
    member.strasse = ""
    member.plz = ""
    member.ort = ""
    member.email = ""
    member.telefon = ""
    member.email_opt_in = False
    member.user = None
    member.anonymisiert_am = timezone.now()
    member.save()
    ChangeRequest.objects.filter(member=member).update(
        wunschwert="", kommentar="", status=ChangeRequest.Status.ABGELEHNT
    )
    AuditLog.objects.create(
        benutzer=benutzer,
        aktion="Mitglied anonymisiert",
        text=f"Kontaktdaten von „{vorher}“ (ID {member.pk}) nach Ablauf der Frist entfernt.",
        member=member,
    )
    return member


def anonymisierungs_kandidaten(*, heute=None, frist_tage=None):
    """Ausgetretene Mitglieder, deren Frist abgelaufen und die noch nicht anonymisiert sind."""
    heute = heute or timezone.localdate()
    grenze = heute - timedelta(days=frist_tage or ANONYMISIERUNGS_FRIST_TAGE)
    return Member.objects.filter(
        status=Member.Status.AUSGETRETEN,
        austrittsdatum__isnull=False,
        austrittsdatum__lte=grenze,
        anonymisiert_am__isnull=True,
    ).order_by("austrittsdatum")
