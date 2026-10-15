from functools import wraps

import jwt
from flask import jsonify, request

from backend.config import JWT_ALGORITHM, JWT_SECRET


def _error(status_code, code, message):
    return jsonify({"status": "error", "code": code, "error": message, "retryable": False}), status_code


def load_user(user_id):
    """Fetch the account row for a token. Imported lazily so this module has no import-time DB dependency."""
    from backend.dbconnect import db
    from backend.model_orm.usr_orm import User
    return db.session.get(User, user_id)


def role_required(allowed_roles):
    """
    Flask decorator to enforce role-based access control (RBAC) via JWT Bearer tokens.

    On every request it re-checks the account in the database, so that:
      - logout / password change (token_version bump) revoke old tokens immediately,
      - locked or deleted accounts lose access immediately,
      - a role change in the database applies immediately (the token's role is not trusted).

    Args:
        allowed_roles (list or str): Roles permitted to access the endpoint.

    Returns:
        HTTP 401 (not authenticated / session invalid) or 403 (role not allowed) on failure.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]
    allowed = set(allowed_roles)

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return _error(401, "UNAUTHORIZED", "Missing or invalid authorization token.")

            token = auth_header[len("Bearer "):].strip()
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            except jwt.InvalidTokenError:  # includes ExpiredSignatureError
                return _error(401, "UNAUTHORIZED", "Missing or invalid authorization token.")

            user_id = payload.get("user_id")
            user = load_user(user_id) if user_id is not None else None
            if user is None or user.is_locked or payload.get("token_version") != user.token_version:
                return _error(401, "UNAUTHORIZED", "Session is no longer valid. Please log in again.")

            if user.role not in allowed:
                return _error(403, "FORBIDDEN", "Your role is not allowed to access this resource.")

            payload["role"] = user.role  # database is the source of truth
            request.current_user = payload
            return f(*args, **kwargs)

        return decorated_function

    return decorator
