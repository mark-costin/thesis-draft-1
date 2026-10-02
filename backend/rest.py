import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask

from backend.dbconnect import init_db, db
from backend.routes.predictions import predictions_bp
from backend.routes.doctor import doctor_bp
from backend.routes.auth0 import auth_bp
from backend.middleware.security import apply_security_headers

# Load environment configuration
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

# Bind database and connection pooling to this specific Flask app
init_db(app)

# Apply global HTTP security and CORS headers
app.after_request(apply_security_headers)

# Register versioned API blueprints
app.register_blueprint(predictions_bp)
app.register_blueprint(doctor_bp)
app.register_blueprint(auth_bp)

with app.app_context():
    # Import ORM models to register tables with SQLAlchemy metadata
    import backend.model_orm.clinic_orm  # noqa: F401
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)