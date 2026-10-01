# ADR-014: Preisgestaltung für das Managed-Angebot (drei Stufen, Jahresvertrag, Endpreise)

## Status

Accepted (Konzept). **Dieses ADR legt nur die Preise fest** — die Umsetzung in
`core/produkt.py`, `core/templates/core/produkt.html` und `README.md` folgt in einem
eigenen Schritt (siehe „Offene Punkte").

## Date

2026-10-01

## Context

Die Landingpage `/produkt/` trägt Platzhalterpreise (29 / 49 / 89 €, „zzgl. gesetzlicher
Umsatzsteuer", „keine Mindestlaufzeit"); `README.md` und `core/produkt.py` weisen
ausdrücklich darauf hin, dass die Preise vor dem Livegang festzulegen sind.

**Liefermodell (vom Auftraggeber festgelegt):** ausschließlich Managed-Abo — pro Verein
eine eigene Instanz mit eigener Datenbank, Hosting in Deutschland, Backups, Support.
Kein Self-Hosting, keine Einmallizenz.

**Marktgröße.** Der Deutsche Schachbund hat rund 89.400 Mitglieder in etwa 2.300 Vereinen
[1](https://www.schachbund.de/factsheet.html). Das sind **Ø ~39 Mitglieder pro Verein**.
Die Mehrheit des Marktes ist also klein — eine Stufe „ab 120 Mitglieder" ist eine Nische,
kein Volumensegment.

**Haushaltsrealität der Zielkunden.** Jahresbeiträge in Schachvereinen liegen typischerweise
zwischen 30 und 130 € (Beispiele: 90 € Erwachsene / 45 € Jugendliche
[2](https://scbb.de/verein/mitglied-werden/); 60 € / 40 € / 30 €
[4](https://schachverein-brilon.jimdofree.com/mitgliedschaft/); 50 € / 25 €
[5](https://www.aalen.schachvereine.de/verein/mitgliedschaft/)). Ein Verein mit 40
Mitgliedern hat damit einen Jahreshaushalt von grob **2.500–3.500 €**. 29 €/Monat = 348 €
wären > 10 % davon — für einen Kassenwart nicht argumentierbar.

**Wettbewerb (Vereinssoftware DE, 2026).** ClubDesk kostenlos bis 50 Mitglieder, dann
10,00 / 16,00 / 28,00 / 33,00 € pro Monat; WISO MeinVerein 10–50 € je nach Größe;
easyVerein ab etwa 7,14 € bis 41,99 € [1](https://omr.com/de/reviews/contenthub/beste-vereinssoftware-im-vergleich)[1](https://business.digital/tools/easyverein);
verein.cloud ab 6,90 €, campai ab 4,17 € [5](https://trusted.de/clubdesk-alternativen).
Die Commodity-Leistung „Mitgliederverwaltung" kostet damit **5–15 € pro Monat**.

**Kostenbasis.** Ein kleiner Cloud-Server kostet 3,79–6,80 € pro Monat
[1](https://www.hetzner.com/pressroom/new-cx-plans/); mehrere Vereinsinstanzen teilen sich
einen Host (ADR-009: Caddy + restic). Reale Stückkosten pro Verein und Monat:
Server-/Container-Anteil 2–3 €, Backup-Speicher 0,50–1 €, TLS/Domain/Monitoring ~0,20 €,
Zahlungsverkehr 0,20–0,50 €. **Der eigentliche Kostentreiber ist Arbeitszeit**:
Einrichtung 1,5–5 h, laufende Betreuung 1,5–4 h pro Jahr.

**Engpass ist Betreuungszeit, nicht Hardware.** Eine Preiskalkulation, die nur die
Serverkosten deckt, ist zu dünn; eine, die 24 Minuten Support pro Verein und Monat nicht
einpreist, ist falsch.

**Offene Frage aus der Abstimmung:** Umsatzsteuer (Kleinunternehmerregelung vs.
Regelbesteuerung) — unten eingeordnet.

## Decision

### 1. Das Modell

Managed-Abo mit drei Stufen nach **Vereinsgröße**. Staffelgrenze ist eine
*Planungsgrenze*, kein harter technischer Stopp: Wer darüber hinaus wächst, bekommt zum
nächsten Vertragsjahr ein Upgrade-Gespräch, keine Nachberechnung.

### 2. Die Preise

Alle Preise sind **Endpreise** (siehe Abschnitt 6). Standard ist die Jahreszahlung.

| Stufe | Zielgruppe | Jahreszahlung | monatliche Zahlung | Einrichtung & Datenübernahme |
|---|---|---:|---:|---|
| **Start** | bis 60 Mitglieder | **19 €/Monat** (228 €/Jahr) | 23 € | 99 € einmalig |
| **Verein** *(empfohlen)* | bis 150 Mitglieder, mit Spielbetrieb | **35 €/Monat** (420 €/Jahr) | 42 € | inklusive |
| **Verband** | 151–400 Mitglieder, mehrere Mannschaften | **69 €/Monat** (828 €/Jahr) | 82 € | inklusive + 90-Minuten-Einweisung |

Leistungsinhalte bleiben wie in `core/produkt.py` beschrieben; ergänzt werden:

- **Start:** Mitglieder, Beiträge, Kassenbuch, Turniere, öffentliche Vereinsseite,
  Backups, E-Mail-Support mit Reaktionszeit 3 Werktage.
- **Verein:** zusätzlich Mannschaften/Aufstellungen/Ligatabellen, Rundbriefe, 2FA für den
  Vorstand, **Einrichtung und Datenübernahme inklusive**, **Vorstandsübergabe** (eine
  Stunde Einweisung für den neu gewählten Vorstand, siehe Abschnitt 7).
- **Verband:** zusätzlich eigene Domain, persönliche Einweisung, bevorzugter Support,
  zweites Support-Konto für den Schriftführer.

### 3. Vertrags- und Zahlungsregeln

- **Laufzeit 12 Monate**, Verlängerung um weitere 12 Monate, Kündigung einen Monat vor
  Ablauf. (Rechtsprüfung der AGB vor dem Livegang; abweichend von der heutigen
  Formulierung „keine Mindestlaufzeit" — Begründung in Abschnitt 7.)
- **Zahlung per Rechnung**, Einzug per SEPA-Basislastschrift oder Überweisung.
  Jahreszahlung ist der Standardfall; monatliche Zahlung kostet **+20 %** (gerundet: 23 / 42 / 82 €) — sie deckt den
  realen Mehraufwand und macht die Jahreszahlung zur vernünftigen Wahl.
  Kein Kreditkarten-Zwang, kein Payment-Provider mit 2 % Gebühr auf Kleinstbeträge.
- **30 Tage Testen**: eigene Instanz mit Demo-Daten, keine Zahlungsdaten, keine
  Kündigungsfrist. Danach Entscheidung oder Löschung.
- **Preisgarantie:** Der Preis gilt für die Vertragslaufzeit. Anpassungen frühestens zum
  nächsten Vertragsjahr mit drei Monaten Vorankündigung; Bestandskunden behalten ihren
  Preis für mindestens 24 Monate.
- **Gründerpreis:** Die ersten zehn Vereine zahlen **29 €** statt 35 € in der Stufe
  „Verein", fest für 24 Monate — gegen Referenznennung und ein Feedback-Gespräch.
- **Mengenrabatt:** ab drei Instanzen eines Trägers (Spielgemeinschaft, Bezirk,
  Landesverband) 10 %, ab fünf 15 %. Empfehlung: ein Monat Gutschrift für Werber und
  Geworbenen — die Szene ist klein und vernetzt.
- **Kein Gemeinnützig-Rabatt:** alle Kunden sind gemeinnützig; ein Rabatt wäre nur eine
  Preisreduktion mit Umweg.
- **Datenhoheit:** CSV-Export jederzeit; nach Vertragsende bleibt die Instanz vier Wochen
  zum Export offen, Backups werden nach Fristablauf gelöscht.

### 4. Warum diese Zahlen

**Hybride Positionierung:** Der Einstieg liegt bewusst knapp über dem Commodity-Niveau,
die oberen Stufen deutlich darüber — getragen von Betreuung und schachspezifischen
Funktionen.

- **Nach unten:** Unter ~15 €/Monat trägt der Preis die Betreuungszeit nicht. Gegen
  campai (4,17 €) und verein.cloud (6,90 €) gewinnt man den Preiswettbewerb nicht — die
  brauchen Volumen, wir brauchen Deckungsbeitrag. Also nicht der Billigste sein, sondern
  der Passendste.
- **Nach oben:** Über ~80 €/Monat ist gegen „Excel plus zwei Ehrenamts-Abende" nicht mehr
  zu argumentieren. Der Kassenwart budgetiert realistisch 150–450 € pro Jahr für Software.
- **Der Aufpreis wird durch Schachspezifik getragen:** Mannschaften, Aufstellungen,
  Ligatabellen, Turniere mit Schweizer Paarung, DWZ-/ChessResults-Export. Keine der
  Standardlösungen kann das — dort liegt der Nutzen, nicht in der Mitgliederverwaltung.
- **Wertanker in der Kommunikation:** nicht „Mitgliederverwaltung" (Commodity ab 4 €),
  sondern „Vereinsbüro für Schachvereine, betrieben für Sie". Vergleichsgröße ist die
  Arbeitszeit des Kassenwarts (zwei Abende im Monat), nicht der Preis von ClubDesk.
- **Verkaufspsychologie:** „Start" ist der Anker nach unten, „Verein" ist der Standard.
  Fast jeder Verein mit Mannschaften landet in „Verein" — die Stufe ist so geschnitten,
  dass der Aufpreis durch den Wegfall der Einrichtungsgebühr erklärbar bleibt.

### 5. Kalkulation

Annahmen: Stundensatz 60 € netto (Opportunitätskosten), Einrichtung über 24 Monate
abgeschrieben (unterstellte Verweildauer).

**Kosten pro Verein und Monat**

| Position | Start | Verein | Verband |
|---|---:|---:|---:|
| Server-/Container-Anteil, Backup, TLS, Monitoring | 2,80 € | 3,30 € | 6,00 € |
| Zahlungsverkehr (jährliche Lastschrift) | 0,30 € | 0,30 € | 0,30 € |
| Laufende Betreuung (1,5 / 2 / 4 h pro Jahr) | 7,50 € | 10,00 € | 20,00 € |
| **Summe (Folgejahre)** | **10,60 €** | **13,60 €** | **26,30 €** |
| + Einrichtung (1,5 / 3 / 5 h, über 24 Monate) | 3,75 € | 7,50 € | 12,50 € |
| **Summe (Jahr 1)** | **14,35 €** | **21,10 €** | **38,80 €** |

**Deckungsbeitrag pro Verein und Monat**

| | Preis | Jahr 1 | Folgejahre | Marge (Folgejahre) |
|---|---:|---:|---:|---:|
| Start | 19 € | 4,65 € *(zzgl. 99 € Einrichtung)* | 8,40 € | 44 % |
| Verein | 35 € | 13,90 € | 21,40 € | 61 % |
| Verband | 69 € | 30,20 € | 42,70 € | 62 % |

Jahr 1 ist bei „Verein" und „Verband" bewusst knapp: Die Einrichtung ist „inklusive" und
verkauft die Stufe; sie amortisiert sich ab Monat 13.

**Szenarien** (Mix-Annahme 35 % Start, 50 % Verein, 15 % Verband → Ø 34,50 € Umsatz,
Ø 14,45 € Kosten, **Ø 20,05 € Deckungsbeitrag** pro Verein und Monat):

| Vereine | Umsatz/Monat | Umsatz/Jahr | Deckungsbeitrag/Monat | Betreuungsaufwand |
|---:|---:|---:|---:|---:|
| 20 | 690 € | 8,3 T€ | ~400 € | ~45 h/Jahr |
| 50 | 1.725 € | 20,7 T€ | ~1.000 € | ~105 h/Jahr |
| 100 | 3.450 € | 41,4 T€ | ~2.005 € | ~215 h/Jahr |
| 200 | 6.900 € | 82,8 T€ | ~4.010 € | ~425 h/Jahr |

**Der stärkste Hebel ist der Preis, nicht die Verkaufsmenge:** 5 € mehr pro Verein und
Monat bringen bei 50 Vereinen 250 €/Monat zusätzlich — ohne eine Minute Mehrarbeit.
Preiserhöhungen für Neukunden sind billiger als Akquise.

### 6. Umsatzsteuer: Einordnung und Empfehlung

**Die Regel (ab 2025):** Kleinunternehmer nach § 19 UStG ist, wessen Gesamtumsatz im
Vorjahr **25.000 €** nicht überstiegen hat und im laufenden Jahr **100.000 €** nicht
übersteigt [1](https://kleinbooks.de/blog/kleinunternehmerregelung-19-ustg/)[2](https://www.steuerberater-es.de/wissen/kleinunternehmerregelung-2026/).
Folgen: Umsätze sind echt steuerfrei, **keine Umsatzsteuer auf der Rechnung**, kein
Vorsteuerabzug, Hinweis auf der Rechnung. Wird die 100.000-€-Grenze im laufenden Jahr
überschritten, endet die Befreiung **sofort ab dem grenzüberschreitenden Umsatz** (früher
erst zum Jahresende) [2](https://www.steuerberater-es.de/wissen/kleinunternehmerregelung-2026/).
Ein Verzicht auf die Regelung (§ 19 Abs. 3) bindet fünf Jahre.

**Kundenperspektive:** Ein Verein kann Vorsteuer nur ziehen, wenn er selbst Unternehmer
mit steuerpflichtigen Umsätzen ist und nicht unter § 19 UStG fällt. Bei reinen
Schachvereinen mit Beitragswirtschaft ist das **häufig nicht der Fall** — die Umsatzsteuer
ist für sie ein echter Kostenfaktor, kein Durchlaufposten. Das ist der entscheidende Punkt:
Für den Kassenwart zählt der Bruttobetrag.

**Empfehlung: Start in der Kleinunternehmerregelung, Preise als Endpreise.**

- 19 / 35 / 69 € brutto entsprechen einem Nettoäquivalent von 15,97 / 29,41 / 57,98 €.
  Wir bekommen den vollen Betrag, der Verein zahlt keinen Aufschlag — bei gleichem
  Bruttopreis sind wir damit 19 % günstiger als mit „zzgl. USt".
- Die 100.000-€-Grenze entspricht bei diesem Mix **rund 240 Vereinen**
  (200 Vereine = 82,8 T€). Die Regelung trägt die gesamte realistische Wachstumsphase.
- Vorsteuerabzug lohnt bei Serverkosten von ~30 €/Monat (~5 € Vorsteuer) nicht — erst
  recht nicht mit der fünfjährigen Bindung des Verzichts.
- **Rechtzeitig planen:** Bei absehbar > 60 T€ Jahresumsatz (Q4 vorher) den Wechsel
  vorbereiten und die Preisanpassungsklausel ziehen. Ohne Klausel frisst der Wechsel
  19 % der Marge; mit Klausel („Endpreise; bei Wechsel zur Regelbesteuerung erhöhen sie
  sich um die gesetzliche Umsatzsteuer") bleibt der Bruttopreis erhalten.
- Auf jeder Rechnung: „Gemäß § 19 UStG wird keine Umsatzsteuer berechnet."

### 7. Churn: der Gegner ist die Vorstandswahl, nicht der Preis

Vereinssoftware wird nicht gekündigt, weil sie 5 € teurer ist, sondern weil ein neuer
Kassenwart „sein" Excel oder „sein" Tool mitbringt — typischerweise nach der
Jahreshauptversammlung. Deshalb:

- **12 Monate Laufzeit statt monatlicher Kündigung:** Sie überbrückt genau diesen Zyklus
  und gibt dem neuen Vorstand Zeit, den Nutzen zu sehen. Wer monatlich kündigen kann,
  verliert im Frühjahr nach der Wahl. (Vertrauens-Alternative, falls die Laufzeit im
  Verkauf bremst: monatliche Kündigung behalten, aber Jahresvorauszahlung mit zwei
  Gratismonaten bepreisen — dann 12 Monate zum Preis von 10.)
- **Zwei Admins pro Verein** einrichten, nicht einen — der Kassenwart allein ist ein
  Single Point of Failure.
- **Vorstandsübergabe als Leistung** in „Verein" und „Verband": eine Stunde Einweisung
  für die Nachfolge. Das ist billiger als jede Neukundenakquise.
- Vertragsbeginn nach Möglichkeit auf das Vereinsjahr legen (meist Kalenderjahr).

## Alternatives Considered

### Platzhalter 29 / 49 / 89 € netto beibehalten
- Pros: kein Änderungsaufwand; hohe Marge pro Verein.
- Cons: 29 € netto = 34,51 € brutto = 414 €/Jahr — bei Ø 39 Mitgliedern über 10 % des
  Vereinshaushalts und damit über dem Markt, ohne dass die Aufpreis-Gründe (Schachspezifik,
  Einrichtung, Betreuung) auf der Seite stehen.
- Rejected: preislich über der Zahlungsbereitschaft des Kernmarkts.

### Kampfpreis 5–9 €/Monat (Volumenstrategie)
- Pros: schneller Markteintritt, wenig Erklärungsbedarf.
- Cons: deckt die Betreuungszeit nicht; der Wettbewerb (campai, verein.cloud) ist
  strukturell billiger und hat Volumen. 50 Vereine brächten ~250 €/Monat Deckungsbeitrag
  bei vollem Haftungs- und Support-Risiko.
- Rejected.

### Preis pro Mitglied (z. B. 0,30 €/Mitglied/Monat, Minimum 12 €)
- Pros: skaliert automatisch mit dem Nutzen; ein 40-Mitglieder-Verein zahlt 12 €, ein
  150er-Verein 45 €; faire Abstufung ohne Stufen.
- Cons: Vereine melden zu wenige Mitglieder; die Rechnungshöhe schwankt; schwerer zu
  kommunizieren als drei Kästchen; Mitbewerber werden genau für Mitgliederstaffeln
  kritisiert [1](https://omr.com/de/reviews/contenthub/beste-vereinssoftware-im-vergleich).
- Rejected als Primärmodell; **merken als Fallback**, falls die Stufengrenzen im Verkauf
  dauernd diskutiert werden.

### Freemium (kostenlos bis 20–50 Mitglieder)
- Pros: Reichweite in einer kleinen Szene; ClubDesk macht das erfolgreich.
- Cons: volle Betriebs- und Supportkosten ohne Gegenfinanzierung; Testinstanzen bleiben
  liegen; der Zahlungssprung von 0 auf 35 € ist größer als von 0 auf 19 €.
- Rejected zugunsten einer 30-tägigen Testphase.

### Einrichtung in allen Stufen inklusive (keine Einrichtungsgebühr)
- Pros: eine Zahl pro Stufe, weniger Einwände im Erstgespräch.
- Cons: Die Einrichtungsgebühr ist ein Filter gegen Unverbindlichkeit und hält den
  monatlichen Anker niedrig; 99 € einmalig kann ein Kassenwart allein freigeben, 228 €
  pro Jahr braucht einen Vorstandsbeschluss.
- Rejected für „Start" (dort 99 €), angenommen für „Verein" und „Verband" — dort ist die
  „inklusive"-Botschaft den Aufpreis wert.

### Einmallizenz / Self-Hosting
- Vom Auftraggeber nicht gewünscht. Zusätzlich: entfällt der AVV-Vorteil, und
  Support-Aufwand ohne laufende Einnahme. Rejected.

## Consequences

- Die Zahlen gelten als **Endpreise**; die Landingpage-Formulierung „Preise zzgl.
  gesetzlicher Umsatzsteuer" ist damit überholt und muss ersetzt werden.
- Die Aussage „keine Mindestlaufzeit" ist überholt (Abschnitt 7).
- Preisspielraum nach unten ist durch Arbeitszeit, nach oben durch das Vereinsbudget
  begrenzt. Anpassungen nur zum Vertragsjahr, nie unterjährig.
- Die Marge entsteht im zweiten Jahr. Das macht Verweildauer zur wichtigsten
  Geschäftsgröße — wichtiger als die Neukundenzahl.
- Die Kalkulation steht und fällt mit der Annahme „≤ 0,2 h Betreuung pro Verein und
  Monat". Wird sie dauerhaft überschritten, ist die Antwort eine Preiserhöhung, nicht
  mehr Verkauf.

## Offene Punkte

Umsetzung: **Punkte 1–4 sind erledigt** (`core/produkt.py` mit `PREISHINWEIS` und den
Feldern `jahr`/`preis_monatlich`/`einrichtung`, Preiskarten und Kopfbereich im Template,
FAQ auf zwölf Fragen erweitert, README aktualisiert). Die Regeln werden durch
Negativtests in `core/tests/test_produkt.py` gegen ein Zurückrutschen in die alten
Formulierungen („zzgl. gesetzlicher Umsatzsteuer", „keine Mindestlaufzeit") abgesichert.

Noch offen:

5. Vor dem Livegang: Impressum, Datenschutzerklärung, AVV-Vorlage, AGB-Prüfung der
   Laufzeitklausel (12 Monate, Verlängerung, Kündigungsfrist).
6. Gründerpreis (29 € für die ersten zehn Vereine) ist beschlossen, aber noch nicht auf
   der Seite sichtbar — bewusst: er wird im Gespräch vergeben, nicht öffentlich
   ausgeschrieben.

**Review-Trigger:**

| Auslöser | Handlung |
|---|---|
| Nach 10 Vereinen oder 6 Monaten | Betreuungsstunden pro Verein auswerten; Ziel ≤ 0,2 h/Monat |
| Ø > 0,35 h/Monat über 6 Monate | Preise anheben oder in Doku/Self-Service investieren |
| Jahresumsatz > 60 T€ | Wechsel zur Regelbesteuerung vorbereiten, Preisklausel ziehen |
| > 3 Anfragen nach Self-Hosting | Modell erneut prüfen |
| jedes Jahr zum 1.10. | Preisrunde für Neukunden |
