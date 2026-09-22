from flask import Flask

def init_security_headers(app: Flask) -> None:
    """
    Applies browser defense headers to mitigate XSS, Clickjacking, and MIME-sniffing attacks.
    Synchronized with RBAC and Idempotency middleware to permit custom HTTP headers.
    """
    @app.after_request
    def apply_security_headers(response):
        # 1. Strict Security Headers (Baseline Defense)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        # 2. CORS Headers (Streamlit Frontend -> Flask API Communication)
        response.headers["Access-Control-Allow-Origin"] = "*"  # Update to specific frontend domain/port in production
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        
        # 3. Middleware Integration: Explicitly whitelist headers required by rbac.py and idempotency.py
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Idempotency-Key, X-Idempotency-Key"

        return response