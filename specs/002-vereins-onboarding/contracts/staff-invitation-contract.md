# Interface Contract: Funktionärseinladungen (`StaffInvitation`)

**Bereich**: Authentifizierung, Benutzeraktivierung & Rollenzuweisung  
**URLs**:
- Einladung versenden (Admin-Onboarding): `/onboarding/schritt/5/`
- Einladung annehmen (Öffentlich für Eingeladene): `/einladung/<str:token>/`  

---

## 1. Einladungserstellung (`create_staff_invitation`)

### Signatur
```python
def create_staff_invitation(
    email: str,
    vorname: str,
    nachname: str,
    rolle: str,
    eingeladen_von: User,
    basis_url: str = "",
) -> StaffInvitation
```

### Validierung
- `email`: Gültiges E-Mail-Format; falls bereits ein aktiver `User` mit dieser E-Mail existiert, wird die Einladung abgelehnt (Hinweis: Benutzer existiert bereits).
- `rolle`: Muss `ADMIN_GROUP` ("admin") oder `KAPITAEN_GROUP` ("kapitaen") sein.
- `token`: 32 Byte URL-sicheres Token via `secrets.token_urlsafe(32)`.
- `gueltig_bis`: `timezone.now() + timedelta(days=7)`.

### E-Mail-Inhalt
- Absender: Offizielle Vereins-E-Mail (`ClubProfile.get_solo().kontakt_email` oder Default).
- Betreff: `Einladung zur Vereinsverwaltung des {Vereinsname}`.
- Inhalt: Persönliche Anrede, zugewiesene Funktion (Vorstand / Mannschaftsführer), Einladungslink mit Token und Gültigkeitsfrist (7 Tage).

---

## 2. Einladungsannahme (`/einladung/<str:token>/`)

### GET-Request
1. Prüft, ob `StaffInvitation` mit `token` existiert und `is_valid()` ist (`status == "offen"` und `gueltig_bis >= now()`).
2. Falls abgelaufen oder ungültig: Zeigt eine barrierefreie Fehlermeldung mit der Bitte, den Administrator um einen neuen Einladungslink zu bitten.
3. Falls gültig: Zeigt das Registrierungsformular:
   - Benutzername (vorgeschlagen: `vorname.nachname` oder E-Mail)
   - Vorname & Nachname (vorbelegt aus Einladung)
   - Passwort (Passwort-Bestätigung nach Django-Passwortrichtlinien)

### POST-Request
1. Validiert Passwort-Komplexität und Eindeutigkeit des Benutzernamens.
2. Führt in einer atomaren Transaktion (`transaction.atomic`) aus:
   - Erstellt neuen `User` (oder aktiviert bestehenden).
   - Weist die Ziel-Gruppe (`Group.objects.get(name=invitation.rolle)`) zu.
   - Setzt `is_staff = True` (für `admin`), `is_active = True`.
   - Setzt `invitation.status = "angenommen"`, `invitation.angenommen_am = now()`, `invitation.benutzer = user`.
   - Schreibt `AuditLog`-Eintrag.
3. Authentifiziert den neuen Benutzer automatisch (`login(request, user)`).
4. Führt Redirect zum rollenspezifischen Dashboard durch (`core:dashboard`).
