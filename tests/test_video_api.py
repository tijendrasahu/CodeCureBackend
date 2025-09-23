import os
import pytest
import requests
import random

# Set the base URL for the API. It defaults to localhost:5000.
BASE = os.environ.get('TEST_BASE', 'http://localhost:5000')

# --- Pytest Fixtures: Reusable setup code for tests ---

@pytest.fixture(scope="module")
def approved_doctor_token():
    """
    Logs in the pre-approved doctor using the credentials you provided
    and returns a valid JWT.
    """
    payload = {
        "doctor_id": "D-IGIXS",
        "password": "Poorveshnew123#"
    }
    r = requests.post(f'{BASE}/doctors/login', json=payload)
    # If this fails, it might mean the doctor is not in the DB or not approved.
    # Run populate_db.py or manually approve the doctor.
    assert r.status_code == 200, f"Doctor login failed: {r.text}"
    return r.json()['access_token']

@pytest.fixture(scope="module")
def registered_patient_details():
    """Registers a new patient and returns their details and a valid JWT."""
    mobile = f"9100{random.randint(100000, 999999)}"
    patient_data = {
        'first_name': 'VideoTest', 'last_name': 'Patient', 'age': '25',
        'dob': '2000-01-01', 'sex': 'M', 'mobile': mobile,
        'password': 'videopass', 'confirm_password': 'videopass', 'otp': '4444'
    }
    r_reg = requests.post(f'{BASE}/patients/register', json=patient_data)
    assert r_reg.status_code == 201
    
    # Login the patient to get their token
    r_login = requests.post(f'{BASE}/patients/login', json={'mobile': mobile, 'password': 'videopass'})
    assert r_login.status_code == 200

    details = r_reg.json()
    details['token'] = r_login.json()['access_token']
    return details

# --- Test Cases for the New Video API ---

def test_doctor_creates_room_and_gets_token(approved_doctor_token, registered_patient_details):
    """
    Tests the main success case: A doctor initiates a call, a new room is created,
    and the doctor receives a valid room_id and auth token.
    """
    headers = {'Authorization': f'Bearer {approved_doctor_token}', 'Content-Type': 'application/json'}
    payload = {'patient_id': registered_patient_details['unique_id']}

    r = requests.post(f'{BASE}/video/create-room', headers=headers, json=payload)
    
    assert r.status_code == 200, f"API failed with: {r.text}"
    data = r.json()
    assert 'room_id' in data
    assert 'token' in data
    assert isinstance(data['room_id'], str)
    assert isinstance(data['token'], str)
    
def test_patient_gets_auth_token(registered_patient_details, approved_doctor_token):
    """
    Tests the patient's part of the flow:
    1. Doctor creates a room.
    2. Patient uses that room_id to get their own auth token.
    """
    # Step 1: Doctor creates a room to get a valid room_id
    doc_headers = {'Authorization': f'Bearer {approved_doctor_token}', 'Content-Type': 'application/json'}
    doc_payload = {'patient_id': registered_patient_details['unique_id']}
    r_doc = requests.post(f'{BASE}/video/create-room', headers=doc_headers, json=doc_payload)
    assert r_doc.status_code == 200
    room_id = r_doc.json()['room_id']

    # Step 2: Patient uses the room_id to request their token
    patient_headers = {'Authorization': f'Bearer {registered_patient_details["token"]}', 'Content-Type': 'application/json'}
    patient_payload = {'room_id': room_id}
    r_patient = requests.post(f'{BASE}/video/patient/auth-token', headers=patient_headers, json=patient_payload)

    assert r_patient.status_code == 200, f"API failed with: {r_patient.text}"
    data = r_patient.json()
    assert 'token' in data
    assert isinstance(data['token'], str)

def test_patient_cannot_create_room(registered_patient_details):
    """
    Security Test: Ensures that a patient (non-doctor role) cannot create a video room.
    Expects a 403 Forbidden error.
    """
    headers = {'Authorization': f'Bearer {registered_patient_details["token"]}', 'Content-Type': 'application/json'}
    # A patient should not have a patient_id to pass, but we test the endpoint's security
    payload = {'patient_id': 'some-other-patient-id'} 

    r = requests.post(f'{BASE}/video/create-room', headers=headers, json=payload)
    assert r.status_code == 403 # Forbidden
    assert r.json()['error'] == "Access forbidden: Doctor access required"
