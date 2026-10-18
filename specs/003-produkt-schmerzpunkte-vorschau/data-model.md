# Data Model: Schmerzpunkte, Lösungen & Interaktive Vorschau

**Feature**: `003-produkt-schmerzpunkte-vorschau`  
**Date**: 2026-10-17  
**Status**: Specified  

---

## Übersicht

Die Daten für die Schmerzpunkte, Lösungen und die interaktive Vorschau auf `/produkt` werden rein konfigurationsbasiert in `core/produkt.py` geführt. Sie dienen als statische Inhaltsquelle für die Landingpage, sodass Texte, Kennzahlen und simulierte Interface-Ausschnitte ohne Datenbankabfragen performant gerendert werden.

```text
┌────────────────────────────────────────────────────────┐
│                      RollenProfil                      │
│────────────────────────────────────────────────────────│
│ + id: str (Slug)                                       │
│ + titel: str                                           │
│ + kurztitel: str                                       │
│ + icon: str                                            │
│ + slogan: str                                          │
│ + ersparnis: str                                       │
│ + schmerzpunkte: List[Schmerzpunkt]                    │
│ + vorschau: VorschauMockup                             │
└────────────────────────────────────────────────────────┘
                    │                      │
         1..*       │                      │ 1..1
                    ▼                      ▼
┌───────────────────────────┐  ┌─────────────────────────┐
│        Schmerzpunkt       │  │     VorschauMockup      │
│───────────────────────────│  │─────────────────────────│
│ + titel: str              │  │ + typ: str              │
│ + problem: str (Vorher)   │  │ + titel: str            │
│ + loesung: str (Mit App)  │  │ + status: str           │
│ + detail: str             │  │ + metriken: List[Badge] │
└───────────────────────────┘  │ + elemente: List[Item]  │
                               │ + schalter: List[Toggle]│
                               └─────────────────────────┘
```

---

## 1. Entitäten & Schemas

### 1.1 `RollenProfil` (`RoleProfile`)

Definiert eine Zielgruppen-Rolle im Schachverein samt ihrer spezifischen Herausforderungen und Vorteile.

| Feld | Typ | Pflicht | Beschreibung / Validierungsregel |
|---|---|---|---|
| `id` | `str` | Ja | Einzigartiger Bezeichner (`vorstand`, `kassenwart`, `spielleiter`, `kapitaen`, `mitglieder`). Kleinbuchstaben, nur a–z. |
| `titel` | `str` | Ja | Offizielle Bezeichnung (z. B. `1. Vorsitzender & Vorstand`). |
| `kurztitel` | `str` | Ja | Kompakter Titel für Navigation/Tabs (z. B. `Vorstand`). Max. 20 Zeichen. |
| `icon` | `str` | Ja | Name eines vorhandenen SVG-Icons im Sprite (`shield`, `wallet`, `trophy`, `flag`, `users`). |
| `slogan` | `str` | Ja | Prägnanter Einstiegssatz zum Kernproblem der Rolle. |
| `ersparnis` | `str` | Ja | Quantifizierter Nutzenwert (z. B. `~15 Stunden pro Beitragslauf`, `100 % DSGVO-konform`). |
| `schmerzpunkte` | `list[dict]` | Ja | Mindestens 3 konkrete Schmerzpunkte (siehe `Schmerzpunkt`). |
| `vorschau` | `dict` | Ja | Spezifikation der interaktiven Simulation (siehe `VorschauMockup`). |

---

### 1.2 `Schmerzpunkt` (`PainPoint`)

Repräsentiert die Gegenüberstellung von typischem Problem („Vorher“) und Lösung durch die Software („Mit Schachverwaltung“).

| Feld | Typ | Pflicht | Beschreibung / Validierungsregel |
|---|---|---|---|
| `titel` | `str` | Ja | Überschrift des Schmerzpunkts (z. B. `Vorstandsübergabe ohne Datenverlust`). |
| `problem` | `str` | Ja | Das konkrete Frustszenario ohne die App (z. B. `Excel-Dateien auf privaten Laptops, Passwörter auf Zetteln, Vorstandswechsel scheitert fast`). |
| `loesung` | `str` | Ja | Wie die App das Problem löst (z. B. `Zentrales System mit Rollenrechten, lückenloser AuditLog, 1-Klick-Übergabe an den Nachfolger`). |
| `detail` | `str` | Nein | Zusätzliche Erklärung oder Verweis auf eine konkrete App-Funktion. |

---

### 1.3 `VorschauMockup` (`PreviewMockup`)

Konfiguriert die interaktive Simulationsoberfläche für die gewählte Rolle.

| Feld | Typ | Pflicht | Beschreibung / Validierungsregel |
|---|---|---|---|
| `typ` | `str` | Ja | Typ der Simulation: `dashboard`, `sepa`, `turnier`, `aufstellung`, `dsgvo`. |
| `fenster_titel` | `str` | Ja | Titel in der simulierten App-Menüleiste (z. B. `Beitragswesen – SEPA-Lauf`). |
| `status_badge` | `str` | Ja | Statusanzeige (z. B. `Vorschau`, `Bereit für Bank`, `Runde 2 ausgelost`). |
| `metriken` | `list[dict]` | Ja | 2 bis 3 Kennzahlen-Kacheln (`{"label": str, "wert": str, "status": "ok"|"warn"|"info"}`). |
| `zeilen` | `list[dict]` | Ja | Simulierte Tabellen- oder Listeneinträge (z. B. Beitragszahler, Paarungen, Spieler). |
| `aktionen` | `list[dict]` | Nein | Schaltbare Interaktionen im Mockup (z. B. Stufe 1/2/3, Runde 1/2). |

---

## 2. Standard-Rollen und Datensätze

1. **`vorstand`**
   - *Fokus*: Übergabe, Haftungsrisiken, Satzung, DSGVO Art. 15.
   - *Ersparnis*: Stressfreie Vorstandsübergabe, 0 Haftungsrisiko bei Auskunftsersuchen.
   - *Mockup-Typ*: `dashboard` / `dsgvo` (Audit-Protokoll, Datenauskunft per Klick).

2. **`kassenwart`**
   - *Fokus*: SEPA-Lastschriften (pain.008), Mahnungen, Beitragsstatus, Kassenprüfung.
   - *Ersparnis*: ~15 Stunden Zeitersparnis pro Beitragseinzug.
   - *Mockup-Typ*: `sepa` (Beitragslauf mit offenen Posten, XML-Download, Mahnstufen).

3. **`spielleiter`**
   - *Fokus*: Schweizer System, DWZ-Listen, Paarungschaos am Spielabend, Ergebniserfassung.
   - *Ersparnis*: 45 Minuten Hektik pro Spielabend eingespart.
   - *Mockup-Typ*: `turnier` (Schweizer-System-Auslosung, Paarungstisch, Ergebnisticker).

4. **`kapitaen`**
   - *Fokus*: Mannschaftsaufstellung, DWZ-Reihenfolge, Ersatzspielerregeln, Spielberichtsbogen.
   - *Ersparnis*: Keine Fehlaufstellungen mehr, Spielbericht in 2 Minuten fertig.
   - *Mockup-Typ*: `aufstellung` (Brettaufstellung 1–8 mit automatischer Gültigkeitsprüfung).

5. **`mitglieder`**
   - *Fokus*: Keine Einsicht in Stammdaten, Adressänderungen per Papier, unübersichtliche Termine.
   - *Ersparnis*: 100 % mobile Einsicht, iCal-Kalender auf dem Smartphone.
   - *Mockup-Typ*: `mitglied` (Mein Profil, Beitragsstatus, Terminkalender-Abo).
