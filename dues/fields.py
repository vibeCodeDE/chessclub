"""Eigenes Datenbankfeld für die verschlüsselte IBAN (ADR-010)."""

from django.db import models

from .crypto import entschluesseln, ist_chiffre, verschluesseln


class VerschluesseltesIbanField(models.CharField):
    """``CharField``, das die IBAN verschlüsselt ablegt und transparent liest.

    Im Speicher steht ausschließlich Chiffretext mit Versionspräfix; im
    Python-Objekt und im Formular steht immer Klartext, damit Prüfung
    (`IBAN_MUSTER`), Maskierung und Anzeige unverändert funktionieren.

    Hinweis: ``manage.py dumpdata`` schreibt den Feldwert im Klartext in die
    Ausgabe (die Formular-Vorlage braucht ihn). Für Backups wird `pg_dump`
    benutzt, dort bleibt der Chiffretext erhalten.
    """

    description = "IBAN, verschlüsselt gespeichert (ADR-010)"

    def __init__(self, *args, **kwargs):
        # Platz für „v1:" + Base64-Token; die IBAN selbst hat höchstens 34 Zeichen.
        kwargs.setdefault("max_length", 255)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        return entschluesseln(value)

    def to_python(self, value):
        # Zuweisungen und Formulareingaben sind Klartext – nichts entschlüsseln,
        # aber einen Chiffretext aus einer anderen Quelle (z. B. Import) auflösen.
        return entschluesseln(value) if ist_chiffre(value) else value

    def get_prep_value(self, value):
        if value in (None, ""):
            return ""
        return verschluesseln(value)
