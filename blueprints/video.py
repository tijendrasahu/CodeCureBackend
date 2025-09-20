import os
import uuid
import datetime
from flask import Blueprint, request, current_app, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from agora_token_builder import RtcTokenBuilder

video_bp = Blueprint('video', __name__)

# --- CONFIGURATION (Yeh .env file se aayengi) ---
AGORA_APP_ID = os.getenv('AGORA_APP_ID')
AGORA_APP_CERTIFICATE = os.getenv('AGORA_APP_CERTIFICATE')

# --- Database Collection Helpers ---
def patients_collection():
    return current_app.db['patients']
def doctors_collection():
    return current_app.db['doctors']

# --- Placeholder for Push Notification Logic ---
def send_call_notification(patient_unique_id, room_name, doctor_name):
    """
    Simulates sending a push notification to the patient's device.
    In a real app, this would use a service like Firebase Cloud Messaging (FCM).
    """
    patient = patients_collection().find_one({'unique_id': patient_unique_id})
    if not patient:
        return False
        
    print(f"---- PUSH NOTIFICATION SIMULATION ----")
    print(f"To: Patient {patient.get('first_name')} (Device ID: ...)")
    print(f"From: {doctor_name}")
    print(f"Message: Incoming video call...")
    print(f"Call Data (Payload): {{ 'room_name': '{room_name}' }}")
    print(f"--------------------------------------")
    return True

# ---------------------------
# INITIATE A CALL (Doctor Only)
# ---------------------------
@video_bp.route('/call/initiate', methods=['POST'])
@jwt_required()
def initiate_call():
    jwt_data = get_jwt()
    if jwt_data.get("role") != "doctor":
        return jsonify({"error": "Access forbidden: Doctor access required"}), 403

    data = request.get_json()
    patient_to_call_id = data.get('patient_id')
    
    # Get doctor's name for a more personal notification
    doctor_id = get_jwt_identity()
    doctor = doctors_collection().find_one({"doctor_id": doctor_id})
    doctor_name = f"Dr. {doctor.get('first_name', '')} {doctor.get('last_name', '')}" if doctor else "Your Doctor"

    if not patient_to_call_id:
        return jsonify({"error": "patient_id is required"}), 400

    room_name = str(uuid.uuid4())

    if not send_call_notification(patient_to_call_id, room_name, doctor_name):
        return jsonify({"error": "Could not notify patient"}), 500

    return jsonify({"message": "Call initiated, notifying patient...", "room_name": room_name}), 200

# ==============================================================================
#  !! YEH NAYE, BEHTAR TOKEN ENDPOINTS HAIN !!
# ==============================================================================
def _generate_agora_token(room_name):
    """Helper function to generate a new Agora token."""
    if not AGORA_APP_ID or not AGORA_APP_CERTIFICATE:
        return None
    
    expire_time_in_seconds = 3600 # 1 hour
    current_timestamp = int(datetime.datetime.now(datetime.UTC).timestamp())
    privilege_expired_ts = current_timestamp + expire_time_in_seconds

    token = RtcTokenBuilder.buildTokenWithUid(
        AGORA_APP_ID, AGORA_APP_CERTIFICATE, room_name,
        0, 0, privilege_expired_ts
    )
    return token

# ---------------------------
# GET TOKEN FOR A DOCTOR
# ---------------------------
@video_bp.route('/doctor/token', methods=['POST'])
@jwt_required()
def get_doctor_token():
    jwt_data = get_jwt()
    if jwt_data.get("role") != "doctor":
        return jsonify({"error": "Access forbidden: Doctor access required"}), 403
    
    data = request.get_json()
    room_name = data.get('room_name')
    if not room_name:
        return jsonify({"error": "room_name is required"}), 400
        
    token = _generate_agora_token(room_name)
    if not token:
        return jsonify({"error": "Agora service is not configured on the server."}), 503
        
    return jsonify({'token': token})

# ---------------------------
# GET TOKEN FOR A PATIENT
# ---------------------------
@video_bp.route('/patient/token', methods=['POST'])
@jwt_required()
def get_patient_token():
    # Patient role is implied since doctors have their own endpoint
    data = request.get_json()
    room_name = data.get('room_name')
    if not room_name:
        return jsonify({"error": "room_name is required"}), 400
        
    token = _generate_agora_token(room_name)
    if not token:
        return jsonify({"error": "Agora service is not configured on the server."}), 503
        
    return jsonify({'token': token})
