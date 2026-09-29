# ADR-001: Django + PostgreSQL + serverseitige Templates

## Status
Accepted

## Date
2026-09-28

## Context
Selbst gehostete Vereinsverwaltung für < 200 Mitglieder, ≤ 20 gleichzeitige Nutzer, Single-Tenant. Der Betreiber kennt Django noch nicht und braucht möglichst wenig Framework-Wissen im Alltag. Der Vorstand soll Stammdaten weitgehend über fertige Oberflächen pflegen.

## Decision
- **Backend:** Django 5 (Admin, Auth, CSRF, ORM).
- **Datenbank:** PostgreSQL.
- **Frontend:** serverseitig gerenderte Django Templates + Tailwind (lokaler Build, kein CDN). Keine SPA.
- **Deployment:** Docker Compose auf vereinseigenem Server.
- **Rollen:** Django Groups (`admin`, `kapitaen`, `mitglied`), keine eigene Permission-Engine; verbindliche Matrix in PRD §3.8.
- Views bleiben einfache Function-Based Views; der Django-Admin übernimmt einen großen Teil der Verwaltungs-UI.

## Alternatives Considered

### SPA (React/Vue) + API
- Pros: flexible Oberfläche.
- Cons: zweiter Codestand, Node-Build im Betrieb, mehr Angriffsfläche und Wartung für einen Ein-Personen-Betrieb.
- Rejected: Nutzen steht in keinem Verhältnis zum Aufwand.

### Anderes Python-/PHP-Framework
- Rejected: Django liefert Admin, Auth und CSRF ohne Zusatzpakete; das reduziert Abhängigkeiten.

## Consequences
- Wenig Zusatzpakete, geringe Wartungslast.
- Der Betreiber muss Django-Grundlagen lernen → Wartungsdoku ist Pflicht (`docs/wartung.md`, siehe Risiko im Plan).
- Kein externes CDN oder Drittanbieter-Font (unterstützt N1.1).
