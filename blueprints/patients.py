from flask import Blueprint, request, current_app, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from utils.auth import hash_password, verify_password
from utils.helpers import free_translate, free_audio_to_text, save_file_and_get_name
from utils.ai_model import get_ai_response
import datetime
import os
from bson.objectid import ObjectId

patients_bp = Blueprint('patients', __name__)

# --- Database Collection Helpers ---
def patients_collection():
    return current_app.db['patients']

def events_collection():
    return current_app.db['events']

def reports_collection():
    return current_app.db['reports']

def issues_collection():
    return current_app.db['issues']

# --- Rule-Based Logic for Hybrid AI ---
EMERGENCY_SYMPTOMS = [
    "chest pain", "difficulty breathing", "shortness of breath",
    "unconscious", "bleeding", "seizure", "heart attack",
    "stroke", "severe headache", "vision loss", "suicide"
]

FEATURE_KEYWORDS = {
    ("book", "appointment"): "📅 I can help you book a doctor’s appointment. Please share your preferred date and specialty.",
    ("upload", "report"): "📑 You can upload your medical report. I will securely attach it to your health record.",
    ("pharmacy", "medicine"): "💊 I can check nearby pharmacies for medicine availability.",
    ("emergency",): "🚑 For any medical emergency, please contact your nearest hospital immediately.",
    ("blockchain", "security"): "🔐 Your medical records are secured with advanced technology for privacy and transparency.",
    ("opd",): "🏥 I can help manage OPD bookings and doctor schedules."
}

# ---------------------------
# REGISTRATION
# ---------------------------
@patients_bp.route('/register', methods=['POST'])
def register():
    data = request.form.to_dict() or request.get_json() or {}
    required = ['first_name','last_name','age','dob','sex','mobile','password','confirm_password','otp']
    for r in required:
        if r not in data:
            return jsonify({'error': f'Missing {r}'}), 400

    if data['password'] != data['confirm_password']:
        return jsonify({'error':'Passwords do not match'}), 400

    if data.get('otp') != '4444':
        return jsonify({'error':'Invalid OTP'}), 400

    if patients_collection().find_one({'mobile': data['mobile']}):
        return jsonify({'error':'Mobile already registered'}), 400

    patient = {
        'first_name': data['first_name'],
        'last_name': data['last_name'],
        'age': int(data['age']),
        'dob': data['dob'],
        'sex': data['sex'],
        'mobile': data['mobile'],
        'password_hash': hash_password(data['password']),
        'created_at': datetime.datetime.now(datetime.UTC),
        'profile': {},
        'unique_id': os.urandom(8).hex()
    }
    patients_collection().insert_one(patient)
    return jsonify({'message':'Registered successfully','unique_id': patient['unique_id']}), 201


# ---------------------------
# LOGIN
# ---------------------------
@patients_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    if 'mobile' not in data or 'password' not in data:
        return jsonify({'error':'mobile and password required'}), 400
    user = patients_collection().find_one({'mobile': data['mobile']})
    if not user or not verify_password(user.get('password_hash',''), data['password']):
        return jsonify({'error':'Invalid credentials'}), 401
    access = create_access_token(identity=user['unique_id'])
    return jsonify({'access_token': access}), 200


# ---------------------------
# PROFILE
# ---------------------------
@patients_bp.route('/profile-details', methods=['GET'])
@jwt_required()
def profile_details():
    current_user_id = get_jwt_identity()
    user = patients_collection().find_one({'unique_id': current_user_id}, {'password_hash':0})
    if not user:
        return jsonify({'error':'User not found'}), 404
    user['_id'] = str(user['_id'])
    return jsonify({'profile': user}), 200


@patients_bp.route('/profile-details-update', methods=['PUT', 'POST'])
@jwt_required()
def profile_update():
    current_user_id = get_jwt_identity()
    user = patients_collection().find_one({'unique_id': current_user_id})
    if not user:
        return jsonify({'error':'User not found'}), 404

    data = request.form.to_dict() or {}
    profile = user.get('profile', {})

    for k in ['blood_group','email','category','father','mother','address']:
        if k in data:
            profile[k] = data[k]

    if 'profile_image' in request.files:
        file = request.files['profile_image']
        filename = save_file_and_get_name(current_app.config['UPLOAD_FOLDER'], file)
        profile['profile_image'] = filename

    patients_collection().update_one({'unique_id': current_user_id}, {'$set': {'profile': profile}})
    return jsonify({'message':'Profile updated', 'profile': profile}), 200


# ---------------------------
# EVENTS
# ---------------------------
@patients_bp.route('/events', methods=['GET'])
def events():
    evs = list(events_collection().find({}))
    for e in evs:
        e['_id'] = str(e.get('_id'))
    return jsonify({'events': evs}), 200


