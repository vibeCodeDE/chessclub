#!/usr/bin/env python
"""Build-Schritt für Vercel (``buildCommand`` in ``vercel.json``).

Läuft nach der Paketinstallation und vor dem Deploy. Die Funktion selbst kann
nicht migrieren (kurzlebig, schreibgeschütztes Dateisystem) – deshalb passiert
das hier, solange die Datenbank schon erreichbar ist:

* ``manage.py migrate`` im Production-Build. Preview-Builds teilen sich meist
  die Datenbank mit Production und migrieren nur mit ``MIGRATE_ON_BUILD=1``.
* ``manage.py seed_demo`` bei ``SEED_DEMO=1``. Der Befehl legt nur Daten an,
  solange noch keine Mitglieder existieren – ein erneuter Build ist harmlos.

Ohne Datenbank-URL (``DATABASE_URL``) tut das Skript nichts außer einem
deutlichen Hinweis im Build-Log; ebenso warnt es vor fehlendem
``DJANGO_SECRET_KEY``. Ein fehlgeschlagener Schritt bricht den Build ab;
Vercel behält dann die bisherige Version online.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Direkte Verbindung zuerst: Migrationen vertragen keinen Transaction-Pooler.
URL_VARIABLEN = (
    "DATABASE_URL_UNPOOLED",
    "POSTGRES_URL_NON_POOLING",
    "DATABASE_URL",
    "POSTGRES_URL",
)


def datenbank_url(env):
    """Erste gesetzte Datenbank-URL (direkte Verbindung vor Pooler) oder ``None``."""
    for name in URL_VARIABLEN:
        if env.get(name):
            return env[name]
    return None


def warnungen(env):
    """Hinweise, die den Build nicht stoppen, aber im Log auffallen sollen."""
    if env.get("DJANGO_SECRET_KEY", "") in ("", "dev-insecure-key"):
        return [
            "WARNUNG: DJANGO_SECRET_KEY ist nicht gesetzt – es gilt der öffentlich bekannte "
            "Entwicklungsschlüssel. Bitte in Vercel unter Settings → Environment Variables setzen."
        ]
    return []


def plan(env):
    """Entscheidet, was der Build tut: ``(hinweis, schritte)``.

    Jeder Schritt ist der Argumentvektor eines ``manage.py``-Aufrufs.
    """
    if not datenbank_url(env):
        return (
            "Keine Datenbank-URL gefunden (DATABASE_URL) – Migrationen übersprungen.\n"
            "Die App braucht auf Vercel eine PostgreSQL-Datenbank (z. B. Neon über "
            "Vercel → Storage); siehe docs/deployment.md, Abschnitt „Vercel“.",
            [],
        )
    umgebung = env.get("VERCEL_ENV", "")
    if umgebung not in ("", "production") and env.get("MIGRATE_ON_BUILD") != "1":
        return (
            f"{umgebung}-Build: Migrationen übersprungen (MIGRATE_ON_BUILD=1 erzwingt sie).",
            [],
        )
    schritte = [["migrate", "--noinput"]]
    if env.get("SEED_DEMO") == "1":
        schritte.append(["seed_demo"])
    return None, schritte


def main(env=None, run=subprocess.run):
    env = dict(os.environ if env is None else env)
    for warnung in warnungen(env):
        print(warnung, flush=True)
    hinweis, schritte = plan(env)
    if hinweis:
        print(hinweis, flush=True)
    if not schritte:
        return 0

    # Die Settings lesen DATABASE_URL: dorthin gehört die direkte Verbindung.
    env["DATABASE_URL"] = datenbank_url(env)
    for argumente in schritte:
        print(f"→ manage.py {' '.join(argumente)}", flush=True)
        try:
            run([sys.executable, "manage.py", *argumente], cwd=ROOT, env=env, check=True)
        except subprocess.CalledProcessError as fehler:
            print(
                f"Build abgebrochen: manage.py {argumente[0]} ist fehlgeschlagen "
                f"(Exit-Code {fehler.returncode}).",
                file=sys.stderr,
                flush=True,
            )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
