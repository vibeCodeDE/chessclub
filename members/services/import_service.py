"""CSV-Import-Service für Mitgliederstammdaten (PRD S1.7, ADR-020).

Reine Funktionen ohne HTTP-Kontext für Parsing, Validierung und sichere Übernahme.
"""

import csv
import io
import re
from datetime import date, datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.models import AuditLog
from dues.models import IBAN_MUSTER, FeeCategory, SepaMandate, normalize_iban
from members.models import Member

HEADER_MAPPING = {
    "vorname": "vorname",
    "nachname": "nachname",
    "email": "email",
    "e-mail": "email",
    "mail": "email",
    "telefon": "telefon",
    "tel": "telefon",
    "handy": "telefon",
    "geburtsdatum": "geburtsdatum",
    "geburtstag": "geburtsdatum",
    "geb_datum": "geburtsdatum",
    "strasse": "strasse",
    "straße": "strasse",
    "strasse_nr": "strasse",
    "straße_nr": "strasse",
    "straße/nr.": "strasse",
    "strasse/nr.": "strasse",
    "plz": "plz",
    "postleitzahl": "plz",
    "ort": "ort",
    "wohnort": "ort",
    "stadt": "ort",
    "eintrittsdatum": "eintrittsdatum",
    "eintritt": "eintrittsdatum",
    "beitritt": "eintrittsdatum",
    "austrittsdatum": "austrittsdatum",
    "austritt": "austrittsdatum",
    "status": "status",
    "mitgliedsstatus": "status",
    "beitragskategorie": "beitragskategorie",
    "kategorie": "beitragskategorie",
    "tarif": "beitragskategorie",
    "iban": "iban",
    "kontoinhaber": "kontoinhaber",
    "inhaber": "kontoinhaber",
    "dwz": "dwz",
    "dwz_index": "dwz_index",
    "fide_id": "fide_id",
    "fideid": "fide_id",
    "zps_nummer": "zps_nummer",
    "zps": "zps_nummer",
    "pkz": "pkz",
    "spielberechtigung": "spielberechtigung",
}


def _decode_content(data: str | bytes | io.IOBase) -> str:
    """Dekodiert Rohdaten oder Datei-Objekte zuverlässig nach UTF-8 (mit Fallback auf Latin-1)."""
    if isinstance(data, str):
        return data
    if hasattr(data, "read"):
        raw = data.read()
    else:
        raw = data

    if isinstance(raw, str):
        return raw

    for enc in ["utf-8-sig", "utf-8", "windows-1252", "latin-1"]:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def parse_members_csv(content: str | bytes | io.IOBase) -> list[dict[str, str]]:
    """Liest eine CSV-Zeichenkette oder Datei ein und normalisiert Header."""
    text = _decode_content(content).strip()
    if not text:
        return []

    # Bestimme Trennzeichen anhand der ersten Zeile
    erste_zeile = text.splitlines()[0]
    delimiter = ";" if erste_zeile.count(";") >= erste_zeile.count(",") else ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        raw_headers = next(reader)
    except StopIteration:
        return []

    # Header normalisieren
    normalized_headers = []
    for h in raw_headers:
        cleaned = re.sub(r"\s+", "_", h.strip().lower())
        key = HEADER_MAPPING.get(cleaned, cleaned)
        normalized_headers.append(key)

    rows = []
    for row_idx, row in enumerate(reader, start=2):
        if not any(row):  # Leere Zeile überspringen
            continue
        row_dict = {}
        for col_idx, val in enumerate(row):
            if col_idx < len(normalized_headers):
                field_key = normalized_headers[col_idx]
                row_dict[field_key] = val.strip()
        row_dict["zeilennummer"] = str(row_idx)
        rows.append(row_dict)

    return rows


def _parse_date(val: str | None) -> date | None:
    """Parst ein Datum aus verschiedenen Standardformaten."""
    if not val:
        return None
    val = val.strip()
    if not val:
        return None

    formate = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d.%m.%y"]
    for fmt in formate:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Ungültiges Datumsformat: '{val}'. Erwartet wird DD.MM.YYYY oder YYYY-MM-DD.")


