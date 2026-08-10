import time
from functools import wraps
from flask import request, jsonify, make_response

# In-memory storage for idempotency keys
# Structure: { key: {"data": response_payload, "status": status_code, "timestamp": unix_time} }
IDEMPOTENCY_CACHE = {}
CACHE_TTL_SECONDS = 86400  # 24-hour expiration window

def enforce_idempotency(f):
    """
    Decorator to safeguard state-changing routes against replay attacks and duplicate submissions.
    Requires an 'Idempotency-Key' or 'X-Idempotency-Key' header on POST, PUT, PATCH, DELETE requests.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            key = request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")
            
            if not key:
                return jsonify({
                    "error": "Idempotency-Key header is missing.",
                    "message": "State-changing operations require a unique Idempotency-Key header (UUID)."
                }), 400

            # Evict expired keys
            now = time.time()
            expired_keys = [k for k, v in IDEMPOTENCY_CACHE.items() if now - v["timestamp"] > CACHE_TTL_SECONDS]
            for k in expired_keys:
                del IDEMPOTENCY_CACHE[k]

            # Short-circuit duplicate execution
            if key in IDEMPOTENCY_CACHE:
                cached = IDEMPOTENCY_CACHE[key]
                response = make_response(jsonify(cached["data"]), cached["status"])
                response.headers["X-Cache-Lookup"] = "HIT - Idempotent Replay Short-Circuited"
                return response

            # Execute the original controller/route logic
            result = f(*args, **kwargs)

            # Unpack response object and status code
            if isinstance(result, tuple):
                response_obj, status_code = result[0], result[1]
            else:
                response_obj, status_code = result, 200

            # Cache successful state modifications
            if status_code in [200, 201, 202, 204]:
                data = response_obj.get_json() if hasattr(response_obj, "get_json") else response_obj
                IDEMPOTENCY_CACHE[key] = {
                    "data": data,
                    "status": status_code,
                    "timestamp": now
                }

            return result

        return f(*args, **kwargs)
    return decorated_function