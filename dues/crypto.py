"""Verschlüsselung der IBAN (ADR-010).

Die IBAN liegt **nicht** im Klartext in der Datenbank, sondern als
authifiziert verschlüsselter Chiffretext (Fernet: AES-CBC + HMAC). Der
Schlüssel kommt aus der Umgebung und steht damit weder in der Datenbank noch
im Repository.

Was das **nicht** schützt: jemand mit Shell- oder Code-Zugriff auf den
Container kann die IBAN entschlüsseln, weil Django sie zum Anzeigen
braucht. Geschützt sind gestohlene Dumps, Backups und Datenträger.

Bewusst nicht abgedeckt: Suche, Sortierung und Eindeutigkeitsprüfung auf der
IBAN. Ein Chiffretext ist nicht wiederholbar, `filter(iban=...)` findet also
nichts. Für solche Fälle wäre ein Blind-Index (HMAC mit einem zweiten
Schlüssel) nötig — siehe ADR-010, Abschnitt „Nicht Bestandteil“.
"""

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

#: Präfix im Chiffretext. Es macht die Verfahrensversion sichtbar und erlaubt
#: später eine Rotation, ohne die Spalte umzubauen.
V1_PRAEFIX = "v1:"

_HINWEIS = (
    "IBAN_FERNET_KEY fehlt. Die IBAN lässt sich weder speichern noch lesen. "
    "Schlüssel erzeugen mit: python -c \"from cryptography.fernet import "
    "Fernet; print(Fernet.generate_key().decode())\""
)


def schluessel() -> Fernet:
    """Der Fernet-Schlüssel aus der Umgebung – ohne Schlüssel kein Start."""
    roh = getattr(settings, "IBAN_FERNET_KEY", "") or ""
    if isinstance(roh, str):
        roh = roh.strip()
    if not roh:
        raise ImproperlyConfigured(_HINWEIS)
    try:
        return Fernet(roh.encode() if isinstance(roh, str) else roh)
    except (TypeError, ValueError) as exc:  # ungültiger Schlüssel
        raise ImproperlyConfigured(
            "IBAN_FERNET_KEY ist kein gültiger Fernet-Schlüssel. "
            + _HINWEIS
        ) from exc


def ist_chiffre(wert) -> bool:
    return isinstance(wert, str) and wert.startswith(V1_PRAEFIX)


def verschluesseln(klartext: str) -> str:
    """Klartext → Chiffretext mit Versionspräfix. Bereits Chiffre bleibt so."""
    if not klartext:
        return ""
    if ist_chiffre(klartext):
        return klartext
    return V1_PRAEFIX + schluessel().encrypt(str(klartext).encode()).decode()


def entschluesseln(wert: str) -> str:
    """Chiffretext → Klartext. Klartext (Altbestand, Fixtures) bleibt unberührt."""
    if not wert:
        return ""
    if not ist_chiffre(wert):
        return wert
    try:
        return schluessel().decrypt(wert[len(V1_PRAEFIX) :].encode()).decode()
    except InvalidToken as exc:
        raise ImproperlyConfigured(
            "IBAN_FERNET_KEY passt nicht zu den gespeicherten IBAN-Daten. "
            "Falscher Schlüssel oder Schlüssel vertauscht – bitte "
            "Betriebsdoku (ADR-010) prüfen, nichts zurücksetzen."
        ) from exc
