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

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

#: Präfix im Chiffretext. Es macht die Verfahrensversion sichtbar und erlaubt
#: später eine Rotation, ohne die Spalte umzubauen.
V1_PRAEFIX = "v1:"

_HINWEIS = (
    "IBAN_FERNET_KEY bzw. IBAN_FERNET_KEYS fehlt. Die IBAN lässt sich weder speichern noch lesen. "
    "Schlüssel erzeugen mit: python -c \"from cryptography.fernet import "
    "Fernet; print(Fernet.generate_key().decode())\""
)


def schluessel_liste() -> list[Fernet]:
    """Liest die konfigurierten Fernet-Schlüssel aus den Settings.

    Unterstützt `IBAN_FERNET_KEYS` (kommagetrennte Liste oder Iterable) und
    Fallback auf `IBAN_FERNET_KEY`. Der erste Schlüssel ist stets der primäre
    Schlüssel für neue Verschlüsselungen.
    """
    keys_raw = getattr(settings, "IBAN_FERNET_KEYS", None)
    candidate_keys = []
    if keys_raw is not None:
        if isinstance(keys_raw, str):
            candidate_keys = [k.strip() for k in keys_raw.split(",") if k.strip()]
        elif isinstance(keys_raw, (list, tuple)):
            candidate_keys = [str(k).strip() for k in keys_raw if str(k).strip()]
        else:
            candidate_keys = [str(keys_raw).strip()]

    if not candidate_keys:
        single = getattr(settings, "IBAN_FERNET_KEY", None)
        if single is not None:
            if isinstance(single, str):
                single = single.strip()
            if single:
                candidate_keys = [single]

    if not candidate_keys:
        raise ImproperlyConfigured(_HINWEIS)

    fernets = []
    for k in candidate_keys:
        try:
            fernets.append(Fernet(k.encode() if isinstance(k, str) else k))
        except (TypeError, ValueError) as exc:
            raise ImproperlyConfigured(
                "IBAN_FERNET_KEY bzw. IBAN_FERNET_KEYS enthält einen ungültigen Fernet-Schlüssel. "
                + _HINWEIS
            ) from exc

    return fernets


def primaer_schluessel() -> Fernet:
    """Der primäre Fernet-Schlüssel (erster Schlüssel in der Liste)."""
    return schluessel_liste()[0]


def schluessel() -> MultiFernet:
    """MultiFernet-Instanz – verschlüsselt mit dem Primärschlüssel, entschlüsselt mit allen."""
    return MultiFernet(schluessel_liste())


def ist_chiffre(wert) -> bool:
    return isinstance(wert, str) and wert.startswith(V1_PRAEFIX)


def ist_primaer_verschluesselt(wert: str) -> bool:
    """Prüft, ob der Chiffretext bereits mit dem aktuellen Primärschlüssel verschlüsselt ist."""
    if not ist_chiffre(wert):
        return False
    token = wert[len(V1_PRAEFIX) :].encode()
    try:
        primaer_schluessel().decrypt(token)
        return True
    except InvalidToken:
        return False


def rotiere_chiffre(wert: str) -> str:
    """Rotiert einen Chiffretext auf den aktuellen Primärschlüssel."""
    if not wert:
        return ""
    if not ist_chiffre(wert):
        return verschluesseln(wert)
    token = wert[len(V1_PRAEFIX) :].encode()
    rotiert = schluessel().rotate(token).decode()
    return V1_PRAEFIX + rotiert


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
            "IBAN_FERNET_KEY bzw. IBAN_FERNET_KEYS passt nicht zu den gespeicherten IBAN-Daten. "
            "Falscher Schlüssel oder Schlüssel vertauscht – bitte "
            "Betriebsdoku (ADR-010) prüfen, nichts zurücksetzen."
        ) from exc
