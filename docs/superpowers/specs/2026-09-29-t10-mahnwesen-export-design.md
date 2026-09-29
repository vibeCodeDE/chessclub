# T10: Mahnwesen + Beitrags-Export — Design

**Datum:** 2026-09-29 · **Task:** `tasks/plan.md` T10 · **PRD:** M2.5
**Größe:** M · **Release:** v1 · **Deps:** T9 (erledigt)

## 1. Ziel

Offene Beiträge eines Jahres übersehen, pro Mitglied eine 1. und eine 2. Mahnung
mit Datum setzen, einen druckbaren Mahnbrief erzeugen und die Jahresbeiträge als
CSV exportieren. Kein Mahnungsautomatismus, keine Mahngebühr, kein Versand — der
Vorstand druckt und verschickt selbst (wie der SEPA-Einzug in T9 bankseitig
manuell bleibt, PRD M2.3).

Abnahme laut `tasks/plan.md`: Mahnbrief druckbar für ein Testmitglied; CSV
enthält alle Posten des Jahres; Nicht-Admin erhält 403 auf Übersicht und Export;
CSV enthält nur erlaubte Felder; zweiter Export identisch.

## 2. Entscheidungen (mit dem Menschen, 2026-09-29)

1. **Eigenes Model `Mahnung`** statt Datumsfelder am `FeePost`. Begründung:
   Historie (Wer, Wann, welcher Brief), Erweiterbarkeit auf eine 3. Stufe und ein
   sauberer Export der Mahnstufen. Der Posten selbst bleibt unberührt.
2. **Druckbares HTML statt serverseitigem PDF.** `plan.md` nennt „druckbares
   HTML/PDF", das PRD „Mahnbrief als PDF". Der Browser erzeugt das PDF über
   „Drucken / Als PDF speichern". Damit keine neue Abhängigkeit, kein Umbau des
   Docker-Images und der Inhaltstest bleibt HTML-basiert lesbar. Offen als
   Aufrüstung, falls der Vorstand später serverseitige PDFs braucht.
3. **`verein`-App für die Vereinsdaten.** Ein Model mit genau einem Datensatz
   (Absender, Kontakt, Kassierer, Zahlungshinweis). Es gibt heute nichts, wohin
   diese Angaben gehören; sie werden später auch von T14 (Gruppen-E-Mail) und T13
   (News) gebraucht. Nicht in `dues`, nicht in den Settings.
4. **Stufe streng +1, Datum frei, Prüfungen im Service.** Kein Überspringen, kein
   Doppeln, kein Mahnen eines bezahlten Postens.
5. **Bezahlter Posten fällt automatisch aus der Übersicht**, keine
   Zurückziehen-Funktion. Die Mahnhistorie bleibt lesbar.
6. **CSV ohne Kontaktdaten.** Der Export wird weitergegeben (Buchhaltung, Vorstand);
   er enthält Finanz- und Mahndaten, keine Adressen.
7. **Fachmodule statt Wachstum von `services.py`.** `dues/services.py` hält
   Beitragslauf und Zahlungsstand (T8/T9), T10 kommt in `dues/mahnung.py` und
   `dues/export.py`. T11b (Kassenbericht) bekommt damit ein eigenes Modul.
   Das Muster bleibt: Regelbasis als reine Funktion, ohne HTTP-Kontext, eine
   Abfrage statt N+1, Test ohne Datenbank-UI.

## 3. Architektur

```
dues/
  models.py      + Mahnung
  mahnung.py        NEU  Stufenregel, offene Posten, Brief-Daten
  export.py         NEU  CSV-Spalten und -Zeilen
  services.py       unverändert (Beitragslauf + Zahlungsstand)
  views.py       + mahnliste, mahnbrief, mahnung_setzen, beitraege_export
  urls.py        + 3 Routen
  templates/dues/ + mahnliste.html, mahnbrief.html
  tests/         + test_mahnung_models.py, test_mahnung_services.py,
                    test_export.py, test_views_mahnung.py
verein/         NEU  models.py (Vereinsdaten), admin.py, tests/test_models.py
```

