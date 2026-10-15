"""role_required: no backdoor, sessions revocable, DB is the source of truth."""
import unittest
from unittest.mock import patch

from tests._helpers import auth_header, fake_user, make_token

from flask import Flask, jsonify, request


def _app():
    from backend.middleware.rbac import role_required
    app = Flask(__name__)

    @app.route("/admin-only")
    @role_required(["ADMIN"])
    def admin_only():
        return jsonify({"role": request.current_user["role"]}), 200

    return app


class RbacTests(unittest.TestCase):
    def call(self, headers, user):
        # The DB lookup is replaced because SQLAlchemy is not available in every test
        # environment; tests/test_integration_db.py covers the real lookup.
        with patch("backend.middleware.rbac.load_user", create=True, return_value=user):
            return _app().test_client().get("/admin-only", headers=headers)

    def test_dev_test_token_backdoor_is_rejected(self):
        r = self.call({"Authorization": "Bearer dev-test-token"}, fake_user(role="ADMIN"))
        self.assertEqual(r.status_code, 401)

    def test_valid_token_with_matching_version_is_allowed(self):
        r = self.call(auth_header(role="ADMIN", token_version=3), fake_user(role="ADMIN", token_version=3))
        self.assertEqual(r.status_code, 200)

    def test_token_issued_before_logout_is_rejected(self):
        # Logout bumps users.token_version from 3 to 4; the old token still says 3.
        r = self.call(auth_header(role="ADMIN", token_version=3), fake_user(role="ADMIN", token_version=4))
        self.assertEqual(r.status_code, 401)

    def test_locked_account_is_rejected(self):
        r = self.call(auth_header(role="ADMIN"), fake_user(role="ADMIN", is_locked=True))
        self.assertEqual(r.status_code, 401)

    def test_deleted_user_is_rejected(self):
        r = self.call(auth_header(role="ADMIN"), None)
        self.assertEqual(r.status_code, 401)

    def test_role_comes_from_database_not_token(self):
        # Token claims ADMIN, but the account was demoted to PATIENT.
        r = self.call(auth_header(role="ADMIN"), fake_user(role="PATIENT"))
        self.assertEqual(r.status_code, 403)

    def test_forbidden_response_uses_standard_error_shape(self):
        r = self.call(auth_header(role="ADMIN"), fake_user(role="PATIENT"))
        body = r.get_json()
        self.assertEqual(body["status"], "error")
        self.assertEqual(body["code"], "FORBIDDEN")
        self.assertIn("retryable", body)

    def test_token_signed_with_old_default_secret_is_rejected(self):
        token = make_token(role="ADMIN", secret="clinical-platform-default-jwt-secret-key")
        r = self.call({"Authorization": f"Bearer {token}"}, fake_user(role="ADMIN"))
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
