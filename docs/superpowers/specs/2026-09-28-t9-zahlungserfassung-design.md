# T9: SEPA-Mandate + Zahlungserfassung — Design

**Datum:** 2026-09-28 · **Task:** `tasks/plan.md` T9 · **PRD:** M2.3, M2.4 · **Release:** v1 · **Deps:** T8
**Beteiligte:** T8 hat `FeePost` (Mitglied × Jahr, `unique_together`, Betrag als Momentaufnahme) und die Regelbasis in `dues/services.py` geliefert. T9 bucht Zahlungen **auf** diese Posten.

---

## Ziel

Der Verein bucht Beitragszahlungen von Hand in der Software (Überweisung, SEPA-Einzug, Barzahlung) und sieht je Beitragsposten, was offen ist. Die Software führt **keinen** Einzug durch: das Mandat wird verwaltet, der Einzug erfolgt bankseitig per SEPA-Lastschrift. Es gibt keinen Bank-API-Call im Code.

## Datenmodell (`dues/models.py`)

### `SepaMandate` — je Mitglied, mehrere erlaubt

| Feld | Typ | Bedeutung |
| --- | --- | --- |
| `member` | FK → `members.Member`, `PROTECT`, `related_name="sepa_mandate"` | Mandatsinhaber |
| `referenz` | `CharField(50, unique=True)` | Mandatsreferenz des Einzugs |
| `datum` | `DateField(default=timezone.localdate)` | Mandatsdatum |
| `status` | `CharField(20)`, Default `aktiv` | `aktiv` / `widerrufen` / `beendet` (`TextChoices`) |
| `notiz` | `TextField(blank=True)` | z. B. „IBAN geändert" |

Ein Mandatswechsel (neue Bankverbindung) erzeugt einen neuen Datensatz; der alte behält `widerrufen`/`beendet`. Maßgeblich ist: **mindestens ein aktives Mandat**.

**Kein IBAN-/BIC-Feld.** PRD M2.3 verlangt nur Referenz, Datum, Status; die IBAN liegt beim Verein in der Lastschriftdatei der Bank. Damit keine Bankdaten in der DB, keine DSGVO-Folgefragen.

### `Payment` — eine Zahlung gehört genau einem Beitragsposten

| Feld | Typ | Bedeutung |
| --- | --- | --- |
| `post` | FK → `FeePost`, `PROTECT`, `related_name="zahlungen"` | bezahlter Beitragsposten |
| `betrag` | `Decimal(6,2)` | **negativ = Storno** (Gegenbuchung) |
| `art` | `CharField(10)` | `sepa` (SEPA-Einzug) / `ueberweisung` / `bar` (`TextChoices`) |
| `datum` | `DateField(default=timezone.localdate)` | Zahlungsdatum |
| `referenz` | `CharField(100, blank=True)` | Buchungsbeleg / Kontoauszug |
| `storno_von` | FK → `self`, null, `SET_NULL`, `related_name="stornos"` | Originalzahlung bei einer Gegenbuchung |
| `notiz` | `TextField(blank=True)` | |
| `erfasst` | `DateTimeField(auto_now_add=True)` | |
| `erfasst_von` | FK → User, null, `SET_NULL` | |

`clean()`:
1. `betrag == 0` → `ValidationError` (kein Null-Buchung).
2. `art == sepa` → das Mitglied muss ein **aktives** `SepaMandate` haben. Widerrufen/beendet genügt nicht.

