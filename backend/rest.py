import os
from flask import jsonify
from flask_cors import CORS
from dbconnect import app, db

# Import Security Middleware
from backend.middleware.security import init_security_headers

# Import Blueprints
from backend.routes.auth0 import auth_bp
from backend.routes.doctor import doctor_bp
from backend.routes.admin import admin_bp
from backend.routes.predictions import predictions_bp
from backend.routes.health import health_bp

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

# Bind the Database to the App
db.init_app(app)

# 3. Register API Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(doctor_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(predictions_bp)
app.register_blueprint(health_bp)

# 4. Centralized HTTP Error Handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad Request", "message": str(error.description)}), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({"error": "Unauthorized", "message": "Authentication required or token invalid."}), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({"error": "Forbidden", "message": "Insufficient permissions to access this resource."}), 403

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not Found", "message": "The requested endpoint does not exist."}), 404

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error": "Internal Server Error", "message": "An unexpected system error occurred."}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)