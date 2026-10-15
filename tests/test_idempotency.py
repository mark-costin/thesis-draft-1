"""enforce_idempotency: replay, scoping, in-flight protection, cleanup on failure."""
import time
import unittest
from functools import wraps
from types import SimpleNamespace
from unittest.mock import patch

from tests._helpers import ROOT  # noqa: F401

from flask import Flask, jsonify, request


class MemoryStore:
    """In-memory idempotency store with the same interface as the SQLAlchemy store."""

    def __init__(self):
        self.rows = {}

    def reserve(self, key, now):
        if key in self.rows:
            return self.rows[key]
        self.rows[key] = SimpleNamespace(data={}, status=0, timestamp=now)
        return None

    def complete(self, key, data, status, now):
        self.rows[key] = SimpleNamespace(data=data, status=status, timestamp=now)

    def release(self, key):
        self.rows.pop(key, None)


def as_user(user_id):
    """Stands in for role_required: sets request.current_user."""
    def deco(f):
        @wraps(f)
        def inner(*a, **kw):
            request.current_user = {"user_id": user_id}
            return f(*a, **kw)
        return inner
    return deco


class IdempotencyTests(unittest.TestCase):
    def setUp(self):
        import backend.middleware.idempotency as idem
        self.idem = idem
        self.store = MemoryStore()
        self.patcher = patch.object(idem, "get_store", create=True, return_value=self.store)
        self.patcher.start()
        self.calls = {"n": 0}
        self.next_status = 201
        self.raise_error = False
        self.app = self._app()
        self.client = self.app.test_client()

    def tearDown(self):
        self.patcher.stop()

    def _app(self):
        from backend.middleware.idempotency import enforce_idempotency
        app = Flask(__name__)
        test = self

        def handler():
            test.calls["n"] += 1
            if test.raise_error:
                raise RuntimeError("boom")
            return jsonify({"run": test.calls["n"]}), test.next_status

        for path in ("/a", "/b"):
            view = as_user(1)(enforce_idempotency(handler))
            app.add_url_rule(path, endpoint=path, view_func=view, methods=["GET", "POST"])

        @app.route("/u2/a", methods=["POST"])
        @as_user(2)
        @enforce_idempotency
        def user2_a():
            return handler()

        return app

    def post(self, path="/a", key="k-1"):
        headers = {"Idempotency-Key": key} if key else {}
        return self.client.post(path, headers=headers)

    def test_post_without_key_is_rejected(self):
        r = self.post(key=None)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.calls["n"], 0)

    def test_get_does_not_need_a_key(self):
        r = self.client.get("/a")
        self.assertEqual(r.status_code, 201)

    def test_same_key_replays_original_response_without_rerunning(self):
        first = self.post()
        second = self.post()
        self.assertEqual(self.calls["n"], 1)
        self.assertEqual(second.status_code, first.status_code)
        self.assertEqual(second.get_json(), first.get_json())
        self.assertEqual(second.headers.get("X-Idempotent-Replay"), "true")

    def test_same_key_from_another_user_is_not_a_replay(self):
        self.post("/a", "shared")
        r = self.post("/u2/a", "shared")
        self.assertEqual(self.calls["n"], 2)
        self.assertEqual(r.get_json(), {"run": 2})

    def test_same_key_on_another_endpoint_is_not_a_replay(self):
        self.post("/a", "shared")
        self.post("/b", "shared")
        self.assertEqual(self.calls["n"], 2)

    def test_failed_request_releases_key_so_retry_runs(self):
        self.next_status = 400
        self.post()
        self.next_status = 201
        r = self.post()
        self.assertEqual(self.calls["n"], 2)
        self.assertEqual(r.status_code, 201)

    def test_exception_releases_key(self):
        self.raise_error = True
        self.app.config["TESTING"] = False  # let Flask turn the exception into a 500
        self.app.logger.disabled = True     # the traceback is expected; keep test output clean
        self.assertEqual(self.post().status_code, 500)
        self.assertEqual(self.store.rows, {})

    def test_request_already_in_flight_gets_409(self):
        key = self.idem.scoped_key("k-1", user_id=1, method="POST", path="/a")
        self.store.rows[key] = SimpleNamespace(data={}, status=0, timestamp=time.time())
        r = self.post()
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["code"], "IDEMPOTENCY_IN_PROGRESS")
        self.assertEqual(self.calls["n"], 0)

    def test_stale_in_flight_marker_is_taken_over(self):
        key = self.idem.scoped_key("k-1", user_id=1, method="POST", path="/a")
        old = time.time() - self.idem.PENDING_TIMEOUT_SECONDS - 1
        self.store.rows[key] = SimpleNamespace(data={}, status=0, timestamp=old)
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.calls["n"], 1)

    def test_expired_response_is_not_replayed(self):
        key = self.idem.scoped_key("k-1", user_id=1, method="POST", path="/a")
        old = time.time() - self.idem.CACHE_TTL_SECONDS - 1
        self.store.rows[key] = SimpleNamespace(data={"run": 99}, status=201, timestamp=old)
        r = self.post()
        self.assertEqual(r.get_json(), {"run": 1})

    def test_scoped_key_fits_the_255_char_column(self):
        key = self.idem.scoped_key("x" * 500, user_id=1, method="POST", path="/a")
        self.assertLessEqual(len(key), 255)


if __name__ == "__main__":
    unittest.main()
