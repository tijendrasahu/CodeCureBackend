from flask import Blueprint, request, current_app, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity
from utils.auth import hash_password, verify_password
from utils.helpers import save_file_and_get_name
import datetime
import random
import string
from bson.objectid import ObjectId

doctors_bp = Blueprint('doctors', __name__)

# --- Database Collection Helpers ---
def doctors_collection():
    return current_app.db['doctors']

def patients_collection():
    return current_app.db['patients']
    
def issues_collection():
    return current_app.db['issues']
    
def reports_collection():
    return current_app.db['reports']

def generate_unique_doctor_id():
    while True:
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        doctor_id = f"D-{random_part}"
        if not doctors_collection().find_one({"doctor_id": doctor_id}):
            return doctor_id

# ---------------------------
# DOCTOR REGISTRATION
# ---------------------------
@doctors_bp.route('/register', methods=['POST'])
def doctor_register():
    data = request.get_json() or {}
    required = ['first_name', 'last_name', 'password', 'confirm_password', 'specialization', 'branch']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400

    if data['password'] != data['confirm_password']:
        return jsonify({'error': 'Passwords do not match'}), 400

    doctor_id = generate_unique_doctor_id()
    doctor_document = {
        "doctor_id": doctor_id,
        "first_name": data['first_name'],
        "last_name": data['last_name'],
        "password_hash": hash_password(data['password']),
        "specialization": data['specialization'],
        "branch": data['branch'],
        "approved_status": False,
        "registered_at": datetime.datetime.now(datetime.UTC)
    }
    doctors_collection().insert_one(doctor_document)
    return jsonify({
        "message": "Registration successful. Please wait for admin approval.",
        "doctor_id": doctor_id
    }), 201

# ---------------------------
# DOCTOR LOGIN
# ---------------------------
@doctors_bp.route('/login', methods=['POST'])
def doctor_login():
    data = request.get_json() or {}
    if 'doctor_id' not in data or 'password' not in data:
        return jsonify({'error': 'doctor_id and password are required'}), 400

    doctor = doctors_collection().find_one({"doctor_id": data['doctor_id']})
    if not doctor or not verify_password(doctor.get('password_hash', ''), data['password']):
        return jsonify({"error": "Invalid credentials"}), 401

    if not doctor.get('approved_status', False):
        return jsonify({"error": "Your account is pending admin approval."}), 403

    access_token = create_access_token(
        identity=doctor['doctor_id'], 
        additional_claims={'role': 'doctor'}
    )
    return jsonify(access_token=access_token), 200

# ---------------------------
# VIEW ALL PATIENT ISSUES
# ---------------------------
@doctors_bp.route('/issues/all', methods=['GET'])
@jwt_required()
def get_all_patient_issues():
    jwt_data = get_jwt()
    if jwt_data.get("role") != "doctor":
        return jsonify({"error": "Access forbidden: Doctor access required"}), 403

    all_issues = list(issues_collection().find({}))
    enriched_issues = []
    for issue in all_issues:
        patient = patients_collection().find_one({'unique_id': issue.get('user_id')})
        issue['patient_name'] = f"{patient.get('first_name')} {patient.get('last_name')}" if patient else "Unknown Patient"
        issue['_id'] = str(issue['_id'])
        enriched_issues.append(issue)
    return jsonify(enriched_issues), 200

# ---------------------------
# VIEW A SPECIFIC PATIENT'S FILE
# ---------------------------
@doctors_bp.route('/patient/<string:patient_unique_id>', methods=['GET'])
@jwt_required()
def get_patient_file(patient_unique_id):
    jwt_data = get_jwt()
    if jwt_data.get("role") != "doctor":
        return jsonify({"error": "Access forbidden: Doctor access required"}), 403

    patient_profile = patients_collection().find_one({'unique_id': patient_unique_id}, {'_id': 0, 'password_hash': 0})
    if not patient_profile:
        return jsonify({"error": "Patient not found"}), 404

    patient_reports = list(reports_collection().find({'user_id': patient_unique_id}, {'_id': 0}))
    patient_issues = list(issues_collection().find({'user_id': patient_unique_id}, {'_id': 0}))
    patient_file = {"profile": patient_profile, "reports": patient_reports, "issues": patient_issues}
    return jsonify(patient_file), 200

# ---------------------------
# ADD PRESCRIPTION OR NOTES TO AN ISSUE
# ---------------------------
@doctors_bp.route('/issue/<string:issue_id>/prescribe', methods=['POST'])
@jwt_required()
def prescribe_for_issue(issue_id):
    jwt_data = get_jwt()
    if jwt_data.get("role") != "doctor":
        return jsonify({"error": "Access forbidden: Doctor access required"}), 403

    current_doctor_id = get_jwt_identity()
    prescription_text = request.form.get('prescription_text')
    doctor_notes = request.form.get('doctor_notes')
    prescription_image = request.files.get('prescription_image') if 'prescription_image' in request.files else None

    if not prescription_text and not doctor_notes and not prescription_image:
        return jsonify({"error": "At least one field is required: prescription_text, doctor_notes, or prescription_image"}), 400

    try:
        if not issues_collection().find_one({'_id': ObjectId(issue_id)}):
            return jsonify({"error": "Issue not found"}), 404
    except Exception:
        return jsonify({"error": "Invalid issue ID format"}), 400

    prescription_data = {
        "doctor_id": current_doctor_id,
        "prescribed_at": datetime.datetime.now(datetime.UTC),
        "text": prescription_text,
        "notes": doctor_notes,
        "image_filename": None
    }
    if prescription_image:
        image_filename = save_file_and_get_name(current_app.config['UPLOAD_FOLDER'], prescription_image)
        prescription_data["image_filename"] = image_filename

    result = issues_collection().update_one(
        {'_id': ObjectId(issue_id)},
        {'$set': {'prescription': prescription_data}}
    )

    if result.modified_count == 1:
        return jsonify({"message": "Prescription added successfully"}), 200
    else:
        return jsonify({"error": "Failed to add prescription"}), 500

# ---------------------------
# UPLOAD REPORT FOR A PATIENT
# ---------------------------
@doctors_bp.route('/patient/<string:patient_unique_id>/upload-report', methods=['POST'])
@jwt_required()
def upload_report_for_patient(patient_unique_id):
    jwt_data = get_jwt()
    if jwt_data.get("role") != "doctor":
        return jsonify({"error": "Access forbidden: Doctor access required"}), 403

    current_doctor_id = get_jwt_identity()
    if not patients_collection().find_one({'unique_id': patient_unique_id}):
        return jsonify({"error": "Patient not found"}), 404

    if 'file' not in request.files or request.files['file'].filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    filename = save_file_and_get_name(current_app.config['UPLOAD_FOLDER'], file)
    report_document = {
        'user_id': patient_unique_id,
        'filename': filename,
        'original_name': file.filename,
        'uploaded_at': datetime.datetime.now(datetime.UTC),
        'uploaded_by': {'type': 'doctor', 'doctor_id': current_doctor_id}
    }
    reports_collection().insert_one(report_document)
    return jsonify({
        "message": f"Report uploaded successfully for patient {patient_unique_id}",
        "filename": filename
    }), 201

