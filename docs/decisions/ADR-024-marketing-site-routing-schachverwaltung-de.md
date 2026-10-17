# ADR-024: Marketing-Routing und Produkt-Landingpage auf der Hauptdomain (`schachverwaltung.de`)

## Status

Accepted

## Date

2026-10-17

## Context

Das Gesamtsystem bedient zwei unterschiedliche Nutzungskontexte:
1. **Zentraler Plattform- und Vertriebsauftritt (`schachverwaltung.de`):**
   - Auf der Hauptdomain informieren sich fremde Vereinsvorstände und Kassenwarte über das Angebot.
   - Besucher erwarten hier auf der Wurzelroute `/` die Produkt-Landingpage (`/produkt/`) mit Nutzenversprechen, Funktionen, Preisstufen (ADR-014) und Demo-Anfrage.
2. **Kunden- und Vereinsinstanzen (`[verein].schachverwaltung.de` oder eigene Vereinsdomain):**
   - Eigene Mitglieder, Eltern und Gastspieler erwarten hier die Vereinshomepage (oder bei inaktivem Homepage-Modul direkt den Login / das Dashboard, siehe ADR-023).
   - Eine kommerzielle Verkaufsseite auf `/` wäre für den Vereinsbetrieb unpassend.

Bislang lag die Produkt-Landingpage fest unter `/produkt/`, während `/` immer die Vereinsseite war.

## Decision

1. **Hybride Weiche für Marketing-Routing (`core/services.py:is_marketing_site`):**
   - Die Wurzelroute `/` (`core:home`) prüft vor Auslieferung der Vereinsseite `is_marketing_site(request)`:
     - **Hostname-Erkennung:** Trifft der Request auf `PRODUCT_HOSTS` ein (Standard: `schachverwaltung.de`, `www.schachverwaltung.de`), wird direkt die Produkt-Landingpage (`produkt_seite`) ausgeliefert.
     - **Einstellungs-Override:** Ist `IS_MARKETING_SITE=True` in den Django-Settings gesetzt (z. B. auf einer dedizierten Marketing-Instanz via `IS_MARKETING_SITE=1` in `.env`), wird `/` ebenfalls als Produkt-Landingpage gerendert.
     - **Vereins-Instanzen:** Bei Zugriff über Vereins-Subdomains (z. B. `musterstadt.schachverwaltung.de`) oder eigene Domains bleibt das reguläre Vereinsrouting aktiv (Vereinshomepage oder Dashboard/Login-Weiterleitung gemäß ADR-023).

2. **Koexistenz der Routen:**
   - Die Route `/produkt/` bleibt für alle Mandanten und zu Testzwecken weiterhin explizit erreichbar.
   - Der Anmelde-Link im Header der Marketing-Seite führt direkt zu `/anmelden/` (`core:login`).

3. **Konfiguration in `config/settings.py`:**
   - `IS_MARKETING_SITE = os.environ.get("IS_MARKETING_SITE", "0") in ("1", "true", "True")`
   - `PRODUCT_HOSTS = [h.strip().lower() for h in os.environ.get("PRODUCT_HOSTS", "schachverwaltung.de,www.schachverwaltung.de").split(",") if h.strip()]`
   - `ALLOWED_HOSTS` enthält standardmäßig `schachverwaltung.de` und `.schachverwaltung.de`.

## Consequences

- Klare funktionale Trennung zwischen Verkaufsplattform und Vereinsbetrieb ohne Code-Duplizierung.
- Nahtlose Akquise auf `schachverwaltung.de` ohne Irritation von Vereinsmitgliedern auf Kundeninstanzen.
- 100 % abwärtskompatibel: Für bestehende Vereinsinstanzen ändert sich am gewohnten Ablauf nichts.
