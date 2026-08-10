import os
from flask_cors import CORS
from dbconnect import app
from middleware.security import init_security_headers
from routes.health import health_bp

# 1. Enforce CORS Policy Restrictions
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:3000",
            "http://localhost:8501",
            "http://127.0.0.1:8501"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-CSRF-Token", "Idempotency-Key", "X-Idempotency-Key"]
    }
})

# 2. Attach Web Defense Headers
init_security_headers(app)

# 3. Register API Blueprints
app.register_blueprint(health_bp)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)