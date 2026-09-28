"""Die Software nimmt keinen Zahlungseingang vom Bankensystem an (PRD M2.3).

Der Einzug erfolgt bankseitig manuell per SEPA-Lastschrift; die App verwaltet
nur Mandat und Zahlungsstatus. Dieser Test ist die Absicherung der
T9-Acceptance „kein Bank-API-Call im Code" — er schlägt fehl, sobald in der
`dues`-App eine Netzwerkbibliothek oder ein Bank-SDK auftaucht.
"""

from pathlib import Path

from django.test import SimpleTestCase

import dues

VERBOTENE_IMPORTS = (
    "requests",
    "httpx",
    "urllib.request",
    "urllib3",
    "http.client",
    "socket",
    "django_paypal",
    "pysepa",
)


class KeineBankApiTests(SimpleTestCase):
    def test_dues_importiert_keine_netzwerkbibliothek(self):
        quelle = Path(dues.__file__).parent
        treffer = []

        for datei in sorted(quelle.rglob("*.py")):
            text = datei.read_text(encoding="utf-8")
            for verboten in VERBOTENE_IMPORTS:
                if f"import {verboten}" in text:
                    treffer.append(f"{datei.name}: {verboten}")

        self.assertEqual(treffer, [], f"Netzwerkzugriff in der dues-App: {treffer}")

    def test_kein_bank_endpunkt_in_den_settings(self):
        """Ohne Bank-Endpunkt in den Settings gibt es auch nichts anzurufen."""
        from django.conf import settings

        self.assertEqual(
            [name for name in dir(settings) if "BANK" in name.upper() or "ENDPOINT" in name.upper()],
            [],
        )