Datenfluss der Übersicht: `offene_posten(jahr)` liefert einmal Dicts
(dieselbe Form wie `posten_mit_status(jahr)`, plus Mahnangaben). Brief, Übersicht und Mahnknöpfe
lesen dieselben Dicts. Es gibt keine zweite Berechnung des offenen Betrags.

## 4. Datenmodell

### 4.1 `dues.Mahnung`

| Feld | Typ | Notizen |
|---|---|---|
| `post` | FK → `FeePost`, `on_delete=PROTECT`, `related_name="mahnungen"` | Finanznachweis, kein Hard-Delete an der Historie (§ 147 AO) |
| `stufe` | PositiveSmallInteger, choices 1/2 | `Stufe.MAHNUNG_1 = 1`, `Stufe.MAHNUNG_2 = 2` |
| `datum` | DateField, default `timezone.localdate` | vom Vorstand frei wählbar, auch rückdatiert |
| `frist` | DateField, null=True, blank=True | Zahlungsfrist, erscheint im Brief |
| `notiz` | TextField, blank=True | interner Vermerk, erscheint **nicht** im Brief |
| `erstellt` | DateTimeField, `auto_now_add` | |
| `erstellt_von` | FK → User, `SET_NULL`, null, blank | |

`Meta`: `ordering = ["-datum", "-pk"]`,
`constraints = [UniqueConstraint(fields=["post", "stufe"], name="unique_mahnung_pro_post_stufe")]`.

Kein Feld für `zurueckgezogen` — Entscheidung Nr. 5. Ein Posten wird bezahlt,
nicht „entmahnt“.

`__str__`: `f"{self.stufe}. Mahnung · {self.post}"`.

### 4.2 `verein.Vereinsdaten`

Genau ein Datensatz für den Brief und später für News/E-Mail.

| Feld | Typ | Notizen |
|---|---|---|
| `name` | CharField(100) | Vereinsname, Pflicht |
| `strasse` | CharField(200, blank) | |
| `plz` | CharField(10, blank) | |
| `ort` | CharField(100, blank) | |
| `telefon` | CharField(50, blank) | |
| `email` | EmailField(blank) | |
| `kassierer` | CharField(100, blank) | Grußformel („Mit freundlichen Grüßen …“) |
| `zahlungshinweis` | TextField(blank) | Textbaustein, z. B. Zahlungswege |
| `zahlungsziel` | TextField(blank) | Verwendungszweck-Text |

`Meta`: `verbose_name_plural = "Vereinsdaten"`.

`Vereinsdaten.aktuell()` liefert den einen Datensatz und legt ihn beim ersten
Aufruf an (`get_or_create(pk=1)`), damit ein frisches Deployment keinen
`DoesNotExist` in der Briefansicht produziert. `save()` erzwingt `pk=1`, damit
sich nicht versehentlich eine zweite Zeile bildet. `str()` = `name`.

Im Frontend nur lesend. Bearbeitung ausschließlich im Admin
(`verein/admin.py`).

## 5. Regelbasis `dues/mahnung.py`

Alle Funktionen nehmen/enthalten Modelle oder IDs, keine `HttpRequest`.

### 5.1 `naechste_stufe(post)` → `int | None`

Liest die vorhandenen Stufen des Postens:

- keine Mahnung → `1`
- nur Stufe 1 → `2`
- 1 und 2 vorhanden → `None` („Stufen ausgeschöpft“)

### 5.2 `mahnungen_setzen(post, stufe, datum, frist=None, benutzer=None, notiz="")` → `Mahnung`

In `transaction.atomic()`, mit drei Prüfungen und klaren `ValidationError`-Meldungen:

1. **Posten noch offen?** `if offen(post) <= 0` → „Der Beitragsposten … ist bereits
   bezahlt — für ihn kann keine Mahnung gesetzt werden." (Ein Gutschrift-Posten
   ebenso.)
2. **Stufe genau die nächste?** `stufe != naechste_stufe(post)` → zwei Meldungen:
   `stufe > erwartet` → „Stufe {stufe} kann nicht gesetzt werden — es fehlt die
   {erwartet}. Mahnung.“; `stufe < erwartet` → „Stufe {stufe} existiert bereits
   für diesen Beitragsposten.“
