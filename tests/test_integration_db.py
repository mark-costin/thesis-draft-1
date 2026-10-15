"""End-to-end checks against a real SQLite database (run on a machine with the full stack).

Needs: flask_sqlalchemy, bcrypt, pgvector (all in your backend's requirements).
"""
import os
import unittest

from tests._helpers import has_modules

DB_STACK = has_modules("flask_sqlalchemy", "bcrypt", "pgvector")


@unittest.skipUnless(DB_STACK, "needs flask_sqlalchemy + bcrypt + pgvector (runs on your machine)")
class DatabaseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_URL"] = "sqlite://"  # in-memory, never touches clinic.db
        from flask import Flask, jsonify
        from backend.dbconnect import db, init_db
        import backend.model_orm  # noqa: F401  registers every table
        from backend.middleware.rbac import role_required
        from backend.middleware.idempotency import enforce_idempotency
        from backend.routes.auth0 import auth_bp

        app = Flask(__name__)
        init_db(app)
        app.register_blueprint(auth_bp)
        cls.calls = {"n": 0}

        @app.route("/protected")
        @role_required(["DOCTOR"])
        def protected():
            return jsonify({"ok": True}), 200

        @app.route("/write", methods=["POST"])
        @role_required(["DOCTOR"])
        @enforce_idempotency
        def write():
            cls.calls["n"] += 1
            return jsonify({"run": cls.calls["n"]}), 201

        cls.app, cls.db = app, db
        with app.app_context():
            db.create_all()

    def setUp(self):
        from backend.model_orm.usr_orm import User
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.db.session.query(User).delete()
        user = User(username="doc_test", role="DOCTOR")
        user.set_password("correct-horse-1")
        self.db.session.add(user)
        self.db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        self.db.session.rollback()
        self.ctx.pop()

    def login(self):
        r = self.client.post("/api/v1/auth/login", json={"username": "doc_test", "password": "correct-horse-1"})
        self.assertEqual(r.status_code, 200, r.get_json())
        return {"Authorization": f"Bearer {r.get_json()['access_token']}"}

    def test_logout_revokes_the_token(self):
        headers = self.login()
        self.assertEqual(self.client.get("/protected", headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/api/v1/auth/logout", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/protected", headers=headers).status_code, 401)

    def test_idempotency_replays_on_sqlite(self):
        headers = {**self.login(), "Idempotency-Key": "integration-1"}
        first = self.client.post("/write", headers=headers)
        second = self.client.post("/write", headers=headers)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.get_json(), first.get_json())
        self.assertEqual(self.calls["n"], 1)


if __name__ == "__main__":
    unittest.main()
