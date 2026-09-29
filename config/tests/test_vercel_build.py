"""Build-Schritt für Vercel (``tools/vercel_build.py``): Migrationen beim Deploy."""

import contextlib
import io
import json
import subprocess
from pathlib import Path

from django.test import SimpleTestCase

from tools import vercel_build

PRODUKTION = {"VERCEL_ENV": "production", "DATABASE_URL": "postgresql://u:p@pooler/db"}


class BuildPlanTests(SimpleTestCase):
    def test_ohne_datenbank_wird_nichts_migriert(self):
        hinweis, schritte = vercel_build.plan({"VERCEL_ENV": "production"})
        self.assertEqual(schritte, [])
        self.assertIn("DATABASE_URL", hinweis)
        self.assertIn("docs/deployment.md", hinweis)

    def test_production_migriert(self):
        self.assertEqual(vercel_build.plan(PRODUKTION), (None, [["migrate", "--noinput"]]))

    def test_postgres_url_der_integration_genuegt(self):
        env = {"VERCEL_ENV": "production", "POSTGRES_URL": "postgres://u:p@h/db"}
        self.assertEqual(vercel_build.plan(env)[1], [["migrate", "--noinput"]])

    def test_preview_ueberspringt_die_migration(self):
        hinweis, schritte = vercel_build.plan({**PRODUKTION, "VERCEL_ENV": "preview"})
        self.assertEqual(schritte, [])
        self.assertIn("MIGRATE_ON_BUILD", hinweis)

    def test_preview_kann_die_migration_erzwingen(self):
        env = {**PRODUKTION, "VERCEL_ENV": "preview", "MIGRATE_ON_BUILD": "1"}
        self.assertEqual(vercel_build.plan(env)[1], [["migrate", "--noinput"]])

    def test_lokaler_aufruf_ohne_vercel_env_migriert(self):
        self.assertEqual(
            vercel_build.plan({"DATABASE_URL": "postgresql://u:p@h/db"})[1],
            [["migrate", "--noinput"]],
        )

    def test_demo_daten_nur_auf_anforderung(self):
        self.assertEqual(vercel_build.plan({**PRODUKTION, "SEED_DEMO": "1"})[1][-1], ["seed_demo"])
        for wert in ("0", "", "true"):
            with self.subTest(SEED_DEMO=wert):
                schritte = vercel_build.plan({**PRODUKTION, "SEED_DEMO": wert})[1]
                self.assertNotIn(["seed_demo"], schritte)

    def test_direkte_verbindung_hat_vorrang_vor_dem_pooler(self):
        env = {
            "DATABASE_URL": "postgresql://pooler",
            "POSTGRES_URL": "postgresql://pooler2",
            "POSTGRES_URL_NON_POOLING": "postgresql://direkt2",
            "DATABASE_URL_UNPOOLED": "postgresql://direkt",
        }
        self.assertEqual(vercel_build.datenbank_url(env), "postgresql://direkt")
        del env["DATABASE_URL_UNPOOLED"]
        self.assertEqual(vercel_build.datenbank_url(env), "postgresql://direkt2")
        del env["POSTGRES_URL_NON_POOLING"]
        self.assertEqual(vercel_build.datenbank_url(env), "postgresql://pooler")
        self.assertIsNone(vercel_build.datenbank_url({}))


class BuildWarnungTests(SimpleTestCase):
    def test_fehlender_oder_oeffentlicher_schluessel_wird_gemeldet(self):
        for env in ({}, {"DJANGO_SECRET_KEY": ""}, {"DJANGO_SECRET_KEY": "dev-insecure-key"}):
            with self.subTest(env=env):
                (meldung,) = vercel_build.warnungen(env)
                self.assertIn("DJANGO_SECRET_KEY", meldung)

    def test_gesetzter_schluessel_ist_unauffaellig(self):
        self.assertEqual(vercel_build.warnungen({"DJANGO_SECRET_KEY": "x" * 50}), [])


class BuildMainTests(SimpleTestCase):
    def _main(self, env, fehler=None):
        aufrufe = []

        def falscher_lauf(befehl, **optionen):
            aufrufe.append((befehl, optionen))
            if fehler:
                raise subprocess.CalledProcessError(fehler, befehl)
            return subprocess.CompletedProcess(befehl, 0)

        ausgabe, fehlerausgabe = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(ausgabe), contextlib.redirect_stderr(fehlerausgabe):
            code = vercel_build.main(env, run=falscher_lauf)
        return code, aufrufe, ausgabe.getvalue(), fehlerausgabe.getvalue()

    def test_fuehrt_die_schritte_gegen_die_direkte_verbindung_aus(self):
        env = {
            **PRODUKTION,
            "DATABASE_URL_UNPOOLED": "postgresql://u:p@direkt/db",
            "SEED_DEMO": "1",
        }
        code, aufrufe, _, _ = self._main(env)
        self.assertEqual(code, 0)
        self.assertEqual(
            [befehl[2:] for befehl, _ in aufrufe], [["migrate", "--noinput"], ["seed_demo"]]
        )
        for befehl, optionen in aufrufe:
            self.assertEqual(Path(befehl[1]).name, "manage.py")
            self.assertEqual(optionen["cwd"], vercel_build.ROOT)
            self.assertTrue(optionen["check"])
            self.assertEqual(optionen["env"]["DATABASE_URL"], "postgresql://u:p@direkt/db")

    def test_ohne_datenbank_laeuft_kein_unterprozess(self):
        code, aufrufe, ausgabe, _ = self._main({"VERCEL_ENV": "production"})
        self.assertEqual(code, 0)  # der Build soll trotzdem durchlaufen
        self.assertEqual(aufrufe, [])
        self.assertIn("Keine Datenbank-URL", ausgabe)

    def test_schluessel_warnung_erscheint_im_build_log_ohne_abbruch(self):
        code, aufrufe, ausgabe, _ = self._main(PRODUKTION)  # ohne DJANGO_SECRET_KEY
        self.assertEqual(code, 0)
        self.assertEqual(len(aufrufe), 1)  # die Migration läuft trotzdem
        self.assertIn("WARNUNG: DJANGO_SECRET_KEY", ausgabe)

    def test_fehlgeschlagene_migration_bricht_den_build_ab(self):
        code, aufrufe, _, fehlerausgabe = self._main({**PRODUKTION, "SEED_DEMO": "1"}, fehler=3)
        self.assertEqual(code, 1)
        self.assertEqual(len(aufrufe), 1)  # seed_demo läuft nach einem Fehler nicht mehr
        self.assertIn("migrate", fehlerausgabe)
        self.assertIn("3", fehlerausgabe)


class VercelKonfigurationTests(SimpleTestCase):
    """``vercel.json`` verweist auf das Skript und bleibt gültig."""

    def test_build_command_zeigt_auf_ein_vorhandenes_skript(self):
        wurzel = vercel_build.ROOT
        konfig = json.loads((wurzel / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(konfig["buildCommand"], "python tools/vercel_build.py")
        self.assertTrue((wurzel / "tools" / "vercel_build.py").is_file())

    def test_funktion_liegt_in_der_eu(self):
        """PRD N1.1: Daten nur in der EU/DE – Frankfurt."""
        konfig = json.loads((vercel_build.ROOT / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(konfig["regions"], ["fra1"])
