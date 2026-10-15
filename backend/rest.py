import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask

from backend.dbconnect import init_db, db
from backend.routes.predictions import predictions_bp
from backend.routes.doctor import doctor_bp
from backend.routes.auth0 import auth_bp
from backend.routes.patient import patient_bp
from backend.routes.admin import admin_bp
from backend.routes.health import health_bp
from backend.routes.biomarkers import biomarkers_bp
from backend.middleware.security import apply_security_headers

# Load environment configuration
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# 1. Create the app FIRST
app = Flask(__name__)

# 2. Bind database and connection pooling to this app
init_db(app)

# 3. Apply global HTTP security and CORS headers
app.after_request(apply_security_headers)

# 4. Register API blueprints (only after app exists)
app.register_blueprint(predictions_bp)
app.register_blueprint(doctor_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(patient_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(health_bp)
app.register_blueprint(biomarkers_bp)

# 5. Create tables (importing the package registers every model, audit_ledger included)
with app.app_context():
    import backend.model_orm  # noqa: F401
    db.create_all()

if __name__ == "__main__":
    # Host, port and debug come from .env (FLASK_HOST, FLASK_PORT, FLASK_DEBUG).
    # Default: this computer only, debug off. See backend/config.py run_options().
    from backend.config import run_options
    app.run(**run_options())