**Storno statt Löschen:** Zahlungen sind unveränderlich. Eine falsch gebuchte Zahlung wird durch eine Gegenbuchung mit negativem Betrag auf demselben Posten aufgehoben, verknüpft über `storno_von`, mit `notiz` („Storno zu #id"). Das entspricht dem in T8 für Beitragsposten getroffenen v1-Beschluss (kein Storno-Pfad für Posten, kein Hard-Delete).

## Regelbasis (`dues/services.py`)

Bewusst im Service, nicht im Modell — T10 (Mahnen/Export) und T11b (Kassenbericht) brauchen dieselben Zahlen, genau wie T8 mit `plan_lauf`/`fuehre_lauf`.

- `bezahlte_summe(posten)` — Summe aller Zahlungen inkl. Stornos
- `offen(posten)` = `betrag − bezahlte_summe`; **negativ = Gutschrift**
- `ist_bezahlt(posten)` = `bezahlte_summe >= betrag`
- `posten_mit_status(jahr)` — Queryset mit den Annotationen `bezahlte_summe` (`Coalesce(Sum("zahlungen__betrag"), 0)`), damit Listen ohne N+1 auskommen
- `aktives_mandat(member)`, `hat_sepa_mandat(member)`

Status als `TextChoices`, in der Postenliste als Badge:

| Status | Bedingung | Anzeige |
| --- | --- | --- |
| `unbezahlt` | Summe = 0 | „unbezahlt" + voller Betrag offen |
| `offen` | 0 < Summe < Betrag | „teilbezahlt" + Restbetrag |
| `bezahlt` | Summe = Betrag | „bezahlt" + 0,00 € offen |
| `gutschrift` | Summe > Betrag | „überzahlt" + negativer offener Betrag als **Gutschrift** (T9-Acceptance: anzeigen, **nicht** kappen) |

## UI (`dues/views.py`, `dues/urls.py`, Templates)

Alles Admin-only über `@role_required(ADMIN_GROUP)`; Muster wie T8. Kein Bank-API-Call, keine externen Requests.

| Route | Methode | Zweck |
| --- | --- | --- |
| `/beitraege/zahlungen/` | GET | Zahlungsliste (nach Jahr filterbar) + Formular „Zahlung buchen" + Abschnitt „SEPA-Mandate" (anlegen, Status setzen) |
| `/beitraege/zahlungen/` | POST | bucht die Zahlung, redirect in die Liste |
| `/beitraege/zahlungen/<pk>/storno/` | POST | Storno-Gegenbuchung |

- `?posten=<id>` prefüllt das Formular aus der Postenliste (Betrag = offener Betrag, Art voreinstellbar).
- Die Postenauswahl im Formular zeigt je Posten den Restbetrag; überschreitet der Betrag den Postenbetrag, ist das erlaubt (Überzahlung → Gutschrift) und wird beim Speichern als solche angezeigt.
- **`/beitraege/`** (`posten_liste`) bekommt die Spalten „Bezahlt" / „Offen" + Status-Badge und je Zeile einen Button „Zahlung buchen" (`?posten=<id>`).
- **Nav:** zweiter Admin-Eintrag „Zahlungen" (`dues:zahlungsliste`) in `core/context_processors.py`.
- 360 px / 1280 px ohne horizontalen Overflow (Bestehende CSS-Klassen `.table-wrap`, `.inline-form`, `.tile`, `.badge`, `.alert-*` genügen.)

### Fehlerverhalten

| Fall | Verhalten |
| --- | --- |
| SEPA ohne aktives Mandat | `ValidationError` → `messages.error` mit Klartext, **keine** Buchung |
| Betrag 0 | abgelehnt |
| unbekannter Posten / ungültiges Jahr | abgelehnt (wie `_parse_jahr` in T8) |
| Buchung per GET | 405 (`@require_POST`) |
| Rolle „kapitaen"/„mitglied" | 403, und es entsteht **keine** Zahlung |
| Formularfehler | Eingaben bleiben im Formular erhalten, Fehlermeldung per `messages` |

## Audit (`core.AuditLog`)

Muster wie T8 (`fuehre_lauf`, `FeePostAdmin.save_model`) — manuelle Einträge, keine Signale:

- Zahlung gebucht → `aktion="Zahlung gebucht"`, `member=post.member`, Betrag/Art/Datum/Posten-Jahr im `text`
- Storno → `aktion="Zahlung storniert"`, Verweis auf die Originalzahlung im `text`
- Mandat angelegt → `aktion="SEPA-Mandat angelegt"`, `member=mandat.member`
- Mandat-Statuswechsel → `aktion="SEPA-Mandat geändert"`, `feld="status"`, `alt_wert`/`neu_wert`

## Admin (`dues/admin.py`)

- `SepaMandateAdmin`: anlegen/ändern erlaubt, `member` read-only, `list_display` (Mitglied, Referenz, Status, Datum), `list_filter` (Status), Suche über Mitgliedsnamen + Referenz
- `PaymentAdmin`: **nur einsehbar** — `has_add_permission`/`has_delete_permission` = `False`, Betrag/Art/Datum/Posten read-only; Korrektur ausschließlich per Storno aus der UI (gleiches Muster wie `FeePostAdmin`)

## Tests

Konvention: `django.test.TestCase`, Modul-Helper (`make_user`, `make_member`, `kategorie`), Negativtests mit Docstring `"""Negativtest: …"""`, DB-Constraints über `transaction.atomic()` + `IntegrityError`.

- `dues/tests/test_models.py` — Negativtest Betrag 0; Negativtest SEPA ohne Mandat; Negativtest SEPA mit nur `widerrufenem` Mandat; `referenz` unique; Storno-Verknüpfung
- `dues/tests/test_services.py` — offener Betrag, Bezahlt-Schwelle, **Überzahlung bleibt Gutschrift (nicht gekappt)**, Annotation ohne N+1 (AssertNumQueries), Storno stellt den offenen Betrag wieder her
- `dues/tests/test_views.py` — Buchung per POST; **GET → 405**; **403 für „kapitaen" und „mitglied" ohne Seiteneffekt**; Formular bleibt bei Fehler; Mandat anlegen + Status setzen; Storno per POST
- `dues/tests/test_admin.py` — Payment nicht anlegbar/löschbar, Mandat anlegbar
- **Integrationsfloss (End-to-End):** Beitragslauf 2027 → Posten → Buchung → Posten „bezahlt" → Storno → wieder „unbezahlt"
- **Kein Bank-API-Call:** Test, dass `dues` keinerlei Netzwerk-Imports (`requests`, `urllib.request`, `http.client`, `socket`) einbindet (T9-Acceptance)

## Abgrenzung — bewusst nicht in T9

- Mitglieder-Sicht auf den eigenen Beitragsstand (Berechtigungsmatrix §3.8, aber eigene spätere Aufgabe)
- Mahnwesen, Mahnbrief, CSV-Export → T10
- Dashboard-Beitragskachel → T11 · Kassenbericht/Jahresübersicht → T11b
- Storno-Pfad für **Beitragsposten** (aus T8) — weiterhin nicht Teil von v1
- Kein IBAN, keine SEPA-Datei-Erzeugung, kein Banking-API-Call

## Entscheidungen mit dem Menschen (2026-09-28)

1. Zahlung hängt **direkt** am Beitragsposten (kein Posten-freier Zahlungseingang) → offener Betrag ist eindeutig berechenbar.
2. Mandat speichert nur Referenz/Datum/Status — **keine IBAN** (PRD M2.3, Abgrenzung „bankseitig manuell").
3. Falsche Buchung → **Storno per Gegenbuchung**, kein Löschen, kein Überschreiben.
4. Mandatsstatus: `aktiv` / `widerrufen` / `beendet`.
5. Eigene Zahlungsseite mit Buchungsformular; Postenliste zeigt nur Betrag + Button.
6. Offener Betrag und Status kommen aus `dues/services.py` mit Annotationen (keine gespeicherten Summen, keine Modell-Properties mit N+1).
7. Die Mitglieder-Sicht auf den eigenen Beitragsstand ist **nicht** Teil von T9.
