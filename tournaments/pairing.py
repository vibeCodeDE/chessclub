"""Schweizer Paarung und Bye-Behandlung (PRD S3.4).

Bewusst eine kleine, testbare Eigenimplementierung für Vereinsgrößen
(≤ 64 Teilnehmer) statt einer exotischen Fremdbibliothek:
  * gleiche Punktzahl wird bevorzugt gegeneinander gepaart,
  * bereits gespielte Paarungen werden vermieden,
  * wer noch keine Farbhistorie hat, bekommt Weiß/Schwarz abwechselnd,
  * ungerade Teilnehmerzahl → Bye (1 Punkt) für die schwächste noch freie Person.
"""

from collections import defaultdict

from .models import Pairing, TournamentRound


def _paarungsschluessel(a, b):
    return frozenset((a.pk, b.pk))


def bisherige_gegner(tournament):
    """Menge aller Paarungen (als pk-Paare), damit niemand doppelt spielt."""
    gespielt = set()
    for paarung in Pairing.objects.filter(runde__tournament=tournament):
        if paarung.weiss_id and paarung.schwarz_id:
            gespielt.add(_paarungsschluessel(paarung.weiss, paarung.schwarz))
    return gespielt


def farben_bilanz(tournament):
    """Anzahl Weiß-Einsätze je Person (Farbausgleich)."""
    weiss = defaultdict(int)
    for paarung in Pairing.objects.filter(runde__tournament=tournament):
        if paarung.weiss_id:
            weiss[paarung.weiss_id] += 1
    return weiss


def generate_round(tournament):
    """Erzeugt die nächste Runde mit Paarungen. Idempotent je Rundennummer."""
    from .models import teilnehmer_stand

    letzte = tournament.runden.order_by("-nummer").first()
    nummer = (letzte.nummer if letzte else 0) + 1
    if nummer > tournament.runden_anzahl:
        return None, "Alle geplanten Runden sind bereits angelegt."

    teilnehmer = list(tournament.teilnehmer.all())
    if len(teilnehmer) < 2:
        return None, "Für eine Paarung sind mindestens zwei Teilnehmer:innen nötig."

    gespielte = bisherige_gegner(tournament)
    weiss_zaehler = farben_bilanz(tournament)

    stand = teilnehmer_stand(tournament)
    rang = {p.pk: index for index, p in enumerate(stand)}

    offen = list(stand)
    bye = None
    if len(offen) % 2 == 1:
        # Bye an die am schlechtesten platzierte Person, die noch keins hatte
        hatte_bye = {
            p.pk
            for p in teilnehmer
            if Pairing.objects.filter(ergebnis=Pairing.Ergebnis.BYE)
            .filter(weiss=p)
            .exists()
        }
        kandidaten = [p for p in reversed(offen) if p.pk not in hatte_bye]
        bye = kandidaten[0] if kandidaten else offen[-1]
        offen.remove(bye)

    paare = []
    freie = list(offen)
    while freie:
        spieler = freie.pop(0)
        gegner = None
        for kandidat in freie:
            if _paarungsschluessel(spieler, kandidat) not in gespielte:
                gegner = kandidat
                break
        if gegner is None:
            # Notfall: keine ausweichbare Paarung mehr (kleine Felder)
            gegner = freie[0]
        freie.remove(gegner)
        paare.append((spieler, gegner))

    runde = TournamentRound.objects.create(tournament=tournament, nummer=nummer)
    brett = 1
    for a, b in paare:
        # Farbe: wer seltener Weiß hatte, spielt Weiß
        a_weiss = weiss_zaehler[a.pk] <= weiss_zaehler[b.pk]
        weiss, schwarz = (a, b) if a_weiss else (b, a)
        weiss_zaehler[weiss.pk] += 1
        Pairing.objects.create(runde=runde, brett=brett, weiss=weiss, schwarz=schwarz)
        brett += 1
    if bye is not None:
        Pairing.objects.create(runde=runde, brett=brett, weiss=bye, schwarz=None, ergebnis=Pairing.Ergebnis.BYE)

    if tournament.status != tournament.Status.BEENDET:
        tournament.status = tournament.Status.LAUFEND
        tournament.save(update_fields=["status"])
    return runde, None


def turnier_abschliessen(tournament):
    tournament.status = tournament.Status.BEENDET
    tournament.save(update_fields=["status"])
    return tournament
