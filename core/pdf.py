"""PDF-Erzeugung für die Datenauskunft (PRD N1.2: „ein Klick → vollständiges PDF“).

Nutzt reportlab (reine Python-Abhängigkeit, läuft offline auf dem Vereinsserver).
"""

import io
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PRIMÄR = colors.HexColor("#2f5bea")
GOLD = colors.HexColor("#b4860b")
GRAU = colors.HexColor("#5b6478")
LINIE = colors.HexColor("#dfe4ee")
KOPF_HG = colors.HexColor("#eef2fd")


def _stile():
    basis = getSampleStyleSheet()
    return {
        "titel": ParagraphStyle("titel", parent=basis["Title"], fontSize=17, spaceAfter=2, textColor=PRIMÄR),
        "unter": ParagraphStyle("unter", parent=basis["Normal"], fontSize=9, textColor=GRAU, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=basis["Heading2"], fontSize=12.5, spaceBefore=12, spaceAfter=4, textColor=PRIMÄR),
        "text": ParagraphStyle("text", parent=basis["Normal"], fontSize=9.5, leading=13, alignment=TA_LEFT),
        "klein": ParagraphStyle("klein", parent=basis["Normal"], fontSize=8.5, leading=11, textColor=GRAU),
    }


def _wert(wert):
    if wert is None or wert == "":
        return "–"
    if isinstance(wert, Decimal):
        return f"{wert:.2f} €".replace(".", ",")
    if hasattr(wert, "strftime"):
        return wert.strftime("%d.%m.%Y")
    return str(wert)


def _tabelle(zeilen, breite, stile, kopf=None):
    daten = ([[Paragraph(f"<b>{spalte}</b>", stile["klein"]) for spalte in kopf]] if kopf else []) + [
        [Paragraph(str(zelle), stile["text"]) for zelle in zeile] for zeile in zeilen
    ]
    tabelle = Table(daten, colWidths=breite, repeatRows=1 if kopf else 0, hAlign="LEFT")
    befehle = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, LINIE),
    ]
    if kopf:
        befehle.append(("BACKGROUND", (0, 0), (-1, 0), KOPF_HG))
    tabelle.setStyle(TableStyle(befehle))
    return tabelle


def _datensatz_tabelle(paare, breite, stile, schluesselbreite=45 * mm):
    return _tabelle(paare, [schluesselbreite, breite - schluesselbreite], stile)


def _beitraege_abschnitt(daten, breite, stile):
    if not daten["beitraege"]:
        return [Paragraph("Keine Beitragsdaten gespeichert.", stile["text"])]
    zeilen = []
    for posten in daten["beitraege"]:
        zahlungen = ", ".join(
            f"{_wert(z['datum'])}: {_wert(z['betrag'])} ({z['art']})" for z in posten["zahlungen"]
        )
        zeilen.append(
            [
                _wert(posten["jahr"]),
                posten["kategorie"],
                _wert(posten["betrag"]),
                posten["status"],
                _wert(posten["faellig_am"]),
                str(posten["mahnstufe"]),
                zahlungen or "–",
            ]
        )
    return [
        _tabelle(
            zeilen,
            [13 * mm, 28 * mm, 19 * mm, 22 * mm, 24 * mm, 14 * mm, breite - 120 * mm],
            stile,
            kopf=["Jahr", "Kategorie", "Betrag", "Status", "Fällig", "Mahn.", "Zahlungen"],
        ),
        Spacer(1, 4),
        Paragraph(f"Summe erfasster Zahlungen: <b>{_wert(daten['zahlungen_gesamt'])}</b>", stile["klein"]),
    ]


def _mandat_abschnitt(daten, breite, stile):
    if not daten["sepa_mandat"]:
        return [Paragraph("Kein Mandat gespeichert.", stile["text"])]
    mandat = daten["sepa_mandat"]
    return [
        _datensatz_tabelle(
            [
                ["Mandatsreferenz", mandat["referenz"]],
                ["IBAN", mandat["iban"]],
                ["Kontoinhaber:in", _wert(mandat["kontoinhaber"])],
                ["Erteilt am / Status", f"{_wert(mandat['erteilt_am'])} · {mandat['status']}"],
                ["Widerrufen am", _wert(mandat["widerrufen_am"])],
            ],
            breite,
            stile,
        )
    ]


