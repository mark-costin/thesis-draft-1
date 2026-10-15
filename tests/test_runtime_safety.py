"""
Batch 5a: how the server starts and where it stores data.

  1. rest.py ran the server with debug=True on 0.0.0.0: Flask's debugger lets anyone on the
     same network run Python on this computer. Debug is now off unless asked for, and is
     refused on any address other than this computer.
  2. dbconnect.py fell back to sqlite:///clinic.db when DATABASE_URL was missing, so a .env
     that failed to load looked like "all patients are gone". It now refuses to start.
  3. datetime.utcnow() and Query.get() are deprecated (the two warnings in every test run).
"""
import os
import subprocess
import sys
import unittest
import warnings
from datetime import datetime, timedelta, timezone

from tests._helpers import ROOT, has_modules


class RunOptionsTests(unittest.TestCase):
    def options(self, **env):
        from backend.config import run_options
        return run_options(env)

    def test_default_is_this_computer_only_without_debug(self):
        self.assertEqual(self.options(), {"host": "127.0.0.1", "port": 5000, "debug": False})

    def test_debug_can_be_turned_on_for_this_computer(self):
        self.assertTrue(self.options(FLASK_DEBUG="1")["debug"])

    def test_other_computers_can_connect_when_debug_is_off(self):
        # e.g. a defense demo on the same Wi-Fi
        self.assertEqual(self.options(FLASK_HOST="0.0.0.0")["host"], "0.0.0.0")

    def test_debug_on_the_network_is_refused(self):
        with self.assertRaises(RuntimeError):
            self.options(FLASK_DEBUG="1", FLASK_HOST="0.0.0.0")

    def test_port_comes_from_the_environment(self):
        self.assertEqual(self.options(FLASK_PORT="8000")["port"], 8000)
        with self.assertRaises(RuntimeError):
            self.options(FLASK_PORT="web")

    def test_rest_py_no_longer_hardcodes_debug(self):
        source = (ROOT / "backend" / "rest.py").read_text(encoding="utf-8")
        self.assertNotIn("debug=True", source)
        self.assertIn("run_options(", source)


class DatabaseUrlTests(unittest.TestCase):
    def url(self, **env):
        from backend.config import database_url
        return database_url(env)

    def test_missing_url_refuses_to_start(self):
        with self.assertRaises(RuntimeError) as ctx:
            self.url()
        self.assertIn("DATABASE_URL", str(ctx.exception))

    def test_empty_url_refuses_to_start(self):
        with self.assertRaises(RuntimeError):
            self.url(DATABASE_URL="  ")

    def test_old_postgres_scheme_is_normalised(self):
        self.assertEqual(self.url(DATABASE_URL="postgres://u@localhost/db"), "postgresql://u@localhost/db")

    def test_in_memory_sqlite_is_still_allowed_for_tests(self):
        self.assertEqual(self.url(DATABASE_URL="sqlite://"), "sqlite://")

    def test_no_silent_clinic_db_fallback_left(self):
        source = (ROOT / "backend" / "dbconnect.py").read_text(encoding="utf-8")
        self.assertNotIn("clinic.db", source)

    @unittest.skipUnless(has_modules("flask_sqlalchemy"), "flask_sqlalchemy not installed")
    def test_server_refuses_to_start_without_database_url(self):
        env = {**os.environ, "DATABASE_URL": ""}   # empty, so .env cannot refill it
        r = subprocess.run([sys.executable, "-c", "import backend.rest"], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=120)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DATABASE_URL is not set", r.stderr)


class DeprecationTests(unittest.TestCase):
    def test_utc_now_is_naive_utc_without_a_warning(self):
        from backend.timeutil import utc_now_naive
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            now = utc_now_naive()
        self.assertIsNone(now.tzinfo)        # the columns are timestamp WITHOUT time zone
        utc = datetime.now(timezone.utc).replace(tzinfo=None)
        self.assertLess(abs(now - utc), timedelta(seconds=5))

    def backend_sources(self):
        for path in (ROOT / "backend").rglob("*.py"):
            yield path.relative_to(ROOT), path.read_text(encoding="utf-8")

    def test_no_utcnow_left_in_the_backend(self):
        self.assertEqual([str(p) for p, s in self.backend_sources() if "utcnow(" in s or "utcnow," in s
                          or "utcnow)" in s], [])

    def test_no_legacy_query_get_left_in_the_backend(self):
        self.assertEqual([str(p) for p, s in self.backend_sources() if ".query.get(" in s], [])


if __name__ == "__main__":
    unittest.main()