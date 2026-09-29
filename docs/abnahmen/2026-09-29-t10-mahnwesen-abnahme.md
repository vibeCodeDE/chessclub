# Abnahme T10 — Mahnwesen + Beitrags-Export

**Datum:** 2026-09-29 · **Task:** T10 (Abnahme) · **Commit der Abnahme:** siehe `tasks/todo.md`

Dieses Dokument hält die **gemessenen** Abnahme-Belege fest, damit die Abnahme nach
dem Push ohne den SDD-Report nachprüfbar bleibt. Es enthält **Werte, keine Bilder**:
jede Zahl ist eine Beobachtung aus dem echten Browser, kein geschätzter Wert.

**Werkzeug:** `agent-browser` 0.33.2 (Chromium via CDP, auf dem Host installiert)
gegen `http://localhost:8000` des laufenden Docker-Stacks (`docker compose up`).
Gemessen wurde mit `document.documentElement.scrollWidth` gegen
`document.documentElement.clientWidth` bzw. `document.body` — **nicht** aus dem
Stylesheet gelesen und **nicht** aus gerendertem HTML geschlossen.

**Konto:** `t8check`, Gruppe `admin`, `is_staff=True`, Django-Modell-Berechtigungen
für `verein`/`dues`/`members` (nötig für den Django-Admin, sonst 403 dort). Zusätzlich
`kapitaen` und `mitglied` für die Rollenmatrix. Die Zugangsdaten stehen bewusst
**nicht** in diesem Dokument.

**Daten:** Beitragsjahr **2028** als isoliertes Prüfjahr (`FeeCategory` „Abnahme-Test",
3 Prüfmitglieder Nele/Jonas/Tara Brandt). Grund: 2026 und 2027 enthielten bereits
Vorab-Daten aus Task 1–7, eine Mahnliste mit „genau einem offenen Posten" war damit
nicht herstellbar, **ohne** Finanzdaten zu löschen. Die `Vereinsdaten` wurden über
`/admin/verein/vereinsdaten/1/change/` ausgefüllt. Bestandsdaten in 2026/2027 wurden
nicht angefasst.

**Zustand am Ende:** 9 Beitragsposten 2028 über 576,00 €, davon 8 bezahlt, genau
1 offener Posten (Brandt, Nele · 42,00 €), darauf 1. und 2. Mahnung.

---

## 1. Abnahmekriterien aus `tasks/plan.md` (T10)

| Kriterium | Ergebnis | Messwert |
|---|---|---|
| Mahnbrief **druckbar** für ein Testmitglied | erfüllt | Druckknopf `<button type="button" onclick="window.print()">` vorhanden; `@media print` → `.werkzeug{display:none}`, `body{margin:0;max-width:none}`, `@page{margin:2cm}`; **im Bildschirm-Medium nachgemessen**: `werkzeug=display:none`, `bodyMargin=0px`, `bodyMaxWidth=none`; PDF-Datei `t8_brief.pdf`, **53.071 Byte** |
| CSV enthält **alle** Posten des Jahres | erfüllt | 2028: **10 Zeilen** = 1 Kopf + **9 von 9** Posten (`FeePost.objects.filter(jahr=2028).count()` = 9); 2026: 8 = 1 + 7; 2027: 8 = 1 + 7 |
| **403** für Nicht-Admin auf Mahnungsübersicht **und** Export | erfüllt | siehe Rollenmatrix §4 |
| CSV enthält **nur die erlaubten Felder** | erfüllt | Kopf = `Jahr;Nachname;Vorname;Kategorie;Beitrag;Bezahlt;Offen;Status;Mahnungen;1. Mahnung am;2. Mahnung am`; Suche nach `Straße`/`Strasse`/`PLZ`/`Turnierweg`/`Pruefweg`/`Musterstadt`/`example.org`/`0123`/`Geburtsdatum` in allen drei Exporten → `verboten: []` |
| **Zweiter Export identisch** | erfüllt | **664 Byte**, FNV-1a **`5728c242`** — drei aufeinanderfolgende Abrufe identisch (zwei in Runde 1, einer nach dem CSS-Rollback in Fix-Runde 1) |

