# ADR-025: Hosting- und Datenschutzversprechen auf EU-Ebene (Scalingo PaaS & DSGVO)

## Status

Accepted (harmonisiert und präzisiert PRD N1.1, ADR-009, ADR-014 und ADR-018)

## Date

2026-10-17

## Context

Das Lastenheft ([PRD](file:///C:/Users/xyxyx/Desktop/development/docs/prd.md) §2 und N1.1) definiert als nicht-funktionale Anforderung an den Datenschutz:
> „N1.1 Datenhaltung nur in EU/DE; keine Drittanbieter-Tracker, kein externes CDN.“

In nachgelagerten Marketing-Texten (`core/produkt.py`), der Landingpage (`core/templates/core/produkt.html`), dem AVV-Muster (`docs/avv_muster.md`) sowie Vertriebsvorlagen hatte sich diese Aussage jedoch stellenweise auf *„100 % Deutschland“* bzw. *„Datenhaltung ausschließlich in Deutschland“* verengt.

In der Praxis wird die Plattform für Kunden- und Pilotvereine auf dem europäischen PaaS-Anbieter **Scalingo** (*Scalingo SAS*, 15 avenue du Rhin, 67100 Strasbourg, Frankreich) bereitgestellt ([docs/deployment.md](file:///C:/Users/xyxyx/Desktop/development/docs/deployment.md)). Das primäre Deployment nutzt die Region *Europe (Paris / `osc-fr1`)* bzw. Frankfurt (`osc-cl1`).

Ein Werbe- oder Vertragsversprechen wie *„100 % Deutschland“* oder *„Hosting ausschließlich in Deutschland“* birgt bei Betrieb über einen französischen Anbieter mit Rechenzentrumsregion in Paris wettbewerbsrechtliche Abmahnrisiken (§ 5 UWG) und steht im Widerspruch zur Auftragsverarbeitungsvereinbarung (AVV).

Die DSGVO (GDPR) gilt als europäische Verordnung unmittelbar und mit identischem Schutzstandard in allen EU-Mitgliedstaaten. Der entscheidende Vertrauens- und Sicherheitsfaktor für ehrenamtliche Vereinsvorstände ist:
1. **100 % DSGVO-Konformität** mit AVV gem. Art. 28 DSGVO.
2. **Europäische Daten-Souveränität** (EU-Anbieter, ISO-27001-Zertifizierung).
3. **Keine US-Hyperscaler** (kein AWS, Azure, Google Cloud $\rightarrow$ kein US CLOUD Act, keine Datenübermittlung in Drittstaaten gem. Art. 44 ff. DSGVO).
4. **Keine fremden Tracking-Skripte oder externen CDNs**.

## Decision

1. **Harmonisierung der Leistungs- und Marketingversprechen auf EU-Ebene:**
   - Auf der Produkt-Landingpage (`/` bzw. `/produkt/`), in Metatags und Broschüren wird einheitlich mit **„100 % EU-Hosting (DSGVO & Datenschutz)“** bzw. **„Hosting & Datenhaltung in der EU“** geworben.
   - Die Zielgruppenansprache bleibt unverändert auf Schachvereine in Deutschland und der DACH-Region ausgerichtet (*„Für Schachvereine in Deutschland“*), da die fachlichen Module (DSB, DWZ, SEPA, AO) spezifisch hierfür ausgelegt sind.

2. **Aufnahme von Scalingo in die AVV- und Pilotunterlagen:**
   - Im Muster-Auftragsverarbeitungsvertrag ([docs/avv_muster.md](file:///C:/Users/xyxyx/Desktop/development/docs/avv_muster.md)) wird **Scalingo SAS** als primärer europäischer Unterauftragsverarbeiter für die Cloud-Plattform (PaaS) mit Rechenzentren in der Europäischen Union (Frankreich/Deutschland) ausgewiesen.
   - **Hetzner Online GmbH** verbleibt als Unterauftragsverarbeiter für dedizierte Server-/Self-Hosting-Optionen und Offsite-Backups.
   - In der Pilotvereinbarung ([docs/pilotvereinbarung_muster.md](file:///C:/Users/xyxyx/Desktop/development/docs/pilotvereinbarung_muster.md)) wird der Serverstandort verbindlich auf die *Europäische Union (EU)* festgeschrieben.

3. **Dokumentation & Deployment:**
   - [docs/deployment.md](file:///C:/Users/xyxyx/Desktop/development/docs/deployment.md) und [docs/einfuehrung_testverein.md](file:///C:/Users/xyxyx/Desktop/development/docs/einfuehrung_testverein.md) spiegeln die hybride Eignung wider (Scalingo PaaS als Cloud-Betriebsmodell, Docker Compose auf Hetzner/Netcup als Self-Hosting-Modell).

## Consequences

- **Rechtssicherheit:** Vollständige Übereinstimmung zwischen technischer Infrastruktur, vertraglichen Pflichten (AVV) und Werbeaussagen ohne wettbewerbsrechtliche Risiken.
- **DSGVO-Garantie:** Das hohe Datenschutzniveau (keine Drittstaatenübermittlung, keine US-Dienste, verschlüsselte IBANs, keine Tracker) bleibt uneingeschränkt gewahrt.
- **Flexibilität:** Vereine können flexibel auf Scalingo (Frankreich/Deutschland) oder dedizierten EU-Servern (z. B. Hetzner) betrieben werden.
