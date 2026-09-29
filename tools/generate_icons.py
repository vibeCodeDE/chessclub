"""Erzeugt die PWA-Icons als PNG (ohne Fremdbibliotheken, reine Standardbibliothek).

Motiv: dunkelblaues Feld mit gold-weißem Schachbrett und Königsspringer-Andeutung.
Aufruf:  python3 tools/generate_icons.py
"""

import pathlib
import struct
import zlib

HINTERGRUND = (13, 21, 38)       # #0d1526
HELL = (245, 247, 252)           # #f5f7fc
GOLD = (180, 134, 11)            # #b4860b

ZIEL = pathlib.Path(__file__).resolve().parent.parent / "static" / "icons"


def _png_schreiben(pfad, breite, hoehe, pixel):
    """Schreibt RGBA-Pixel als PNG."""
    roh = b"".join(b"\x00" + pixel(y) for y in range(hoehe))

    def chunk(typ, daten):
        return (
            struct.pack(">I", len(daten))
            + typ
            + daten
            + struct.pack(">I", zlib.crc32(typ + daten) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", breite, hoehe, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(roh, 9))
    png += chunk(b"IEND", b"")
    pfad.write_bytes(png)


def icon_erzeugen(groesse):
    rand = max(2, round(groesse * 0.06))
    feld = round((groesse - 2 * rand) * 0.72)
    start = (groesse - feld) // 2
    zelle = feld / 8

    def pixel(y):
        zeile = bytearray()
        for x in range(groesse):
            # Rahmen in Gold
            if x < rand or y < rand or x >= groesse - rand or y >= groesse - rand:
                farbe = GOLD if (x < rand or y < rand or x >= groesse - rand or y >= groesse - rand) else HINTERGRUND
                if rand <= x < groesse - rand and rand <= y < groesse - rand:
                    farbe = HINTERGRUND
            else:
                farbe = HINTERGRUND

            # Schachbrett
            if start <= x < start + feld and start <= y < start + feld:
                spalte = int((x - start) // zelle)
                reihe = int((y - start) // zelle)
                hell = (spalte + reihe) % 2 == 0
                if hell:
                    farbe = HELL if not (spalte == 0 and reihe == 0) else GOLD
            zeile += bytes((*farbe, 255))
        return bytes(zeile)

    return pixel


def main():
    ZIEL.mkdir(parents=True, exist_ok=True)
    for groesse in (192, 512):
        _png_schreiben(ZIEL / f"icon-{groesse}.png", groesse, groesse, icon_erzeugen(groesse))
        print(f"static/icons/icon-{groesse}.png")
    _png_schreiben(ZIEL / "apple-touch-icon.png", 180, 180, icon_erzeugen(180))
    print("static/icons/apple-touch-icon.png")
    _png_schreiben(ZIEL / "favicon.png", 32, 32, icon_erzeugen(32))
    print("static/icons/favicon.png")


if __name__ == "__main__":
    main()
