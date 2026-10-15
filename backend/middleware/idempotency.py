"""
Idempotency for state-changing routes (POST/PUT/PATCH/DELETE).

A client sends `Idempotency-Key: <uuid>`. The first request with that key runs the route
and its successful response is stored; any retry with the same key gets the stored
response back instead of running the route again.

How it avoids the old problems:
  * Scoped: the stored key combines user, method, path and the client's key, so one
    user's key can never replay another user's response or another endpoint's response.
  * Reserve first: a "pending" row is inserted BEFORE the route runs. A second request
    arriving while the first is still running finds that row and gets 409, instead of
    running the route a second time.
  * Released on failure: if the route errors or returns non-2xx, the reservation is
    removed so the client can retry.
  * Database-agnostic: uses the SQLAlchemy model, so it works on SQLite and PostgreSQL.

Order on a route: put @role_required ABOVE @enforce_idempotency so the user is known.
"""
import hashlib
import time
from functools import wraps

from flask import jsonify, make_response, request

CACHE_TTL_SECONDS = 86400      # completed responses are replayed for 24 hours
PENDING_TIMEOUT_SECONDS = 120  # a reservation older than this is assumed abandoned (crash)
PENDING_STATUS = 0             # status value marking "request still running"
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def scoped_key(raw_key, user_id, method, path):
    """Fixed-length key unique to (user, method, path, client key). Fits String(255)."""
    scope = f"{user_id}|{method.upper()}|{path}|{raw_key}"
    return "idem:" + hashlib.sha256(scope.encode("utf-8")).hexdigest()


class SQLAlchemyIdempotencyStore:
    """Stores reservations and responses in the idempotency_cache table."""

    def reserve(self, key, now):
        """Insert a pending row. Returns None if reserved, else the existing row."""
        from sqlalchemy.exc import IntegrityError
        from backend.dbconnect import db
        from backend.model_orm.clinic_orm import IdempotencyCache

        try:
            db.session.add(IdempotencyCache(key=key, data={}, status=PENDING_STATUS, timestamp=now))
            db.session.commit()
            return None
        except IntegrityError:
            db.session.rollback()
            existing = db.session.get(IdempotencyCache, key)
            if existing is None:  # deleted between our insert and read: try once more
                return self.reserve(key, now)
            return existing

    def complete(self, key, data, status, now):
        from backend.dbconnect import db
        from backend.model_orm.clinic_orm import IdempotencyCache

        row = db.session.get(IdempotencyCache, key)
        if row is None:
            row = IdempotencyCache(key=key)
            db.session.add(row)
        row.data, row.status, row.timestamp = data, status, now
        db.session.commit()

    def release(self, key):
        from backend.dbconnect import db
        from backend.model_orm.clinic_orm import IdempotencyCache

        db.session.rollback()  # the route may have left the session in a failed state
        row = db.session.get(IdempotencyCache, key)
        if row is not None:
            db.session.delete(row)
            db.session.commit()


_default_store = SQLAlchemyIdempotencyStore()


def get_store():
    return _default_store


def _error(status_code, code, message, retryable):
    return jsonify({"status": "error", "code": code, "error": message, "retryable": retryable}), status_code


def _replay(row):
    if row.status == 204:
        response = make_response("", 204)
    else:
        response = make_response(jsonify(row.data), row.status)
    response.headers["X-Idempotent-Replay"] = "true"
    return response


def enforce_idempotency(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method not in STATE_CHANGING_METHODS:
            return f(*args, **kwargs)

        raw_key = request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")
        if not raw_key:
            return _error(400, "IDEMPOTENCY_KEY_MISSING",
                          "State-changing operations require a unique Idempotency-Key header (UUID).", False)

        user = getattr(request, "current_user", None) or {}
        key = scoped_key(raw_key, user.get("user_id", "anonymous"), request.method, request.path)
        store = get_store()
        now = time.time()

        existing = store.reserve(key, now)
        if existing is not None:
            age = now - existing.timestamp
            if existing.status == PENDING_STATUS and age <= PENDING_TIMEOUT_SECONDS:
                return _error(409, "IDEMPOTENCY_IN_PROGRESS",
                              "A request with this Idempotency-Key is still being processed.", True)
            if existing.status != PENDING_STATUS and age <= CACHE_TTL_SECONDS:
                return _replay(existing)
            # Expired response or abandoned reservation: start over.
            store.release(key)
            existing = store.reserve(key, now)
            if existing is not None:  # another request took it in the meantime
                return _error(409, "IDEMPOTENCY_IN_PROGRESS",
                              "A request with this Idempotency-Key is still being processed.", True)

        try:
            response = make_response(f(*args, **kwargs))
        except Exception:
            store.release(key)
            raise

        if 200 <= response.status_code < 300:
            store.complete(key, response.get_json(silent=True) or {}, response.status_code, time.time())
        else:
            store.release(key)
        return response

    return decorated_function
