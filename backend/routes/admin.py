from flask import Blueprint, request, jsonify
from dbconnect import db
from backend.model_orm.usr_orm import User
from backend.model_orm.doc_orm import Doctor

# Import Security Middleware
from backend.middleware.rbac import role_required
from backend.middleware.idempotency import enforce_idempotency
from backend.middleware.sanitizer import sanitize_response

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/directory', methods=['GET'])
@role_required(['ADMIN', 'SYSTEM_ADMIN'])
def list_system_directory():
    """Lists system-wide clinical accounts."""
    users = User.query.all()
    user_list = [user.to_dict() for user in users]
    
    return jsonify(sanitize_response(user_list, role="ADMIN")), 200


@admin_bp.route('/provision', methods=['POST'])
@role_required(['ADMIN', 'SYSTEM_ADMIN'])
@enforce_idempotency
def provision_clinician_account():
    """Provisions a new clinician, protected by idempotency to prevent duplicate accounts."""
    data = request.get_json()
    username = data.get("username")
    
    # ... Validation and User/Doctor insertion logic ...

    response_payload = {
        "message": "Clinical account provisioned successfully",
        "account_id": username,
        "status": "Awaiting initial verification"
    }
    
    return jsonify(sanitize_response(response_payload, role="ADMIN")), 201