## 2. Testlauf

`docker compose exec -T app pytest -q` → **390 passed, 4 subtests passed**
(Runde 1: 116,05 s · wiederholt am Ende der Runde: 67,02 s).
`manage.py check` → *System check identified no issues (0 silenced).*

Aufteilung T10 nach Testdatei: Models 8 · Services 36 · Export 17 · Views 48 ·
verein 8 = **117** in den fünf T10-Testdateien. Dazu kommen **2** Nav-Tests in
`core/tests/test_nav.py` (`test_admin_sees_mahnungen`, `test_member_sees_no_mahnungen`),
die der Commit `4480b64` (T10 Task 6) dort ergänzt hat → **119 Tests aus T10**.
Die Rechenkette geht damit auf: 271 (Ende T9, Commit `68af3bf`) + 119 = **390**.

## 3. Viewport-Messungen

Gemessen nach `set viewport <w> 900`, Dokumentbreite gegen Fensterbreite.

| Seite | 360 px | 768 px | 1280 px |
|---|---|---|---|
| **Mahnbrief** `/beitraege/mahnungen/17/` | `scrollWidth 360` / `clientWidth 360` → **kein Overflow** | `768 / 768` → **kein Overflow** | `1280 / 1280` → **kein Overflow** |
| **Mahnliste** `/beitraege/mahnungen/?jahr=2028` | `scrollWidth 360` / `clientWidth 360` → **kein Overflow** | `scrollWidth 973` / `clientWidth 768` → **205 px Overflow, siehe §3.1** | `1280 / 1280` → **kein Overflow** |

Zusatzwerte:

