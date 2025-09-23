import os
import requests
import jwt
import time
import uuid
from flask import Blueprint, request, current_app, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

video_bp = Blueprint('video', __name__)

# --- CONFIGURATION ---
HMS_ACCESS_KEY = os.getenv('HMS_ACCESS_KEY')
HMS_SECRET = os.getenv('HMS_SECRET')
HMS_TEMPLATE_ID = os.getenv('HMS_TEMPLATE_ID')
HMS_API_BASE_URL = "https://api.100ms.live/v2"

# --- Database Collection Helpers ---
def patients_collection():
    return current_app.db['patients']
def doctors_collection():
    return current_app.db['doctors']

# --- Helper functions for 100ms API ---

def _get_management_token():
    """Generates a short-lived JWT to talk to the 100ms Management API."""
    if not HMS_ACCESS_KEY or not HMS_SECRET:
        print("DEBUG: HMS_ACCESS_KEY or HMS_SECRET is missing in .env file.")
        return None
    
    payload = {
        'access_key': HMS_ACCESS_KEY, 'type': 'management', 'version': 2,
        'jti': str(uuid.uuid4()), 'iat': int(time.time()),
        'nbf': int(time.time()), 'exp': int(time.time()) + (24 * 3600)
    }
    return jwt.encode(payload, HMS_SECRET, algorithm='HS256')

def _create_100ms_room(patient_name):
    """Creates a new, temporary room on the 100ms server."""
    management_token = _get_management_token()
    if not management_token: return None
        
    if not HMS_TEMPLATE_ID:
        print("DEBUG: HMS_TEMPLATE_ID is missing in .env file.")
        return None

    headers = {'Authorization': f'Bearer {management_token}', 'Content-Type': 'application/json'}
    payload = {
        'name': f"Call with {patient_name} - {time.strftime('%Y-%m-%d %H:%M')}",
        'description': 'One-on-one telemedicine call',
        'template_id': HMS_TEMPLATE_ID
    }
    
    try:
        res = requests.post(f"{HMS_API_BASE_URL}/rooms", json=payload, headers=headers)
        if res.status_code != 200:
            print(f"--- 100ms ERROR (Room Creation) ---\nSTATUS: {res.status_code}\nBODY: {res.text}\n-------------------")
        res.raise_for_status()
        return res.json().get('id')
    except requests.exceptions.RequestException as e:
        print(f"Error creating 100ms room: {e}")
        return None

def _get_100ms_auth_token(user_id, room_id, role):
    """
    Generates a short-lived Auth Token JWT for a user to join a room directly.
    This does NOT make an API call, it creates the token locally as per 100ms docs.
    """
    if not HMS_ACCESS_KEY or not HMS_SECRET:
        print("DEBUG: HMS_ACCESS_KEY or HMS_SECRET is missing in .env file.")
        return None

    payload = {
        'access_key': HMS_ACCESS_KEY,
        'room_id': room_id,
        'user_id': user_id,
        'role': role,
        'type': 'app',
        'version': 2,
        'jti': str(uuid.uuid4()),
        'iat': int(time.time()),
        'nbf': int(time.time()),
        'exp': int(time.time()) + (24 * 3600)  # 24 hours validity
    }
    
    try:
        token = jwt.encode(payload, HMS_SECRET, algorithm='HS256')
        return token
    except Exception as e:
        print(f"Error generating 100ms auth token: {e}")
        return None

# --- Super Easy Endpoints ---
@video_bp.route('/create-room', methods=['POST'])
@jwt_required()
def create_room_and_get_token():
    if get_jwt().get("role") != "doctor":
        return jsonify({"error": "Access forbidden: Doctor access required"}), 403
    
    doctor_id = get_jwt_identity()
    patient_id = request.get_json().get('patient_id')
    if not patient_id:
        return jsonify({"error": "patient_id is required"}), 400

    patient = patients_collection().find_one({'unique_id': patient_id})
    if not patient:
        return jsonify({"error": "Patient not found"}), 404
    patient_name = f"{patient.get('first_name')} {patient.get('last_name')}"

    new_room_id = _create_100ms_room(patient_name)
    if not new_room_id:
        return jsonify({"error": "Failed to create video call room. Check server logs."}), 503

    doctor_token = _get_100ms_auth_token(user_id=doctor_id, room_id=new_room_id, role='doctor')
    if not doctor_token:
        return jsonify({"error": "Failed to generate doctor token. Check server logs."}), 503
    
    return jsonify({'room_id': new_room_id, 'token': doctor_token})

@video_bp.route('/patient/auth-token', methods=['POST'])
@jwt_required()
def get_patient_auth_token():
    patient_id = get_jwt_identity()
    room_id = request.get_json().get('room_id')
    if not room_id:
        return jsonify({"error": "room_id is required"}), 400

    token = _get_100ms_auth_token(user_id=patient_id, room_id=room_id, role='patient')
    if not token:
        return jsonify({"error": "100ms service is not configured or failed to generate token."}), 503
        
    return jsonify({'token': token})

