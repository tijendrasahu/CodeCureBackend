import os
import pytest
import requests
from io import BytesIO
from pymongo import MongoClient
from config import Config
import certifi
import random

# Set the base URL for the API. It defaults to localhost:5000.
BASE = os.environ.get('TEST_BASE', 'http://localhost:5000')

# --- Pytest Fixtures: Reusable setup code for tests ---

@pytest.fixture(scope="module")
def db_connection():
    """Provides a direct connection to the test database for setup and verification."""
    client = MongoClient(Config.MONGO_URI, tlsCAFile=certifi.where())
    db = client[Config.MONGO_DB_NAME]
    yield db
    # Teardown: Clean up created test data after all tests in the module are done
    db.doctors.delete_many({"first_name": {"$in": ["Approved", "Unapproved"]}})
    db.patients.delete_many({"first_name": "PatientForDoc"})
    db.issues.delete_many({"text": "Test issue from patient for doctor view"})
    client.close()

@pytest.fixture(scope="module")
def registered_patient(db_connection):
    """Registers a patient via the API and returns their details."""
    mobile = f"9000{random.randint(100000, 999999)}"
    patient_data = {
        'first_name': 'PatientForDoc', 'last_name': 'Test', 'age': '40',
        'dob': '1985-01-01', 'sex': 'F', 'mobile': mobile,
        'password': 'patientpass', 'confirm_password': 'patientpass', 'otp': '4444'
    }
    r = requests.post(f'{BASE}/patients/register', json=patient_data)
    assert r.status_code == 201
    # Add mobile to the returned data for login purposes
    response_data = r.json()
    response_data['mobile'] = mobile
    return response_data

@pytest.fixture(scope="module")
def approved_doctor_token(db_connection):
    """
    Registers a doctor, MANUALLY approves them in the DB (simulating an admin), 
    and returns a valid login token for testing protected endpoints.
    """
    payload = {
        'first_name': 'Approved', 'last_name': 'Doctor', 'password': 'approvedpass',
        'confirm_password': 'approvedpass', 'specialization': 'General Medicine', 'branch': 'Main'
    }
    r_reg = requests.post(f'{BASE}/doctors/register', json=payload)
    assert r_reg.status_code == 201
    doctor_id = r_reg.json()['doctor_id']

    # Manually approve the doctor in the database, just like an admin would
    db_connection.doctors.update_one(
        {"doctor_id": doctor_id},
        {"$set": {"approved_status": True}}
    )

    # Log in as the now-approved doctor to get a token
    r_login = requests.post(f'{BASE}/doctors/login', json={'doctor_id': doctor_id, 'password': 'approvedpass'})
    assert r_login.status_code == 200
    return r_login.json()['access_token']

@pytest.fixture(scope="module")
def unapproved_doctor_id():
    """Registers a new doctor who will remain unapproved for testing purposes."""
    payload = {
        'first_name': 'Unapproved', 'last_name': 'Doctor', 'password': 'unapprovedpass',
        'confirm_password': 'unapprovedpass', 'specialization': 'Pediatrics', 'branch': 'West'
    }
    r = requests.post(f'{BASE}/doctors/register', json=payload)
    assert r.status_code == 201
    return r.json()['doctor_id']

# --- Test Cases for Doctor Endpoints ---

def test_doctor_login_pending_approval(unapproved_doctor_id):
    """Tests that an unapproved doctor cannot log in (expects 403 Forbidden)."""
    payload = {'doctor_id': unapproved_doctor_id, 'password': 'unapprovedpass'}
    r = requests.post(f'{BASE}/doctors/login', json=payload)
    assert r.status_code == 403
    assert r.json()['error'] == "Your account is pending admin approval."

def test_get_all_patient_issues(approved_doctor_token, registered_patient):
    """Tests if an approved doctor can successfully retrieve a list of all patient issues."""
    headers = {'Authorization': f'Bearer {approved_doctor_token}'}

    # The patient submits an issue so the list is not empty
    patient_login_r = requests.post(f'{BASE}/patients/login', json={'mobile': registered_patient['mobile'], 'password': 'patientpass'})
    patient_token = patient_login_r.json()['access_token']
    issue_text = "Test issue from patient for doctor view"
    requests.post(f'{BASE}/patients/issue', headers={'Authorization': f'Bearer {patient_token}'}, data={'text': issue_text})

    # The doctor fetches all issues
    r = requests.get(f'{BASE}/doctors/issues/all', headers=headers)
    assert r.status_code == 200
    issues = r.json()
    assert isinstance(issues, list)
    assert any(issue_text in issue.get('text', '') and issue.get('patient_name') == "PatientForDoc Test" for issue in issues)

def test_get_specific_patient_file(approved_doctor_token, registered_patient):
    """Tests if an approved doctor can retrieve a complete file for a specific patient."""
    headers = {'Authorization': f'Bearer {approved_doctor_token}'}
    patient_id = registered_patient['unique_id']

    r = requests.get(f'{BASE}/doctors/patient/{patient_id}', headers=headers)
    assert r.status_code == 200
    patient_file = r.json()
    assert 'profile' in patient_file and 'reports' in patient_file and 'issues' in patient_file
    assert patient_file['profile']['first_name'] == 'PatientForDoc'

def test_add_prescription_to_issue(approved_doctor_token, registered_patient, db_connection):
    """Tests if an approved doctor can add a prescription note to a patient's issue."""
    headers = {'Authorization': f'Bearer {approved_doctor_token}', 'Content-Type': 'application/json'}

    # Find the issue submitted by our test patient
    patient_issue = db_connection.issues.find_one({'user_id': registered_patient['unique_id']})
    assert patient_issue is not None
    issue_id = str(patient_issue['_id'])

    # Doctor adds a prescription
    prescription_payload = {
        "prescription_text": "Take Paracetamol 500mg twice a day.",
        "doctor_notes": "Follow up in 3 days."
    }
    r = requests.post(f'{BASE}/doctors/issue/{issue_id}/prescribe', headers=headers, json=prescription_payload)
    assert r.status_code == 200
    assert r.json()['message'] == "Prescription added successfully"

    # Verify the prescription was actually added in the database
    updated_issue = db_connection.issues.find_one({'_id': patient_issue['_id']})
    assert 'prescription' in updated_issue
    assert updated_issue['prescription']['text'] == "Take Paracetamol 500mg twice a day."

def test_doctor_uploads_report_for_patient(approved_doctor_token, registered_patient):
    """Tests if an approved doctor can successfully upload a medical report for a patient."""
    headers = {'Authorization': f'Bearer {approved_doctor_token}'}
    patient_id = registered_patient['unique_id']
    report_content = BytesIO(b'Doctor uploaded lab results.')
    files = {'file': ('lab_results.pdf', report_content, 'application/pdf')}

    r = requests.post(f'{BASE}/doctors/patient/{patient_id}/upload-report', headers=headers, files=files)
    assert r.status_code == 201
    response_data = r.json()
    assert "Report uploaded successfully" in response_data['message']
    assert 'filename' in response_data