* Mahnbrief 360 px: Postentabelle **336 px** breit, `body.scrollWidth 360`.
* Mahnliste 360 px: `.table-wrap` `scrollWidth 772` bei Fenster 360 — die Tabelle
  scrollt **innerhalb** ihres Containers. Das ist das app-weite Muster aus `plan.md`
  („mobile-first, scrollbare Tabellen"), nicht seitenweiter Overflow.
* Mahnliste 1280 px: `.table-wrap` `scrollWidth 928`.

### 3.1 Gefundener Mangel: horizontaler Overflow 768–972 px (Basis-Template, nicht T10)

Bei 768 px scrollt das Dokument der Mahnliste um **205 px** nach rechts. Ursache
gemessen, nicht geraten — die Elemente, die über den Rand reichen:

| Element | Breite | `right` bei Fenster 768 |
|---|---|---|
| `DETAILS.nav-toggle` | 957 | **973** |
| `NAV` (Kopfmenü) | 957 | **973** |
| `A` „Verwaltung" | 95 | 880 |
| `FORM` / `BUTTON` „Abmelden" | 89 | **973** |

Der T10-Inhalt selbst ist **sauber**:

```
main.site-container   clientWidth 768   scrollWidth 768
.table-wrap          clientWidth 736   scrollWidth 736
.nav-toggle nav      Breite 957
```

Betroffen ist **jede** Seite mit `base.html` (gemessen: `/`, `/dashboard/`,
`/mitglieder/`, `/beitraege/`, `/beitraege/zahlungen/`, `/beitraege/mahnungen/` —
alle `scrollWidth 973 / clientWidth 768`, Nav 957 px). Der Mahnbrief ist nicht
betroffen, weil er ein eigenständiges Dokument ohne `base.html` ist.

**Band und Ursache:** Unterhalb von 768 px (`48rem`) zeigt `static/css/app.css:126-135`
das Burgermenü (`position: absolute`), es gibt keinen Overflow. Ab **genau 768 px**
schaltet `base.html:41-46` auf die horizontale Navigation um, und die 10
Admin-Menüpunkte ergeben **957 px** — das Dokument bleibt bis 973 px auf `scrollWidth
973` stehen. Gemessene Kante:

| Fenster | 768 | 800 | 900 | 960 | 973 | 980 | 1050 |
|---|---|---|---|---|---|---|---|
| `scrollWidth` | 973 | 973 | 973 | 973 | **973** | 980 | 1050 |

Overflow also für **768 px bis 972 px**; ab **973 px** passt die Admin-Navigation.

**Nur die Rolle `admin` ist betroffen.** Navigation der Rolle `mitglied`:
**231 px** → bei 768, 900, 972 und 973 px jeweils `scrollWidth == clientWidth`, kein
Overflow.

**Bewertung:** Vorgeschichte des Basis-Templates (T1/T2), nicht T10, und **nicht** durch
den Tailwind-Build verursacht: `base.html:14-27` trägt an der Navigation **keine**
Tailwind-Klasse, die Breite entsteht allein aus `static/css/app.css:43-78` und `:126-135`.
Für T10 nicht gefordert (dessen Abnahme verlangt 360 px und 1280 px, beides sauber) —
**aber** `plan.md:66` fordert 768 px, und der Wert steht im selben Regelwerk. Als
Mangel an T2 melden, nicht in T10 nachbessern: sinnvolle Kandidaten sind
`flex-wrap`/`overflow-x` an `.nav-toggle nav` oder eine höhere Breakpoint-Schwelle.

## 4. Rollenmatrix (Statuscodes aus dem echten Browser, `fetch` in eingeloggter Sitzung)

| URL | `admin` | `kapitaen` | `mitglied` |
|---|---|---|---|
| `/beitraege/mahnungen/?jahr=2028` | 200 | **403** | **403** |
| `/beitraege/mahnungen/17/` (Brief) | 200 | **403** | **403** |
| `/beitraege/export.csv?jahr=2028` | 200 | **403** | **403** |
| `POST /beitraege/mahnungen/17/setzen/` | 302 (Redirect) | **403** | **403** |
| `/beitraege/` | 200 | **403** | — |
| `/beitraege/zahlungen/` | 200 | **403** | — |

* **Nav:** `admin` sieht „Dashboard · Mitglieder · Änderungswünsche · Beiträge ·
  Zahlungen · **Mahnungen** · Verwaltung". `kapitaen` sieht nur
  **Startseite · Profil · Abmelden** — kein „Mahnungen", kein „Beiträge", kein „Zahlungen".
* **Kein Seiteneffekt der 403-Angriffe:** `Mahnung.objects.count()` vor und nach den
  POSTs unverändert; der 403-Body ist **135 Zeichen** und enthält keine CSV-Daten
  (`enthaelt_CSVkopf=false`).

## 5. Randfälle (im Browser beobachtet)

| Prüfung | Ergebnis |
|---|---|
| Brief für einen **bezahlten** Posten (15, 16, 18) | 404 / 404 / 404 |
| Brief für **unbekannten** Posten (999999) | 404 |
| `GET /beitraege/mahnungen/17/setzen/` | **405** |
| `?jahr=keinjahr` auf der Mahnliste | Weiterleitung auf die ungefilterte Liste (200) |

## 6. Durchlauf in der Oberfläche (Beobachtungsprotokoll)

1. `/beitraege/?jahr=2028` → Vorschau *„Neu zu buchen 9 · Beitragsposten über
   576,00 € · Bereits gebucht 0"*, dazu *„4 Mitglied(er) ohne Kategorie werden
   übersprungen"* und *„2 passive Mitglied(er) sind nicht einbezogen"*.
2. Knopf **„Beitragslauf 2028 ausführen"** → *„Beitragslauf 2028: 9 Beitragsposten
   über 576,00 € erzeugt."*
3. Acht Buchungen über `/beitraege/zahlungen/?jahr=2028&posten=<pk>` (Betrag vom Server
   vorbelegt, Datum und Referenz gesetzt, Knopf **„Zahlung buchen"**).
4. `/beitraege/mahnungen/?jahr=2028` → *„1 offene(r) Posten, zusammen 42,00 €"*, genau
   eine Zeile (Brandt, Nele), Knopf „CSV-Export 2028".
5. **„1. Mahnung setzen"**, Mahndatum 15.03.2028, Frist 15.04.2028 →
   *„1. Mahnung für Brandt, Nele gesetzt (Datum 15.03.2028)."*, Zeile danach
   *„1. Mahnung am 15.03.2028"*.
6. **„Mahnbrief"** → Brief mit Absenderblock, Empfängeranschrift, Datum 29.09.2026,
   Überschrift *„2. Mahnung — Beiträge 2028"*, Anrede, *„42,00 € offen … bis zum
   15.04.2028"*, Postentabelle, *„Offener Betrag 42,00 €"*, Zahlungshinweis,
   Verwendungszweck, Grußformel mit Kassierer.
7. **„2. Mahnung setzen"**, Mahndatum 30.03.2028 → *„2. Mahnung für Brandt, Nele
   gesetzt (Datum 30.03.2028)."*; danach enthält die Aktionsspalte **kein `<form>`
   mehr**, nur den Brief-Link und „Stufen ausgeschöpft". Die Brief-Überschrift lautet
   nun *„Beiträge 2028"* — das interne Steuerwort `ausgeschöpft` kommt im Dokument
   **nicht** vor.

**Interne Notiz geprüft:** `Mahnung 1.notiz` wurde auf
`'Rueckruf Dienstag 10 Uhr, Vorstand intern'` gesetzt (über `manage.py shell`, weil die
Oberfläche kein Feld dafür anbietet — siehe §7), danach der Brief neu geladen und das
**vollständige gerenderte HTML** durchsucht:

```json
{"html_enthaelt_notiz": false, "body_enthaelt_notiz": false, "status_text": false}
```

## 7. Was die Abnahme **nicht** belegt

* **Das PDF wurde nicht angesehen.** `agent-browser pdf` erzeugte eine Datei
  (53.071 Byte); das Modell unterstützt keinen PDF-Input. Ersatzweise wurden die
  `@media print`-Regeln im Bildschirm-Medium gemessen (§1). Eine menschliche Sichtung
  des Ausdrucks steht aus.
* **Die interne Notiz hat in der Oberfläche kein Eingabefeld.** `Mahnung.notiz` ist
  Modellfeld, `mahnungen_setzen(..., notiz=…)` nimmt sie entgegen und `mahnung_setzen`
  liest sie aus dem POST — aber `dues/templates/dues/mahnliste.html:58-64` bietet nur
  `stufe`, `datum`, `frist`, und `MahnungAdmin` ist mit
  `readonly_fields = [alle Felder]` sowie `has_add_permission = False` vollständig
  schreibgeschützt. Die Zusage „interne Notiz erscheint nicht im Brief" (§6) ist damit
  im Betrieb nicht ausnutzbar: es gibt keine Notiz, die in den Brief geraten könnte.
* **Testdaten stehen in der Entwicklungs-DB** (Benutzer `t8check`, Prüfmitglieder 14–16,
  Kategorie „Abnahme-Test", 2028er Beitragssätze). Bewusst nicht gelöscht — vor dem
  ersten Produktivlauf aufräumen.
* **`npm run build:css` wurde zurückgenommen.** `static/css/tailwind.css` ist auf dem
  Stand vor dem Abnahme-Build (`b8514e4`). Grund: der Build fügte `.sr-only`,
  `.table`, `.border-collapse`, `.border` hinzu — Utilities, die **kein** Element der
  Anwendung verwendet. Sie stammen aus Planungs- und Report-Markdown: Tailwinds
  automatische Quellenerkennung scannt in diesem Repo `.md`-Dateien mit, und jedes
  Wort, das zufällig ein gültiger Utility-Name ist, wird zu CSS (mit
  `tracking-tight` und `backdrop-blur-md` gegen eine temporäre Probendatei in `docs/`
  reproduziert; ein frei erfundenes Wort wird ignoriert). Für die Darstellung ist das
  folgenlos — alle von Mahnliste und Mahnbrief benutzten Klassen stammen aus
  `static/css/app.css` —, aber totes CSS gehört nicht ins Produktionsartefakt.
  **Regel für Folge-Tasks:** den Tailwind-Build nur ausführen, wenn Templates
  tatsächlich Utilities tragen.
