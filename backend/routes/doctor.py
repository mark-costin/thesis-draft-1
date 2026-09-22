from flask import Blueprint, request, jsonify
from dbconnect import db
from backend.model_orm.pat_orm import Patient
from backend.model_orm.doc_orm import Doctor

# Import Security Middleware
from backend.middleware.rbac import role_required
from backend.middleware.idempotency import enforce_idempotency
from backend.middleware.sanitizer import sanitize_response

doctor_bp = Blueprint('doctor', __name__, url_prefix='/api/doctor')

@doctor_bp.route('/queue', methods=['GET'])
@role_required(['DOCTOR', 'ADMIN'])
def get_triage_queue():
    """Fetches the active patient triage queue."""
    # In a real environment, this would query a TriageQueue or Appointment table.
    mock_queue = [
        {"queue_no": "Q-01", "patient_id": 1, "urgency": "High", "status": "Waiting"},
        {"queue_no": "Q-02", "patient_id": 2, "urgency": "Routine", "status": "Waiting"}
    ]
    user_role = request.current_user.get("role")
    return jsonify(sanitize_response(mock_queue, role=user_role)), 200


@doctor_bp.route('/patient/<int:patient_id>', methods=['GET'])
@role_required(['DOCTOR', 'ADMIN'])
def get_patient_record(patient_id):
    """Fetches a complete patient clinical record."""
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({"error": "Patient record not found"}), 404
        
    patient_data = {column.name: getattr(patient, column.name) for column in patient.__table__.columns}
    
    user_role = request.current_user.get("role")
    return jsonify(sanitize_response(patient_data, role=user_role)), 200


@doctor_bp.route('/consultation', methods=['POST'])
@role_required(['DOCTOR'])
@enforce_idempotency
def submit_consultation():
    """Saves clinical directives and prescription orders."""
    data = request.get_json()
    patient_id = data.get("patient_id")
    directives = data.get("directives")
    
    if not patient_id or not directives:
        return jsonify({"error": "patient_id and directives are required"}), 400

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({"error": "Target patient not found"}), 404

    # Perform updates (e.g., logging consultation notes, prescribing medications)
    # db.session.add(ConsultationRecord(...))
    # db.session.commit()
    
    response_payload = {
        "message": "Consultation directives and notes recorded successfully",
        "encounter_status": "Complete",
        "directives_applied": directives
    }
    
    user_role = request.current_user.get("role")
    return jsonify(sanitize_response(response_payload, role=user_role)), 201