def _statusverlauf_abschnitt(daten, breite, stile):
    return [
        _tabelle(
            [
                [
                    _wert(wechsel["am"]),
                    f"{wechsel['von']} → {wechsel['nach']}",
                    _wert(wechsel["durch"]),
                    _wert(wechsel["notiz"]),
                ]
                for wechsel in daten["statusverlauf"]
            ],
            [30 * mm, 42 * mm, 34 * mm, breite - 106 * mm],
            stile,
            kopf=["Zeitpunkt", "Wechsel", "Geändert von", "Notiz"],
        )
    ]


def _spielbetrieb_abschnitt(daten, breite, stile):
    teile = []
    if daten["turnierteilnahmen"]:
        teile.append(
            _tabelle(
                [
                    [
                        _wert(teilnahme["datum"]),
                        teilnahme["turnier"],
                        _wert(teilnahme["twz"]),
                        "Ja" if teilnahme["startgeld_bezahlt"] else "Nein",
                    ]
                    for teilnahme in daten["turnierteilnahmen"]
                ],
                [26 * mm, breite - 82 * mm, 26 * mm, 30 * mm],
                stile,
                kopf=["Datum", "Turnier", "TWZ", "Startgeld"],
            )
        )
    if daten["mannschaftseinsaetze"]:
        if teile:
            teile.append(Spacer(1, 6))
        teile.append(
            _tabelle(
                [
                    [
                        _wert(einsatz["datum"]),
                        einsatz["spiel"],
                        str(einsatz["brett"]),
                        _wert(einsatz["ergebnis"]),
                    ]
                    for einsatz in daten["mannschaftseinsaetze"]
                ],
                [26 * mm, breite - 82 * mm, 20 * mm, 36 * mm],
                stile,
                kopf=["Datum", "Begegnung", "Brett", "Ergebnis"],
            )
        )
    return teile or [Paragraph("Keine Teilnahmen oder Einsätze gespeichert.", stile["text"])]


def _wuensche_abschnitt(daten, breite, stile):
    if not daten["aenderungswuensche"]:
        return [Paragraph("Keine Änderungswünsche erfasst.", stile["text"])]
    return [
        _tabelle(
            [
                [
                    wunsch["feld"],
                    _wert(wunsch["wunschwert"]),
                    wunsch["status"],
                    _wert(wunsch["eingereicht_am"]),
                    _wert(wunsch["kommentar"]),
                ]
                for wunsch in daten["aenderungswuensche"]
            ],
            [24 * mm, 42 * mm, 26 * mm, 26 * mm, breite - 118 * mm],
            stile,
            kopf=["Feld", "Wunschwert", "Status", "Eingereicht", "Kommentar"],
        )
    ]


def _protokoll_abschnitt(daten, breite, stile):
    return [
        _tabelle(
            [
                [
                    _wert(eintrag["zeitpunkt"]),
                    eintrag["aktion"],
                    _wert(eintrag["feld"]),
                    f"{_wert(eintrag['alt_wert'])} → {_wert(eintrag['neu_wert'])}",
                    _wert(eintrag["benutzer"]),
                ]
                for eintrag in daten["protokollierung"][:60]
            ],
            [28 * mm, 34 * mm, 22 * mm, 44 * mm, breite - 128 * mm],
            stile,
            kopf=["Zeitpunkt", "Aktion", "Feld", "Alt → Neu", "Benutzer"],
        )
    ]


