import json
import time
from functools import wraps
from flask import request, jsonify, make_response
from backend.utils.dbconnect import get_db_connection

CACHE_TTL_SECONDS = 86400  # 24-hour expiration window

def enforce_idempotency(f):
    """
    Decorator to safeguard state-changing routes against replay attacks and duplicate submissions
    by persisting state tokens and responses in PostgreSQL.
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

            conn = get_db_connection()
            try:
                now = time.time()
                with conn.cursor() as cursor:
                    # Check for existing valid idempotency record
                    cursor.execute(
                        "SELECT data, status, timestamp FROM idempotency_cache WHERE key = %s",
                        (key,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        cached_data, status_code, timestamp = row
                        # Enforce TTL window
                        if now - timestamp <= CACHE_TTL_SECONDS:
                            response = make_response(jsonify(cached_data), status_code)
                            response.headers["X-Cache-Lookup"] = "HIT - Idempotent Replay Short-Circuited (PostgreSQL)"
                            return response
                        else:
                            # Purge expired idempotency record
                            cursor.execute("DELETE FROM idempotency_cache WHERE key = %s", (key,))
                            conn.commit()

                # Execute original endpoint controller logic
                result = f(*args, **kwargs)

                # Unpack response object and status code
                if isinstance(result, tuple):
                    response_obj, status_code = result[0], result[1]
                else:
                    response_obj, status_code = result, 200

                # Persist successful state-modifying responses
                if status_code in [200, 201, 202, 204]:
                    data = response_obj.get_json() if hasattr(response_obj, "get_json") else response_obj
                    
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT INTO idempotency_cache (key, data, status, timestamp)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (key) DO UPDATE 
                            SET data = EXCLUDED.data, status = EXCLUDED.status, timestamp = EXCLUDED.timestamp
                            """,
                            (key, json.dumps(data), status_code, now)
                        )
                        conn.commit()

                return result

            finally:
                if conn:
                    conn.close()

        return f(*args, **kwargs)
    return decorated_function