3. **Datum gültig?** Datumsprüfung gegen Zukunft **nein** — eine Rückdatierung ist
   legitim. Nur unlesbare Eingaben werden von `_datum()` in `views.py` zu `None`
   und hier mit „Bitte ein gültiges Mahndatum angeben.“ abgefangen.

`frist` < `datum` wird nicht geprüft (Frist in der Vergangenheit ist beim
späteren Drucken sinnvoll). `notiz` wird nie validiert (freier Text).

Danach `AuditLog.objects.create(aktion="Mahnung gesetzt",
text="…", member=post.member)`. Eine `IntegrityError` aus
`unique_mahnung_pro_post_stufe` (Doppelklick, zwei Vorstände gleichzeitig) wird
in dieselbe `ValidationError`-Meldung wie Regel 2 übersetzt, damit der Vorstand
eine verständliche Meldung sieht und kein 500.

Kein Storno-Pfad: eine Mahnung wird nicht zurückgenommen (Entscheidung Nr. 5).

### 5.3 `offene_posten(jahr)` → `list[dict]`

Eine Abfrage, keine N+1. Aufbau wie `posten_mit_status(jahr)`:

- Basis: `FeePost.objects.filter(jahr=jahr).select_related("member", "kategorie")`
  mit `Coalesce(Sum("zahlungen__betrag"), 0)` als `bezahlt_summe`
- im Python-Teil: `offen = betrag - bezahlt`, nur `offen > 0` behalten
- Mahnungen über `prefetch_related("mahnungen")`, dann je Zeile
  `{post, member, kategorie, jahr, betrag, bezahlt, offen, status, status_label,
  status_klasse, mahnungen, stufe, stufe_text}`

`stufe` = `naechste_stufe(post)`, `stufe_text` = `mahnstufe_text(stufe)` bzw.
„ausgeschöpft". Sortierung wie die Postenliste: Nachname, Vorname.

`assertNumQueries` im Test, damit eine spätere Änderung hier nicht unbemerkt
N+1 einführt.

### 5.4 `posten_fuer_brief(jahr, member)` → `(list[dict], Decimal)`

Filtert `offene_posten(jahr)` auf das Mitglied und summiert `offen`. Die Briefseite
kann so nicht von der Übersicht abweichen. Fehlt der Satz (Posten wurde
zwischenzeitlich bezahlt), ist die Liste leer — die View gibt dann 404.

### 5.5 `mahnstufe_text(stufe)` → `str`

`1` → „1. Mahnung“, `2` → „2. Mahnung“, `None` → „ausgeschöpft“. Eine Quelle für
Übersicht, Brief und Button-Beschriftung.

## 6. Export `dues/export.py`

```python
CSV_SPALTEN = (
    "Jahr", "Nachname", "Vorname", "Kategorie", "Beitrag", "Bezahlt", "Offen",
    "Status", "Mahnungen", "1. Mahnung am", "2. Mahnung am",
)
```

`beitragszeilen(jahr)` liefert **alle** Posten des Jahres — auch bezahlte. Der
Export ist die Jahresübersicht für die Buchhaltung, nicht die Mahnliste; genau
deshalb nimmt er `posten_mit_status(jahr)` (T9) und nicht `offene_posten(jahr)`.
Die unterschiedliche Menge wird im Docstring festgehalten, damit sie nicht wie
ein Versehen aussieht.

- Sortierung: Nachname, Vorname (deterministisch — zweiter Export byte-identisch)
- Beträge deutsch (`90,00`), Datumsspalten `isoformat()` oder leer
- Anzahl Mahnungen = `len(posten.mahnungen)`, Stufenspalten aus `mahnungen`
  (Posten ohne Mahnung → leere Zellen, nicht „0“)

Die Spaltenliste *ist* die Erlaubnis: der Inhaltstest vergleicht Kopf und Zellen
gegen `CSV_SPALTEN` und schließt Adresse, PLZ, Ort, E-Mail, Telefon und
Geburtsdatum aus.

## 7. Oberfläche

### 7.1 Routen (alle `role_required(ADMIN_GROUP)`)