def validate_members_import(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Validiert geparste Zeilen und bereitet sie für die Speicherung vor."""
    valid_rows = []
    invalid_rows = []
    warnings = []

    kategorien_map = {k.name.strip().lower(): k for k in FeeCategory.objects.all()}

    for row in rows:
        zeile_nr = row.get("zeilennummer", "?")
        fehler = []
        daten = {}

        # 1. Pflichtfelder Vorname / Nachname
        vorname = row.get("vorname", "").strip()
        nachname = row.get("nachname", "").strip()
        if not vorname:
            fehler.append("Vorname fehlt.")
        if not nachname:
            fehler.append("Nachname fehlt.")
        daten["vorname"] = vorname
        daten["nachname"] = nachname

        # 2. Eintrittsdatum
        eintritt_str = row.get("eintrittsdatum", "")
        if eintritt_str:
            try:
                daten["eintrittsdatum"] = _parse_date(eintritt_str)
            except ValueError as e:
                fehler.append(str(e))
        else:
            # Fallback: Heute
            daten["eintrittsdatum"] = timezone.localdate()

        # 3. Geburtsdatum
        geb_str = row.get("geburtsdatum", "")
        if geb_str:
            try:
                daten["geburtsdatum"] = _parse_date(geb_str)
            except ValueError as e:
                fehler.append(str(e))
        else:
            daten["geburtsdatum"] = None

        # 4. Austrittsdatum
        austritt_str = row.get("austrittsdatum", "")
        if austritt_str:
            try:
                daten["austrittsdatum"] = _parse_date(austritt_str)
            except ValueError as e:
                fehler.append(str(e))
        else:
            daten["austrittsdatum"] = None

        # 5. Status
        raw_status = row.get("status", "").strip().lower()
        if not raw_status:
            daten["status"] = Member.Status.AKTIV
        elif raw_status in {"aktiv", "active"}:
            daten["status"] = Member.Status.AKTIV
        elif raw_status in {"passiv", "passive"}:
            daten["status"] = Member.Status.PASSIV
        elif raw_status in {"ausgetreten", "resigned"}:
            daten["status"] = Member.Status.AUSGETRETEN
        else:
            fehler.append(f"Unbekannter Status '{raw_status}'. Gültig: aktiv, passiv, ausgetreten.")

        # 6. Beitragskategorie
        kat_name = row.get("beitragskategorie", "").strip()
        daten["beitragskategorie"] = None
        if kat_name:
            kat_obj = kategorien_map.get(kat_name.lower())
            if kat_obj:
                daten["beitragskategorie"] = kat_obj
            else:
                warnings.append(
                    f"Zeile {zeile_nr}: Beitragskategorie '{kat_name}' nicht gefunden. Mitglied wird vorerst ohne Kategorie angelegt."
                )

        # 7. Kontaktdaten & Anschrift
        daten["email"] = row.get("email", "").strip()
        daten["telefon"] = row.get("telefon", "").strip()
        daten["strasse"] = row.get("strasse", "").strip()
        daten["plz"] = row.get("plz", "").strip()
        daten["ort"] = row.get("ort", "").strip()

        # 8. Verbands- und Wertungsdaten
        daten["zps_nummer"] = row.get("zps_nummer", "").strip()
        daten["pkz"] = row.get("pkz", "").strip()

        for num_field in ["dwz", "dwz_index", "fide_id"]:
            num_val = row.get(num_field, "").strip()
            if num_val:
                try:
                    daten[num_field] = int(num_val)
                except ValueError:
                    fehler.append(f"{num_field.upper()} muss eine Ganzzahl sein (Wert: '{num_val}').")
            else:
                daten[num_field] = None

        raw_sb = row.get("spielberechtigung", "").strip().lower()
        if raw_sb in {"zweit", "gast"}:
            daten["spielberechtigung"] = Member.Spielberechtigung.ZWEIT
        else:
            daten["spielberechtigung"] = Member.Spielberechtigung.ERST

        # 9. SEPA & Bankverbindung
        raw_iban = row.get("iban", "").strip()
        daten["iban"] = ""
        daten["kontoinhaber"] = row.get("kontoinhaber", "").strip()
        if raw_iban:
            normalized = normalize_iban(raw_iban)
            if not IBAN_MUSTER.match(normalized):
                fehler.append(f"Ungültige IBAN '{raw_iban}'.")
            else:
                daten["iban"] = normalized
                if not daten["kontoinhaber"]:
                    daten["kontoinhaber"] = f"{vorname} {nachname}"

        daten["zeilennummer"] = zeile_nr

        if fehler:
            invalid_rows.append({"zeile": zeile_nr, "fehler": fehler, "rohdaten": row})
        else:
            valid_rows.append(daten)

    return {
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "valid_count": len(valid_rows),
        "error_count": len(invalid_rows),
        "warning_count": len(warnings),
        "warnings": warnings,
    }


def execute_members_import(
    valid_rows: list[dict[str, Any]],
    actor: Any | None = None,
) -> dict[str, Any]:
    """Übernimmt die validierten Zeilen atomar in die Datenbank."""
    created_members = []
    created_mandates_count = 0

    with transaction.atomic():
        for daten in valid_rows:
            member = Member(
                vorname=daten["vorname"],
                nachname=daten["nachname"],
                email=daten["email"],
                telefon=daten["telefon"],
                strasse=daten["strasse"],
                plz=daten["plz"],
                ort=daten["ort"],
                geburtsdatum=daten["geburtsdatum"],
                eintrittsdatum=daten["eintrittsdatum"],
                austrittsdatum=daten["austrittsdatum"],
                status=daten["status"],
                beitragskategorie=daten["beitragskategorie"],
                zps_nummer=daten["zps_nummer"],
                pkz=daten["pkz"],
                dwz=daten["dwz"],
                dwz_index=daten["dwz_index"],
                fide_id=daten["fide_id"],
                spielberechtigung=daten["spielberechtigung"],
            )
            member.save()
            created_members.append(member)

            # Wenn IBAN vorhanden, SEPA-Mandat anlegen
            iban = daten.get("iban")
            if iban:
                heute_tag = timezone.localdate().strftime("%Y%m%d")
                referenz = f"MANDAT-{member.pk}-{heute_tag}"
                mandat = SepaMandate(
                    member=member,
                    referenz=referenz,
                    iban=iban,
                    kontoinhaber=daten.get("kontoinhaber", f"{member.vorname} {member.nachname}"),
                    erteilt_am=daten["eintrittsdatum"] or timezone.localdate(),
                    status=SepaMandate.Status.AKTIV,
                )
                mandat.save()
                created_mandates_count += 1

        # AuditLog erfassen
        if created_members:
            AuditLog.objects.create(
                benutzer=actor,
                aktion="Mitglieder-Import (CSV)",
                text=f"{len(created_members)} Mitglieder und {created_mandates_count} SEPA-Mandate importiert.",
            )

    return {
        "created_members": len(created_members),
        "created_mandates": created_mandates_count,
        "members": created_members,
    }
