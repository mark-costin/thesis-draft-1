from backend.config import CORS_ALLOWED_ORIGIN


def apply_security_headers(response):
    """
    Applies browser defense headers to mitigate XSS, Clickjacking, and MIME-sniffing attacks.
    Synchronized with RBAC and Idempotency middleware to permit custom HTTP headers.
    """
    # 1. Strict Security Headers (Baseline Defense)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    # The legacy XSS auditor is removed from modern browsers and could itself be abused;
    # "0" explicitly turns it off, as OWASP recommends. CSP below is the real protection.
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    # 2. CORS Headers — origin set by CORS_ALLOWED_ORIGIN in .env (default "*")
    response.headers["Access-Control-Allow-Origin"] = CORS_ALLOWED_ORIGIN
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"

    # 3. Middleware Integration: Explicitly whitelist headers required by rbac.py and idempotency.py
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Idempotency-Key, X-Idempotency-Key"

    return response
