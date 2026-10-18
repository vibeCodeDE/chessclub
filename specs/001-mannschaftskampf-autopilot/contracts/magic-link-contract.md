# Contract: Magic-Link Verfügbarkeits- & Ersatzspieler-Rückmeldung

**Feature**: `001-mannschaftskampf-autopilot` | **Date**: 2026-10-17 | **Spec**: [spec.md](../spec.md)

---

## 1. Übersicht

Der Magic-Link ermöglicht Stamm- und Ersatzspielern die sofortige Rückmeldung ohne Benutzer-Login und ohne Passwort auf jedem mobilen Browser (FR-003, FR-008, FR-011).

URL-Muster:
- Stammspieler: `GET /spielbetrieb/rueckmeldung/<token>/`
- Ersatzspieler: `GET /spielbetrieb/ersatz/<token>/`

---

## 2. Stammspieler-Verfügbarkeit

### `GET /spielbetrieb/rueckmeldung/<str:raw_token>/`
Prüft das Token und rendert die für Mobilgeräte optimierte Antwortmaske.

**Ablauf**:
1. Hash bilden: `token_hash = sha256(raw_token)`
2. Lookup `PlayerAvailability` mit `token_hash=token_hash` und `token_gueltig_bis > now()`.
3. Falls ungültig oder abgelaufen → 404 mit erklärender Nachricht („Dieser Link ist abgelaufen oder ungültig.“).
4. Rendert `teams/autopilot/availability_form.html`.

**Angezeigte Daten**:
- Vereinsname & Mannschaft (z. B. „Königsspringer 1 – Landesliga“)
- Spieltermin, Uhrzeit, Heim-/Auswärtsspiel, Gegner und Spielort
- Name des Spielers und gemeldetes Brett (z. B. „Brett 4: Max Mustermann“)
- Aktueller Status (sofern bereits beantwortet)
- Drei Aktions-Buttons:
  - `[Bin dabei]`
  - `[Kann nicht]`
  - `[Brauche Mitfahrgelegenheit / Fahre selbst]`

### `POST /spielbetrieb/rueckmeldung/<str:raw_token>/`
Reicht die Rückmeldung ein.

**Parameter (Form Data)**:
```text
status: "zugesagt" | "abgesagt"
fahr_status: "keine_angabe" | "brauche_mitfahrt" | "biete_mitfahrt" | "selbst_anreise"
freie_plaetze: integer (0 bis 8, Standard 0 bzw. 3 bei biete_mitfahrt)
treffpunkt_notiz: string (optional, max 150 Zeichen)
```

**Antwort**:
- HTML-Bestätigungsseite mit Status-Badge (Grün = Zusage, Rot = Absage) und Möglichkeit zur nachträglichen Änderung bis zum Meldeschluss.
- AJAX-fähig: Bei `Accept: application/json` Rückgabe von:
```json
{
  "success": true,
  "status": "zugesagt",
  "fahr_status": "biete_mitfahrt",
  "freie_plaetze": 3,
  "message": "Vielen Dank! Deine Rückmeldung wurde erfolgreich gespeichert."
}
```

---

## 3. Ersatzspieler First-Come-First-Serve Zusage

### `GET /spielbetrieb/ersatz/<str:raw_token>/`
Zeigt die Einladungsseite für den Ersatzspieler.

**Ablauf**:
1. Hash bilden: `token_hash = sha256(raw_token)`
2. Lookup `SubRequestCandidate` mit `token_hash=token_hash`.
3. Prüfung von `candidate.sub_request.status`:
   - Falls `BESETZT`: Zeigt sofort freundliche Hinweisseite: „Vielen Dank! Der Platz wurde bereits von [Vorname] besetzt.“
   - Falls `OFFEN`: Zeigt Spieldetails, vakantes Brett und großen Bestätigungsbutton `[Ich springe ein!]`.

### `POST /spielbetrieb/ersatz/<str:raw_token>/`
Kandidat willigt ein und sichert sich den Platz.

**Transaktionssicherer Ablauf**:
```python
with transaction.atomic():
    sub_request = SubRequest.objects.select_for_update().get(pk=candidate.sub_request_id)
    if sub_request.status != SubRequest.Status.OFFEN:
        return render(request, "teams/autopilot/sub_already_taken.html", {
            "akzeptiert_von": sub_request.akzeptiert_von
        })
    sub_request.status = SubRequest.Status.BESETZT
    sub_request.akzeptiert_von = candidate.member
    sub_request.akzeptiert_am = timezone.now()
    sub_request.save()
    
    candidate.status = SubRequestCandidate.Status.ZUGESAGT
    candidate.geantwortet_am = timezone.now()
    candidate.save()
    
    # Aufstellungseintrag aktualisieren
    LineupEntry.objects.update_or_create(
        match=sub_request.match,
        brett=sub_request.brett,
        defaults={"member": candidate.member}
    )
    
    # AuditLog schreiben
    AuditLog.log(...)
```

**Antwort**:
- Bei Erfolg: Bestätigungsseite mit Spielort, Treffpunkt und Kontaktdaten des Mannschaftsführers.
- Bei Konkurrenzklick (< 1s zu spät): Hinweisseite, dass der Platz soeben vergeben wurde.