def datenauskunft_pdf(member, daten):
    """Erzeugt das vollständige PDF (Art. 15 DSGVO) als Bytes."""
    puffer = io.BytesIO()
    doc = SimpleDocTemplate(
        puffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Datenauskunft {member.nachname}, {member.vorname}",
        author=getattr(settings, "CLUB_NAME", "Schachverein"),
    )
    stile = _stile()
    breit = doc.width
    stamm = daten["stammdaten"]

    # Abschnitte als (Titel, Inhalt) – leere Bereiche werden ausgelassen und
    # die Nummerierung läuft dadurch ohne Lücken.
    abschnitte = [
        (
            "Stammdaten",
            [
                _datensatz_tabelle(
                    [
                        ["Name", f"{_wert(stamm['vorname'])} {_wert(stamm['nachname'])}"],
                        ["Geburtsdatum", _wert(stamm["geburtsdatum"])],
                        ["Anschrift", f"{_wert(stamm['strasse'])}, {_wert(stamm['plz'])} {_wert(stamm['ort'])}"],
                        ["E-Mail / Telefon", f"{_wert(stamm['email'])} / {_wert(stamm['telefon'])}"],
                        ["Status / Kategorie", f"{stamm['status']} · {_wert(stamm['beitragskategorie'])}"],
                        ["Eintritt / Austritt", f"{_wert(stamm['eintrittsdatum'])} / {_wert(stamm['austrittsdatum'])}"],
                        ["Rundbrief-Opt-in", "Ja" if stamm["email_opt_in"] else "Nein"],
                        ["Benutzerkonto", _wert(stamm["benutzerkonto"])],
                        ["Anonymisiert am", _wert(stamm["anonymisiert_am"])],
                    ],
                    breit,
                    stile,
                )
            ],
        ),
        ("Beiträge und Zahlungen", _beitraege_abschnitt(daten, breit, stile)),
        ("SEPA-Mandat", _mandat_abschnitt(daten, breit, stile)),
    ]
    if daten["statusverlauf"]:
        abschnitte.append(("Statusverlauf der Mitgliedschaft", _statusverlauf_abschnitt(daten, breit, stile)))
    abschnitte.append(("Spielbetrieb", _spielbetrieb_abschnitt(daten, breit, stile)))
    abschnitte.append(("Änderungswünsche", _wuensche_abschnitt(daten, breit, stile)))
    if daten["protokollierung"]:
        abschnitte.append(("Protokollierung von Änderungen", _protokoll_abschnitt(daten, breit, stile)))

    inhalt = [
        Paragraph("Datenauskunft nach Art. 15 DSGVO", stile["titel"]),
        Paragraph(
            f"{getattr(settings, 'CLUB_NAME', 'Schachverein')} · "
            f"{getattr(settings, 'CLUB_CONTACT', '')} · erstellt am "
            f"{timezone.localtime():%d.%m.%Y %H:%M} Uhr",
            stile["unter"],
        ),
    ]
    for nummer, (titel, fliess) in enumerate(abschnitte, start=1):
        inhalt.append(KeepTogether([Paragraph(f"{nummer}. {titel}", stile["h2"]), fliess[0]]))
        inhalt.extend(fliess[1:])

    inhalt += [
        PageBreak(),
        Paragraph("Hinweise zur Verarbeitung", stile["h2"]),
        Paragraph(
            "Diese Auskunft enthält alle personenbezogenen Daten, die die Vereinsverwaltung zu dieser "
            "Person speichert. Rechtsgrundlagen und Speicherfristen sind im Verzeichnis der "
            "Verarbeitungstätigkeiten dokumentiert (Menü „System“ bzw. <i>/datenschutz/verzeichnis.csv</i>).",
            stile["text"],
        ),
        Spacer(1, 6),
        Paragraph(
            "Steuerlich aufbewahrungspflichtige Finanzdaten (Beiträge, Zahlungen, Mahnungen) bleiben auch "
            "nach einem Austritt für die gesetzliche Aufbewahrungsfrist gespeichert; die Kontaktdaten "
            "werden nach Ablauf der vereinbarten Frist automatisch anonymisiert.",
            stile["text"],
        ),
    ]

    doc.build(inhalt, onLaterPages=_fusszeile, onFirstPage=_fusszeile)
    return puffer.getvalue()


def _fusszeile(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRAU)
    canvas.drawString(
        20 * mm,
        12 * mm,
        f"{getattr(settings, 'CLUB_SHORT', 'Schachverein')} · Datenauskunft Art. 15 DSGVO · "
        f"Seite {doc.page}",
    )
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.6)
    canvas.line(20 * mm, 16 * mm, A4[0] - 18 * mm, 16 * mm)
    canvas.restoreState()
