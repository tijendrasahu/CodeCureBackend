from flask import Blueprint, request, current_app, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from utils.auth import hash_password, verify_password
# Updated imports to use the new free helper functions
from utils.helpers import free_translate, free_audio_to_text, save_file_and_get_name
import datetime
import os

patients_bp = Blueprint('patients', __name__)

# Collections
def patients_collection():
    return current_app.db['patients']

def events_collection():
    return current_app.db['events']

def reports_collection():
    return current_app.db['reports']

def issues_collection():
    return current_app.db['issues']


# ---------------------------
# REGISTER
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
        'created_at': datetime.datetime.utcnow(),
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
# PROFILE DETAILS
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


# ---------------------------
# PROFILE UPDATE
# ---------------------------
@patients_bp.route('/profile-details-update', methods=['PUT'])
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
# REPORT UPLOAD & LIST
# ---------------------------
@patients_bp.route('/report/upload', methods=['POST'])
@jwt_required()
def report_upload():
    current_user_id = get_jwt_identity()
    user = patients_collection().find_one({'unique_id': current_user_id})
    if not user:
        return jsonify({'error':'User not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error':'No file uploaded'}), 400
    file = request.files['file']
    filename = save_file_and_get_name(current_app.config['UPLOAD_FOLDER'], file)
    reports_collection().insert_one({
        'user_id': current_user_id,
        'mobile': user['mobile'],
        'filename': filename,
        'original_name': file.filename,
        'uploaded_at': datetime.datetime.utcnow()
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


@patients_bp.route('/report/download/<filename>', methods=['GET'])
def report_download(filename):
    uploads = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(uploads, filename, as_attachment=True)


# ---------------------------
# ISSUE SUBMISSION
# ---------------------------
@patients_bp.route('/issue', methods=['POST'])
@jwt_required()
def issue_submit():
    current_user_id = get_jwt_identity()
    user = patients_collection().find_one({'unique_id': current_user_id})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.form.to_dict() or {}
    note = data.get('text')
    # Expect the client app to send the language code for audio
    language_code = data.get('language_code', 'en-US') # Default to English if not provided

    audio_file = request.files.get('audio') if 'audio' in request.files else None
    
    stored = {
        'user_id': current_user_id,
        'mobile': user['mobile'],
        'created_at': datetime.datetime.utcnow()
    }
    
    if note:
        stored['text'] = note
        # Use the real translation function
        stored['translated'] = free_translate(note, target_lang='en')
        
    if audio_file:
        filename = save_file_and_get_name(current_app.config['UPLOAD_FOLDER'], audio_file)
        stored['audio_filename'] = filename
        
        # Get the full path to the saved file for processing
        full_audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # Use the real audio-to-text function
        stored['audio_transcript'] = free_audio_to_text(full_audio_path, language_code)
        
    issues_collection().insert_one(stored)
    return jsonify({'message':'Issue submitted'}), 201
