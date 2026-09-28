"""CSV-Export der Jahresbeiträge (PRD M2.5) — für Buchhaltung und Vorstand.

Der Export enthält bewusst **nur** Finanz- und Mahndaten: er wird weitergegeben,
und die Kontaktdaten eines Mitglieds stehen im Mahnbrief (Task 7), nicht in
einer Tabelle, die beim Bearbeiten durch die Hände geht. ``CSV_SPALTEN`` ist
deshalb die Erlaubnis: was nicht dort steht, darf nicht im Export stehen.

Diese Datei liefert Zeilen, keine HTTP-Antwort — der View entscheidet über
Dateiname und Header (Muster aus ``members.views.mitglieder_export``).
"""

from .models import Mahnung
from .services import posten_mit_status

# Reihenfolge ist Vertrag: der Inhaltstest in dues/tests/test_export.py prüft
# Kopf und Zellen gegen genau diese Liste.
CSV_SPALTEN = (
    "Jahr",
    "Nachname",
    "Vorname",
    "Kategorie",
    "Beitrag",
    "Bezahlt",
    "Offen",
    "Status",
    "Mahnungen",
    "1. Mahnung am",
    "2. Mahnung am",
)


def _betrag(wert):
    """Deutsches Zahlenformat für die Zelle — Excel mit deutscher Gebietsschema."""
    return f"{wert:.2f}".replace(".", ",")


def _mahn_datum(mahnungen, stufe):
    for mahnung in mahnungen:
        if mahnung.stufe == stufe:
            return mahnung.datum.isoformat()
    return ""


def beitragszeilen(jahr):
    """Alle Beitragsposten des Jahres als CSV-Zeilen (inklusive Kopfzeile).

    Anders als :func:`dues.mahnung.offene_posten` werden **alle** Posten
    ausgegeben, auch bezahlte: der Export ist die Jahresübersicht für die
    Buchhaltung, nicht die Mahnliste. Deshalb wird :func:`dues.mahnung.
    offene_posten` hier bewusst nicht aufgerufen — sie würde die bezahlten
    Posten samt ihrer Zahlungen wegfiltern. Sortierung und Zahlungsstand
    kommen unverändert aus :func:`dues.services.posten_mit_status`, damit der
    Export in derselben Reihenfolge steht wie die Postenliste.

    Die Mahnungen kommen in **einer** Abfrage für das ganze Jahr und werden
    über ``post_id`` indiziert: je Zeile kostet die Stufe damit keine
    Zusatzabfrage.
    """
    mahnungen_pro_post = {}
    for mahnung in Mahnung.objects.filter(post__jahr=jahr).order_by("stufe", "pk"):
        mahnungen_pro_post.setdefault(mahnung.post_id, []).append(mahnung)

    zeilen = [list(CSV_SPALTEN)]
    for post_zeile in posten_mit_status(jahr):
        post = post_zeile["post"]
        mahnungen = mahnungen_pro_post.get(post.pk, [])
        zeilen.append(
            [
                str(jahr),
                post.member.nachname,
                post.member.vorname,
                post.kategorie.bezeichnung,
                _betrag(post.betrag),
                _betrag(post_zeile["bezahlt"]),
                _betrag(post_zeile["offen"]),
                post_zeile["status_label"],
                str(len(mahnungen)),
                _mahn_datum(mahnungen, Mahnung.Stufe.MAHNUNG_1),
                _mahn_datum(mahnungen, Mahnung.Stufe.MAHNUNG_2),
            ]
        )
    return zeilen