| Pfad | Name | Methode |
|---|---|---|
| `beitraege/mahnungen/` | `dues:mahnliste` | GET |
| `beitraege/mahnungen/<int:pk>/` | `dues:mahnbrief` | GET |
| `beitraege/mahnungen/<int:pk>/setzen/` | `dues:mahnung_setzen` | POST |
| `beitraege/export.csv` | `dues:beitraege_export` | GET |

`pk` ist die `FeePost`-id in allen drei Posten-Routen. Der Brief entsteht aus dem
offenen Posten, nicht aus einer Mahnungs-URL.

Nav: vierter Eintrag „Mahnungen“ nach „Zahlungen“, nur Admin
(`core/context_processors.py`).

### 7.2 Views

- **`mahnliste`** — Jahr aus `?jahr=` über `_parse_jahr`, sonst aktuelles Jahr;
  `_jahre()` für den Filter. Kontext `offene_posten(jahr)`, Summenzeile
  (`summe_offen`), `jahre`, `jahr`, Export-URL. Ohne Beitragslauf: leere Liste
  plus Hinweistext „Für dieses Jahr wurden keine Beiträge gebucht.“ — kein
  Crash. Der Mahnknopf erscheint nur, wenn `stufe` nicht `None` ist; das Datum
  ist ein `date`-Input (default heute), die Frist optional.
- **`mahnung_setzen`** — POST. Fehler → `messages.error` + Redirect auf
  `mahnliste?jahr=…`. Bewusst **kein** Re-Render mit Formularwerten: fünf Felder,
  Fehler sind selten, und die Liste behält ihre Auswahl nicht, was hier nichts
  kostet. Erfolg → Erfolgsmeldung mit Stufe und Datum.
- **`mahnbrief`** — GET auf dem Posten. 404 bei unbekanntem Posten, 404 wenn
  `posten_fuer_brief` leer ist (sonst druckt jemand einen leeren Brief). Rendert
  ein eigenständiges Dokument, **nicht** `base.html`.
- **`beitraege_export`** — GET. `HttpResponse(content_type="text/csv; charset=utf-8")`,
  BOM, `;`-Trenner, `filename="beitraege_<jahr>.csv"` — dasselbe Muster wie
  `members.views.mitglieder_export`. **Kein** `AuditLog`: ein Export ist eine
  Leseaktion; protokolliert wird er laut PRD erst mit T23 (Auskunfts-Export).
  Begründung steht im Docstring der View.

### 7.3 Templates

- `dues/mahnliste.html` — Kopf mit Jahresfilter und CSV-Knopf, Summenzeile,
  Tabelle Posten/Kategorie/Beitrag/Bezahlt/Offen/Status/bisherige Mahnungen/
  Aktion (Brief + Mahnformular). Klassen und Badges wie in `posten_liste.html`.
- `dues/mahnbrief.html` — eigenes `<html lang="de">`: Absenderblock aus
  `Vereinsdaten.aktuell()`, Empfängeranschrift, Datum, Anrede, Einleitungstext
  mit Stufe, Tabelle der offenen Posten (Jahr, Kategorie, Beitrag, Bezahlt,
  Offen), Summe, `zahlungshinweis`, `zahlungsziel`, Frist, Grußformel mit
  `kassierer`. Kein `notiz`. Ein sichtbarer Knopf „Drucken / Als PDF speichern“
  (`onclick="window.print()"`), der per `@media print` ausgeblendet wird, dazu
  `@page`-Margin. Das Print-Stylesheet steht im `<style>`-Block des Briefs, weil
  es nur dort gilt.
- Kein neues Fremd-Asset: das Brief-Stylesheet ist Inline-CSS, alles andere
  kommt aus dem vorhandenen Tailwind-Build (`npm run build:css`).

## 8. Tests

TDD — Tests zuerst, in dieser Reihenfolge.

**`dues/tests/test_mahnung_models.py`**
`unique(post, stufe)`; `stufe`-Choices (1, 2); Defaults `datum`/`frist`/`notiz`;
`PROTECT` auf dem Posten; `__str__`.