# ---------------------------
# REPORTS & FILE SERVING
# ---------------------------
@patients_bp.route('/report/upload', methods=['POST'])
@jwt_required()
def report_upload():
    current_user_id = get_jwt_identity()
    if not patients_collection().find_one({'unique_id': current_user_id}):
        return jsonify({'error':'User not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error':'No file uploaded'}), 400
    file = request.files['file']
    filename = save_file_and_get_name(current_app.config['UPLOAD_FOLDER'], file)
    reports_collection().insert_one({
        'user_id': current_user_id,
        'filename': filename,
        'original_name': file.filename,
        'uploaded_at': datetime.datetime.now(datetime.UTC)
    })
    return jsonify({'message':'Uploaded','filename': filename}), 201


@patients_bp.route('/report/list', methods=['GET'])
@jwt_required()
def report_list():
    current_user_id = get_jwt_identity()
    files = list(reports_collection().find({'user_id': current_user_id}))
    for f in files:
        f['_id'] = str(f['_id'])
    return jsonify({'reports': files}), 200

# ==============================================================================
#  !! UNIVERSAL FILE SERVER !!
# ==============================================================================
@patients_bp.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    """
    Serves any file from the UPLOAD_FOLDER (e.g., profile pictures, audio, etc.).
    This single endpoint handles all file serving needs.
    """
    uploads_dir = os.path.join(current_app.root_path, current_app.config.get('UPLOAD_FOLDER', 'uploads'))
    return send_from_directory(uploads_dir, filename)


# ---------------------------
# ISSUES
# ---------------------------
@patients_bp.route('/issue', methods=['POST'])
@jwt_required()
def issue_submit():
    current_user_id = get_jwt_identity()
    if not patients_collection().find_one({'unique_id': current_user_id}):
        return jsonify({'error': 'User not found'}), 404

    data = request.form.to_dict() or {}
    note = data.get('text')
    language_code = data.get('language_code', 'en-US')
    audio_file = request.files.get('audio') if 'audio' in request.files else None
    
    stored = {
        'user_id': current_user_id,
        'created_at': datetime.datetime.now(datetime.UTC),
        'status': 'Pending',
        'prescription': None
    }
    
    if note:
        stored['text'] = note
        stored['translated'] = free_translate(note, target_lang='en')
        
    if audio_file:
        filename = save_file_and_get_name(current_app.config['UPLOAD_FOLDER'], audio_file)
        stored['audio_filename'] = filename
        full_audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        stored['audio_transcript'] = free_audio_to_text(full_audio_path, language_code)
        
    issues_collection().insert_one(stored)
    return jsonify({'message':'Issue submitted'}), 201


@patients_bp.route('/issue/list', methods=['GET'])
@jwt_required()
def issue_list():
    current_user_id = get_jwt_identity()
    user_issues = list(issues_collection().find({'user_id': current_user_id}))
    for issue in user_issues:
        issue['_id'] = str(issue['_id'])
    return jsonify({'issues': user_issues}), 200


@patients_bp.route('/issue/<string:issue_id>', methods=['DELETE'])
@jwt_required()
def delete_issue(issue_id):
    current_user_id = get_jwt_identity()

    try:
        issue_to_delete = issues_collection().find_one({'_id': ObjectId(issue_id)})
    except Exception:
        return jsonify({"error": "Invalid issue ID format"}), 400

    if not issue_to_delete:
        return jsonify({"error": "Issue not found"}), 404

    if issue_to_delete.get('user_id') != current_user_id:
        return jsonify({"error": "Forbidden: You can only delete your own issues."}), 403

    result = issues_collection().delete_one({'_id': ObjectId(issue_id)})

    if result.deleted_count == 1:
        return jsonify({"message": "Issue deleted successfully"}), 200
    else:
        return jsonify({"error": "Failed to delete issue"}), 500

# ---------------------------
# HYBRID AI CHATBOT
# ---------------------------
@patients_bp.route('/prompt', methods=['POST'])
@jwt_required()
def handle_ai_prompt():
    current_user_id = get_jwt_identity()
    if not patients_collection().find_one({'unique_id': current_user_id}):
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({'error': 'Request must contain a "prompt" field.'}), 400
    
    user_prompt = data['prompt']

    try:
        translated_input = free_translate(user_prompt, target_lang='en').lower()
    except Exception:
        translated_input = user_prompt.lower()

    if any(symptom in translated_input for symptom in EMERGENCY_SYMPTOMS):
        return jsonify({"response": "⚠ These symptoms may be serious. Please consult a doctor immediately or seek emergency care."}), 200

    for keywords, response in FEATURE_KEYWORDS.items():
        if all(keyword in translated_input for keyword in keywords):
            return jsonify({"response": response}), 200

    system_prompt = (
        "You are a helpful and empathetic AI medical assistant for a rural healthcare app. "
        "Your primary goal is to understand the user's health issue and provide safe, preliminary guidance. "
        "The user might be writing in Hindi, Punjabi, English, or a mix (Hinglish).\n\n"
        "Provide a response in the SAME language as the user's prompt.\n"
        "If symptoms sound serious, strongly advise them to see a doctor immediately.\n"
        "At the end of EVERY response, you MUST include a disclaimer, translated into the user's language."
    )
    
    ai_result = get_ai_response(user_prompt, system_instruction=system_prompt)

    if "error" in ai_result:
        return jsonify(ai_result), 500
    
    return jsonify(ai_result), 200
