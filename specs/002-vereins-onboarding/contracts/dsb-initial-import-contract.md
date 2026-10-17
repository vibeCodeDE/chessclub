# Interface Contract: DSB Initial-Import Service

**Modul**: `members.services.dsb_sync` (oder Kapselung in `core.services`)  
**Funktion**: `import_dsb_initial(vkz: str, user: User | None = None) -> DSBInitialImportResult`  
**Kontext**: Reine Fachfunktion ohne HTTP-Abhängigkeit; idempotente Ausführung in `transaction.atomic`  

---

## 1. Parameter & Eingabeformat

| Parameter | Typ | Beschreibung | Validierung |
|---|---|---|---|
| `vkz` | `str` | 5-stellige DSB-Vereinskennziffer | Muss 5 Zeichen lang sein (z. B. `C0101` oder `10101`). Führende/nachfolgende Leerzeichen werden gestrippt. |
| `user` | `User \| None` | Handelnder Benutzer | Wird für das `AuditLog` und die Erfasser-Spur protokolliert. |

---

## 2. Rückgabestruktur (`DSBInitialImportResult`)

```python
@dataclass
class DSBInitialImportResult:
    erfolg: bool
    vkz: str
    vereinsname: str
    anzahl_neu: int
    anzahl_aktualisiert: int
    anzahl_uebersprungen: int
    fehler_meldungen: list[str] = field(default_factory=list)
```

---

## 3. Geschäftslogik & Zuordnungsregeln

1. **Abruf**: Ruft `fetch_dsb_vereinsliste(vkz=vkz, force=True)` auf. Bei Netzwerk- oder Konfigurationsfehlern fängt die Funktion die Fehler ab und liefert `erfolg=False` mit verständlicher Fehlermeldung.
2. **Datentransformation je Spieler**:
   - `vorname`: Vorname aus DSB-Datensatz.
   - `nachname`: Nachname aus DSB-Datensatz.
   - `geburtsdatum`: Sofern ein Geburtsjahrgang vorliegt, wird der 01.01. des Jahrgangs als Datum gesetzt; andernfalls bleibt das Feld leer.
   - `status`: Immer `"aktiv"`.
   - `dwz`: Aktueller DWZ-Wert (Integer) oder `None`.
   - `dwz_index`: DWZ-Index (Integer) oder `None`.
   - `fide_id`: FIDE-ID (String) oder `""`.
   - `zps_nummer`: Gesetzt auf die übergebene `vkz`.
3. **Dublettenerkennung**:
   - Ein Mitglied gilt als bereits vorhanden, wenn `zps_nummer == vkz` und `nachname.lower() == ds_nachname.lower()` und `vorname.lower() == ds_vorname.lower()`.
   - Bereits vorhandene Mitglieder werden im Initial-Import nicht überschrieben, sondern inkrementieren `anzahl_uebersprungen`.
4. **Audit-Trail**:
   - Nach erfolgreichem Durchlauf wird ein Eintrag im `AuditLog` erzeugt:
     - `aktion`: „Mitglieder-Initialimport DSB“
     - `text`: „X Mitglieder für VKZ {vkz} aus DSB-Portal importiert.“
