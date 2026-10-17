"""Fachservice für die DSB- und DWZ-Synchronisation (ADR-016 / PRD K3.6).

Reine Funktionen ohne HTTP-Kontext:
- Abruf der Vereinsmitgliederliste vom offiziellen DSB-Wertungsportal
- Ratenbegrenzung & serverseitiges Caching (max. 1× täglich)
- Diskrepanzerkennung (Drift Detection)
- Idempotente Übernahme von DWZ, Index und Verbandskennungen
- AuditLog-Protokollierung
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from core.models import AuditLog
from members.models import Member

logger = logging.getLogger(__name__)


class DSBSyncError(Exception):
    """Basisklasse für Fehler beim DSB-Abgleich."""


class DSBConfigError(DSBSyncError):
    """Fehlende oder ungültige Konfiguration (VKZ oder API-Token)."""


class DSBNetworkError(DSBSyncError):
    """Netzwerk-, HTTP- oder Timeout-Fehler beim Abruf."""


class DSBParseError(DSBSyncError):
    """Ungültiges JSON oder unerwartete Datenstruktur."""


@dataclass
class DriftReport:
    """Ergebnis der Drift-Erkennung zwischen Vereins- und Verbandsdaten."""

    vkz: str
    stand: str
    from_cache: bool
    total_verein: int
    total_verband: int
    verein: str = ""
    fehlt_im_verband: list[Member] = field(default_factory=list)
    fehlt_im_verein: list[dict[str, Any]] = field(default_factory=list)
    dwz_abweichungen: list[dict[str, Any]] = field(default_factory=list)
    status_abweichungen: list[dict[str, Any]] = field(default_factory=list)
    synchrone_mitglieder: list[dict[str, Any]] = field(default_factory=list)

    @property
    def hat_abweichungen(self) -> bool:
        return bool(
            self.fehlt_im_verband
            or self.fehlt_im_verein
            or self.dwz_abweichungen
            or self.status_abweichungen
        )

    @property
    def anzahl_abweichungen(self) -> int:
        return (
            len(self.fehlt_im_verband)
            + len(self.fehlt_im_verein)
            + len(self.dwz_abweichungen)
            + len(self.status_abweichungen)
        )


def _get_config(
    vkz: str | None = None,
    token: str | None = None,
    base_url: str | None = None,
) -> tuple[str, str, str]:
    resolved_vkz = (vkz or getattr(settings, "DSB_VKZ", "")).strip()
    resolved_token = (token or getattr(settings, "DSB_API_TOKEN", "")).strip()
    resolved_url = (
        base_url
        or getattr(
            settings,
            "DSB_API_BASE_URL",
            "https://www.schachbund.de/wertungsportal-api/vereinsliste",
        )
    ).strip()

    if not resolved_vkz or not resolved_token:
        raise DSBConfigError(
            "Vereinskennziffer (DSB_VKZ) und API-Token (DSB_API_TOKEN) müssen konfiguriert sein."
        )
    return resolved_vkz, resolved_token, resolved_url


def fetch_dsb_vereinsliste(
    vkz: str | None = None,
    token: str | None = None,
    base_url: str | None = None,
    force: bool = False,
    timeout: int = 30,
) -> tuple[dict[str, Any], bool]:
    """Ruft die Mitgliederliste des Vereins über die offizielle JSON-Schnittstelle ab.

    Gibt ein Tuple ``(daten, from_cache)`` zurück.
    Beachtet die Ratenbegrenzung: Daten werden serverseitig gecacht (Default 24h, ADR-016).
    Wird ``force=True`` übergeben, wird der Cache umgangen und aktualisiert.
    """
    resolved_vkz, resolved_token, resolved_url = _get_config(vkz, token, base_url)
    cache_key = f"dsb_vereinsliste_{resolved_vkz}"

    if not force:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached, True

    query = urllib.parse.urlencode({"token": resolved_token, "vkz": resolved_vkz})
    request_url = f"{resolved_url}?{query}"

    req = urllib.request.Request(
        request_url,
        headers={
            "User-Agent": f"Vereinsliste/1.0 (VKZ {resolved_vkz})",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            if status_code != 200:
                raise DSBNetworkError(f"DSB-Schnittstelle lieferte HTTP-Status {status_code}.")
            raw_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise DSBNetworkError(f"HTTP-Fehler {exc.code} beim Abruf der DSB-Schnittstelle: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise DSBNetworkError(f"Verbindungsfehler zur DSB-Schnittstelle: {exc.reason}") from exc
    except Exception as exc:
        raise DSBNetworkError(f"Unerwarteter Fehler beim Abruf der DSB-Schnittstelle: {exc}") from exc

    parsed = parse_dsb_data(raw_body, vkz=resolved_vkz)

    cache_timeout = getattr(settings, "DSB_CACHE_TIMEOUT", 86400)
    cache.set(cache_key, parsed, timeout=cache_timeout)

    return parsed, False


def parse_dsb_data(raw_data: Any, vkz: str = "") -> dict[str, Any]:
    """Validiert und normalisiert die JSON-Rückgabe des DSB-Wertungsportals."""
    if isinstance(raw_data, str):
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as exc:
            raise DSBParseError(f"Ungültiges JSON von der DSB-Schnittstelle: {exc}") from exc
    elif isinstance(raw_data, dict):
        data = raw_data
    elif isinstance(raw_data, list):
        data = {"spieler": raw_data}
    else:
        raise DSBParseError("Unerwarteter Datentyp der DSB-Rückgabe.")

    # Unterstützt sowohl {"spieler": [...]} als auch {"members": [...]}
    raw_spieler = data.get("spieler")
    if raw_spieler is None:
        raw_spieler = data.get("members", [])

    if not isinstance(raw_spieler, list):
        raise DSBParseError("DSB-Rückgabe enthält kein gültiges 'spieler'-Array.")

    stand = str(data.get("stand") or timezone.now().isoformat())
    resp_vkz = str(data.get("vkz") or vkz).strip()
    resp_verein = str(data.get("verein") or "").strip()

    normalized_spieler = []
    for s in raw_spieler:
        if not isinstance(s, dict):
            continue

        pkz = str(s.get("id") or s.get("pkz") or "").strip()
        pass_nr = str(s.get("mitgliedsnummer") or s.get("pass") or s.get("mitgliedsnr") or "").strip()
        zps = str(s.get("zps") or s.get("zps_nummer") or "").strip()
        if not zps and pass_nr and resp_vkz:
            zps = f"{resp_vkz}-{pass_nr.zfill(3)}"
        elif not zps and pass_nr:
            zps = pass_nr

        raw_dwz = s.get("dwz")
        dwz_val = None
        if raw_dwz is not None and str(raw_dwz).strip() not in ("", "0", "-"):
            try:
                dwz_val = int(raw_dwz)
            except (ValueError, TypeError):
                dwz_val = None

        raw_index = s.get("dwzIndex") or s.get("dwz_index") or s.get("index")
        index_val = None
        if raw_index is not None and str(raw_index).strip() not in ("", "-"):
            try:
                index_val = int(raw_index)
            except (ValueError, TypeError):
                index_val = None

        raw_fide = s.get("fideId") or s.get("fide_id")
        fide_val = None
        if raw_fide is not None and str(raw_fide).strip() not in ("", "0", "-"):
            try:
                fide_val = int(raw_fide)
            except (ValueError, TypeError):
                fide_val = None

        # Status: "P" im DSB bedeutet Passiv, sonst Aktiv
        raw_status = str(s.get("status") or "").strip().upper()
        verb_status = Member.Status.PASSIV if raw_status == "P" else Member.Status.AKTIV

        normalized_spieler.append(
            {
                "pkz": pkz,
                "zps": zps,
                "mitgliedsnummer": pass_nr,
                "nachname": str(s.get("nachname") or "").strip(),
                "vorname": str(s.get("vorname") or "").strip(),
                "geburtsjahr": str(s.get("geburtsjahr") or "").strip(),
                "dwz": dwz_val,
                "dwz_index": index_val,
                "fide_id": fide_val,
                "elo": int(s["elo"]) if s.get("elo") else None,
                "status": verb_status,
                "nation": str(s.get("nation") or "").strip(),
                "titel": str(s.get("titel") or "").strip(),
                "raw": s,
            }
        )

    return {
        "vkz": resp_vkz,
        "verein": resp_verein,
        "stand": stand,
        "spieler": normalized_spieler,
    }


def detect_drift(
    members_qs=None,
    dsb_data: dict[str, Any] | None = None,
    from_cache: bool = False,
) -> DriftReport:
    """Gleicht den Vereinsbestand mit den DSB-Verbandsdaten ab.

    Erkennt:
    - Mitglieder, die im Verein aktiv sind, aber in der Verbandsliste fehlen
    - Spieler im Verband, die im Verein fehlen oder bereits als ausgetreten geführt werden
    - Status-Abweichungen (z. B. Verein aktiv, Verband passiv)
    - DWZ- und DWZ-Index-Abweichungen
    - Vollständig synchrone Mitglieder
    """
    if members_qs is None:
        members_qs = Member.objects.all()

    members = list(members_qs)
    if dsb_data is None:
        dsb_data = {"vkz": "", "stand": "", "spieler": []}

    spieler_list = dsb_data.get("spieler", [])
    vkz = str(dsb_data.get("vkz", ""))
    stand = str(dsb_data.get("stand", ""))
    verein = str(dsb_data.get("verein", ""))

    report = DriftReport(
        vkz=vkz,
        stand=stand,
        from_cache=from_cache,
        total_verein=len(members),
        total_verband=len(spieler_list),
        verein=verein,
    )

    # Indizierung der Vereinsmitglieder zur schnellen Zuordnung
    by_pkz: dict[str, Member] = {}
    by_zps: dict[str, Member] = {}
    by_name: dict[tuple[str, str], list[Member]] = {}

    for m in members:
        if m.pkz:
            by_pkz[m.pkz.strip()] = m
        if m.zps_nummer:
            by_zps[m.zps_nummer.strip()] = m
        name_key = (m.nachname.strip().lower(), m.vorname.strip().lower())
        by_name.setdefault(name_key, []).append(m)

    matched_members: set[int] = set()
    matched_players_indices: set[int] = set()

    # 1. Matching-Durchlauf
    for idx, sp in enumerate(spieler_list):
        matched_member: Member | None = None

        if sp["pkz"] and sp["pkz"] in by_pkz:
            matched_member = by_pkz[sp["pkz"]]
        elif sp["zps"] and sp["zps"] in by_zps:
            matched_member = by_zps[sp["zps"]]
        else:
            name_key = (sp["nachname"].lower(), sp["vorname"].lower())
            candidates = by_name.get(name_key, [])
            # Bevorzuge aktives oder passives Mitglied vor ausgetretenem
            for c in candidates:
                if c.id not in matched_members:
                    matched_member = c
                    break

        if matched_member:
            matched_members.add(matched_member.id)
            matched_players_indices.add(idx)

            # Abgleich prüfen
            dwz_gekuppelt = (matched_member.dwz == sp["dwz"]) and (
                matched_member.dwz_index == sp["dwz_index"]
            )
            status_gekuppelt = (
                matched_member.status == sp["status"]
                or (
                    matched_member.status in (Member.Status.AKTIV, Member.Status.PASSIV)
                    and sp["status"] in (Member.Status.AKTIV, Member.Status.PASSIV)
                    and matched_member.status == sp["status"]
                )
            )

            # Wenn das Mitglied im Verein bereits ausgetreten ist, gilt das als Statusabweichung
            if matched_member.status == Member.Status.AUSGETRETEN:
                report.status_abweichungen.append(
                    {
                        "member": matched_member,
                        "dsb_player": sp,
                        "status_verein": matched_member.get_status_display(),
                        "status_verband": "Im Verband geführt (Aktiv/Passiv)",
                    }
                )
            elif not status_gekuppelt:
                report.status_abweichungen.append(
                    {
                        "member": matched_member,
                        "dsb_player": sp,
                        "status_verein": matched_member.get_status_display(),
                        "status_verband": (
                            "Passiv"
                            if sp["status"] == Member.Status.PASSIV
                            else "Aktiv"
                        ),
                    }
                )

            if not dwz_gekuppelt:
                report.dwz_abweichungen.append(
                    {
                        "member": matched_member,
                        "dsb_player": sp,
                        "dwz_alt": matched_member.dwz,
                        "dwz_neu": sp["dwz"],
                        "index_alt": matched_member.dwz_index,
                        "index_neu": sp["dwz_index"],
                    }
                )

            if dwz_gekuppelt and status_gekuppelt and matched_member.status != Member.Status.AUSGETRETEN:
                report.synchrone_mitglieder.append(
                    {
                        "member": matched_member,
                        "dsb_player": sp,
                    }
                )

    # 2. Nicht gematchte aktive/passive Vereinsmitglieder -> Fehlt im Verband
    for m in members:
        if m.id not in matched_members:
            if m.status in (Member.Status.AKTIV, Member.Status.PASSIV):
                report.fehlt_im_verband.append(m)

    # 3. Nicht gematchte Verbandsspieler -> Fehlt im Verein
    for idx, sp in enumerate(spieler_list):
        if idx not in matched_players_indices:
            report.fehlt_im_verein.append(sp)

    return report


@transaction.atomic
def sync_dwz_for_member(
    member: Member,
    dsb_player: dict[str, Any],
    benutzer=None,
) -> bool:
    """Übernimmt DWZ, Index und Verbandskennungen für ein einzelnes Mitglied."""
    changed = False

    if member.dwz != dsb_player.get("dwz"):
        member.dwz = dsb_player.get("dwz")
        changed = True

    if member.dwz_index != dsb_player.get("dwz_index"):
        member.dwz_index = dsb_player.get("dwz_index")
        changed = True

    if dsb_player.get("pkz") and member.pkz != dsb_player["pkz"]:
        member.pkz = dsb_player["pkz"]
        changed = True

    if dsb_player.get("zps") and member.zps_nummer != dsb_player["zps"]:
        member.zps_nummer = dsb_player["zps"]
        changed = True

    if dsb_player.get("fide_id") and member.fide_id != dsb_player["fide_id"]:
        member.fide_id = dsb_player["fide_id"]
        changed = True

    if changed:
        member._changed_by = benutzer
        member.save()

    return changed


@transaction.atomic
def sync_dwz_from_report(
    report: DriftReport,
    benutzer=None,
) -> int:
    """Übernimmt alle DWZ-Abweichungen aus einem DriftReport in die Datenbank.

    Schreibt einen zusammenfassenden AuditLog-Eintrag.
    Gibt die Anzahl aktualisierter Mitglieder zurück.
    """
    updated_count = 0

    for item in report.dwz_abweichungen:
        member = item["member"]
        sp = item["dsb_player"]
        if sync_dwz_for_member(member, sp, benutzer=benutzer):
            updated_count += 1

    if updated_count > 0:
        AuditLog.objects.create(
            benutzer=benutzer,
            aktion="DSB-Abgleich durchgeführt",
            text=(
                f"DWZ-Sync für {updated_count} Mitglied(er) übernommen "
                f"(VKZ: {report.vkz or '–'}, Stand: {report.stand})."
            ),
        )

    return updated_count


@dataclass
class DSBInitialImportResult:
    erfolg: bool
    vkz: str
    vereinsname: str
    anzahl_neu: int
    anzahl_aktualisiert: int
    anzahl_uebersprungen: int
    fehler_meldungen: list[str] = field(default_factory=list)


def import_dsb_initial(vkz: str, user=None) -> DSBInitialImportResult:
    """Importiert alle gemeldeten Spieler eines Vereins aus dem DSB-Wertungsportal."""
    from datetime import date
    from members.models import Member

    clean_vkz = (vkz or "").strip()
    if not clean_vkz:
        return DSBInitialImportResult(
            erfolg=False,
            vkz="",
            vereinsname="",
            anzahl_neu=0,
            anzahl_aktualisiert=0,
            anzahl_uebersprungen=0,
            fehler_meldungen=["Bitte eine gültige DSB-Vereinskennziffer angeben."],
        )

    try:
        daten, _ = fetch_dsb_vereinsliste(vkz=clean_vkz, force=True)
    except Exception as exc:
        return DSBInitialImportResult(
            erfolg=False,
            vkz=clean_vkz,
            vereinsname="",
            anzahl_neu=0,
            anzahl_aktualisiert=0,
            anzahl_uebersprungen=0,
            fehler_meldungen=[str(exc)],
        )

    vereinsname = daten.get("verein", "")
    mitglieder_liste = daten.get("mitglieder", [])
    anzahl_neu = 0
    anzahl_uebersprungen = 0

    with transaction.atomic():
        for sp in mitglieder_liste:
            vorname = sp.get("vorname", "").strip()
            nachname = sp.get("nachname", "").strip()
            if not nachname:
                continue

            existing = Member.objects.filter(
                zps_nummer=clean_vkz,
                nachname__iexact=nachname,
                vorname__iexact=vorname,
            ).first()
            if existing:
                anzahl_uebersprungen += 1
                continue

            geburtsjahr = sp.get("geburtsjahr")
            geburtsdatum = date(geburtsjahr, 1, 1) if geburtsjahr else None

            fide_raw = sp.get("fide_id")
            fide_id = None
            if fide_raw:
                try:
                    fide_id = int(fide_raw)
                except (ValueError, TypeError):
                    fide_id = None

            member = Member(
                vorname=vorname,
                nachname=nachname,
                geburtsdatum=geburtsdatum,
                eintrittsdatum=timezone.localdate(),
                status="aktiv",
                dwz=sp.get("dwz"),
                dwz_index=sp.get("dwz_index"),
                fide_id=fide_id,
                pkz=sp.get("pkz") or "",
                zps_nummer=clean_vkz,
            )
            member._changed_by = user
            member.save()
            anzahl_neu += 1

        AuditLog.objects.create(
            benutzer=user,
            aktion="Mitglieder-Initialimport DSB",
            text=f"{anzahl_neu} Mitglieder für VKZ {clean_vkz} ({vereinsname}) aus DSB-Portal importiert ({anzahl_uebersprungen} übersprungen).",
        )

    return DSBInitialImportResult(
        erfolg=True,
        vkz=clean_vkz,
        vereinsname=vereinsname,
        anzahl_neu=anzahl_neu,
        anzahl_aktualisiert=0,
        anzahl_uebersprungen=anzahl_uebersprungen,
    )

