import uuid
from flask import Blueprint, jsonify
from sqlalchemy import text
from dbconnect import db
from middleware.idempotency import enforce_idempotency
from middleware.sanitizer import sanitize_response

health_bp = Blueprint("health", __name__, url_prefix="/api/health")

@health_bp.route("", methods=["GET"])
def health_check():
    """General API Gateway readiness check."""
    raw_payload = {
        "status": "healthy",
        "service": "Flask API Gateway",
        "password_hash": "HIDDEN_SECRET_THAT_SHOULD_BE_STRIPPED"
    }
    return jsonify(sanitize_response(raw_payload)), 200

@health_bp.route("/db", methods=["GET"])
def db_health_check():
    """Executes a live query to verify PostgreSQL ORM connection."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "engine": "PostgreSQL"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }), 500

@health_bp.route("/test-idempotency", methods=["POST"])
@enforce_idempotency
def test_idempotency():
    """Test endpoint to verify idempotency layer behavior."""
    return jsonify({
        "status": "success",
        "message": "State modification processed successfully.",
        "transaction_id": str(uuid.uuid4())
    }), 201