**`dues/tests/test_mahnung_services.py`**
Stufenfolge 1 → 2 → `None`; `mahnungen_setzen` lehnt ab: bezahlter Posten,
Gutschrift-Posten, übersprungene Stufe, doppelte Stufe, unbekannte Stufe, kein
Posten; nimmt an: rückdatiertes Datum, `frist=None`, leere Notiz; Audit-Zeile mit
`aktion="Mahnung gesetzt"` und `member=post.member`; `offene_posten` lässt bezahlte
Posten und Gutschriften heraus, offener Betrag == `offen(posten)`, Reihenfolge stabil,
`assertNumQueries` ohne N+1; `posten_fuer_brief` liefert dieselbe Menge wie
`offene_posten` für das Mitglied; Jahr ohne Posten → leere Liste.

**`dues/tests/test_export.py`**
Kopfzeile exakt `CSV_SPALTEN`; **Inhaltstest:** keine Zelle enthält Straße, PLZ,
Ort, E-Mail, Telefon oder Geburtsdatum (auch nicht die des exportierten
Mitglieds); zwei Exporte desselben Jahres byte-identisch; bezahlte Posten sind
enthalten; Anzahl Datenzeilen == `FeePost.objects.filter(jahr=…).count()`;
Jahressumme == im Test berechnete Modellsumme (kein fester Wert).

**`dues/tests/test_views_mahnung.py`**
403 für `kapitaen` und `mitglied` auf `mahnliste`, `mahnbrief`, Export **und**
`mahnung_setzen` — jeweils mit `assertNumQueries`/Zählprüfung, dass dabei keine
Mahnung entsteht; GET auf `mahnung_setzen` → 405; `mahnbrief` 404 bei
unbekanntem Posten und bei inzwischen bezahltem Posten; Brief enthält
Mitgliedsname und Summe, **nicht** die interne Notiz; Mahnliste ohne Beitragslauf
→ 200 mit Hinweistext; Jahr mit ausgeschöpften Stufen zeigt keine Mahnbuttons;
Redirect nach erfolgreichem Setzen mit Erfolgsmeldung.

**`verein/tests/test_models.py`**
`Vereinsdaten.aktuell()` liefert den einen Datensatz und legt keinen zweiten an;
`save()` erzwingt `pk=1`.

**`core/tests/test_nav.py`** — Nav enthält „Mahnungen“ nur für Admin.

**Verifikation:** `pytest dues/ verein/ core/`, danach Browser-Check am laufenden
Stack: Lauf 2027 → zwei von drei Mitgliedern zahlen → Mahnliste zeigt genau einen
offenen Posten mit Summe → 1. Mahnung mit Datum setzen → Brief ansehen/drucken →
CSV öffnen und Spalten prüfen → 360 px und 1280 px ohne horizontalen Overflow.
Zweiter Klick auf „2. Mahnung“ → Button bzw. Stufe 2; dritter Versuch → saubere
Ablehnung.

## 9. Abgrenzung

Nicht in T10: Mahngebühr, Mahnungsautomatik (Zeitplan, Mailversand),
Zurückziehen einer Mahnung, Zurückziehen/Storno eines **Beitragspostens**
(weiterhin Admin-Korrektur mit Audit-Spur aus T8), Mitglieder-Sicht auf den
eigenen Beitragsstand (PRD §3.8, später), Protokollierung des Exports (T23),
PDF-Serverseite (siehe Entscheidung Nr. 2).

## 10. Nebenwirkungen für Folge-Tasks

- **T11 (Dashboard)** liest offene Summe und Anzahl aus `offene_posten(jahr)` —
  dieselbe Quelle wie die Mahnliste, keine Zweitberechnung.
- **T11b (Kassenbericht)** bekommt `dues/kassenbericht.py` neben `mahnung.py`
  und `export.py`; `beitragszeilen(jahr)` ist die naheliegende Grundlage für
  dessen CSV, der Spaltenumfang ist dort aber zu entscheiden.
- **`verein.Vereinsdaten`** ist die Quelle für Absender und Kontakt in T14
  (Gruppen-E-Mail) und T13 (News) — dort ist die Pflege im Admin bereits da.
