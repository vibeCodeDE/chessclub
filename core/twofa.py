"""Zwei-Faktor-Anmeldung für die Vorstandschaft (PRD N1.6).

Bewusst ohne Zusatzpaket: RFC 6238 (TOTP) lässt sich mit der Standardbibliothek
umsetzen – kein Fremdcode, der geprüft werden müsste (DSGVO-Prinzip Datenminimierung).
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from django.conf import settings

#: Toleriert eine Zeitspanne von ±1 Schritt (30 s), damit leicht abweichende
#: Uhren auf Handys keinen Fehlversuch erzeugen.
FENSTER = 1
SCHRITT_SEKUNDEN = 30
STELLEN = 6


def neues_secret():
    """Bas32-Secret mit 160 Bit Entropie (empfohlene Länge für TOTP)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _normalisieren(secret):
    """Entfernt Padding/Leerzeichen und korrigiert Kleinschreibung."""
    return secret.replace(" ", "").upper().rstrip("=")


def code_erzeugen(secret, *, zeitpunkt=None, schritt=None):
    """Berechnet den TOTP-Code zu einem Zeitpunkt (Standard: jetzt)."""
    schritt = SCHRITT_SEKUNDEN if schritt is None else schritt
    zeitpunkt = time.time() if zeitpunkt is None else zeitpunkt
    zaehler = int(zeitpunkt // schritt)
    schluessel = base64.b32decode(_normalisieren(secret) + "=" * (-len(_normalisieren(secret)) % 8))
    nachricht = struct.pack(">Q", zaehler)
    digest = hmac.new(schluessel, nachricht, hashlib.sha1).digest()
    versatz = digest[-1] & 0x0F
    roh = struct.unpack(">I", digest[versatz : versatz + 4])[0] & 0x7FFFFFFF
    return str(roh % (10**STELLEN)).zfill(STELLEN)


def code_pruefen_schritt(secret, code, *, letzter_zeitschritt=None):
    """Prüft einen vom Nutzer eingegebenen Code (Toleranz ±1 Zeitfenster).

    Gibt bei Erfolg den gültigen Zeitschritt (int) zurück, sonst None.
    Replay-Schutz: Wurde der Code bereits im selben oder einem früheren
    Zeitschritt eingelöst (<= letzter_zeitschritt), wird er abgewiesen.
    """
    if not code:
        return None
    code = "".join(zeichen for zeichen in str(code) if zeichen.isdigit())
    if len(code) != STELLEN:
        return None
    jetzt = time.time()
    zaehler = int(jetzt // SCHRITT_SEKUNDEN)
    for abweichung in range(-FENSTER, FENSTER + 1):
        kandidat_schritt = zaehler + abweichung
        if letzter_zeitschritt is not None and kandidat_schritt <= letzter_zeitschritt:
            continue
        if hmac.compare_digest(
            code_erzeugen(secret, schritt=SCHRITT_SEKUNDEN, zeitpunkt=kandidat_schritt * SCHRITT_SEKUNDEN),
            code,
        ):
            return kandidat_schritt
    return None


def code_pruefen(secret, code, *, letzter_zeitschritt=None):
    """Prüft einen vom Nutzer eingegebenen Code (Toleranz ±1 Zeitfenster)."""
    return code_pruefen_schritt(secret, code, letzter_zeitschritt=letzter_zeitschritt) is not None


def otpauth_uri(secret, konto, aussteller=None):
    """Konfigurations-URI für Authenticator-Apps (wird als Text angezeigt)."""
    aussteller = quote(aussteller or getattr(settings, "CLUB_SHORT", "Schachverein"))
    konto = quote(konto)
    return (
        f"otpauth://totp/{aussteller}:{konto}?secret={_normalisieren(secret)}"
        f"&issuer={aussteller}&algorithm=SHA1&digits={STELLEN}&period={SCHRITT_SEKUNDEN}"
    )
