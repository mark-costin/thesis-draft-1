"""JWT secret must come from .env only; security headers must be current."""
import os
import subprocess
import sys
import unittest

from tests._helpers import ROOT  # noqa: F401  (sets env + sys.path)

from flask import Flask, make_response


def _import_without_secret(module):
    """Import `module` in a fresh interpreter whose environment has no JWT_SECRET."""
    env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET"}
    return subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=str(ROOT), env=env, capture_output=True, text=True,
    )


class JwtSecretTests(unittest.TestCase):
    def test_rbac_refuses_to_start_without_jwt_secret(self):
        # Before the fix, rbac silently fell back to a public hardcoded secret.
        result = _import_without_secret("backend.middleware.rbac")
        self.assertNotEqual(result.returncode, 0, "rbac imported with no JWT_SECRET set")
        self.assertIn("JWT_SECRET", result.stderr)

    def test_config_exposes_one_shared_secret(self):
        from backend import config
        self.assertEqual(config.JWT_SECRET, os.environ["JWT_SECRET"])
        self.assertEqual(config.JWT_ALGORITHM, "HS256")


class SecurityHeaderTests(unittest.TestCase):
    def _headers(self):
        from backend.middleware.security import apply_security_headers
        app = Flask(__name__)
        with app.test_request_context():
            return apply_security_headers(make_response("ok")).headers

    def test_xss_auditor_is_disabled_as_browsers_recommend(self):
        self.assertEqual(self._headers()["X-XSS-Protection"], "0")

    def test_cors_origin_comes_from_environment(self):
        self.assertEqual(self._headers()["Access-Control-Allow-Origin"], "http://localhost:8501")

    def test_baseline_headers_still_present(self):
        h = self._headers()
        self.assertEqual(h["X-Content-Type-Options"], "nosniff")
        self.assertEqual(h["X-Frame-Options"], "DENY")
        self.assertIn("Idempotency-Key", h["Access-Control-Allow-Headers"])


if __name__ == "__main__":
    unittest.main()
