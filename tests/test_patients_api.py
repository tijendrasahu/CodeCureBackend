import os
import random
import pytest
import requests
from io import BytesIO

BASE = os.environ.get('TEST_BASE', 'http://localhost:5000')

def get_unique_mobile():
    """Generates a unique mobile number for each test run to avoid conflicts."""
    return str(random.randint(9000000000, 9999999999))

@pytest.fixture(scope="module")
def patient_token_and_mobile():
    """
    A pytest fixture that runs once per test module.
    It registers a new patient, logs them in, and provides the auth token
    and mobile number to the tests that need it.
    """
    mobile = get_unique_mobile()

    # Register a new patient
    register_payload = {
        'first_name': 'Test', 'last_name': 'User', 'age': '30',
        'dob': '1995-01-01', 'sex': 'M', 'mobile': mobile,
        'password': 'testpass', 'confirm_password': 'testpass', 'otp': '4444'
    }
    r_reg = requests.post(f'{BASE}/patients/register', json=register_payload)
    assert r_reg.status_code in (200, 201)

    # Login with the new patient's credentials
    login_payload = {'mobile': mobile, 'password': 'testpass'}
    r_login = requests.post(f'{BASE}/patients/login', json=login_payload)
    assert r_login.status_code == 200
    token = r_login.json().get('access_token')
    assert token
    return token, mobile


def test_register_and_login(patient_token_and_mobile):
    """Tests that the fixture successfully gets a token."""
    token, _ = patient_token_and_mobile
    assert isinstance(token, str)
    assert len(token) > 20


def test_profile_details(patient_token_and_mobile):
    """Tests fetching profile details for a logged-in user."""
    token, _ = patient_token_and_mobile
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.get(f'{BASE}/patients/profile-details', headers=headers)
    assert r.status_code == 200
    profile = r.json().get('profile')
    assert 'mobile' in profile
    assert 'first_name' in profile


def test_profile_update(patient_token_and_mobile):
    """Tests updating the profile for a logged-in user."""
    token, _ = patient_token_and_mobile
    headers = {'Authorization': f'Bearer {token}'}
    payload = {
        'blood_group': 'O+', 'email': 'test@example.com',
        'category': 'General', 'father': 'Father Name',
        'mother': 'Mother Name', 'address': 'Test Address'
    }
    r = requests.put(f'{BASE}/patients/profile-details-update', headers=headers, data=payload)
    assert r.status_code == 200
    profile = r.json().get('profile')
    assert profile['blood_group'] == 'O+'
    assert profile['email'] == 'test@example.com'


def test_events():
    """Tests the public events endpoint."""
    r = requests.get(f'{BASE}/patients/events')
    assert r.status_code == 200
    data = r.json()
    assert 'events' in data
    assert isinstance(data['events'], list)


def test_file_upload_serving_and_downloading(patient_token_and_mobile):
    """
    NEW TEST: Tests the full file lifecycle:
    1. Uploads a profile image and verifies it can be served.
    2. Uploads a report and verifies it can be downloaded.
    """
    token, _ = patient_token_and_mobile
    headers = {'Authorization': f'Bearer {token}'}

    # 1. Test Profile Image Upload and Serving
    image_content = BytesIO(b'dummy_image_bytes')
    files_image = {'profile_image': ('profile.jpg', image_content, 'image/jpeg')}
    r_upload_img = requests.put(f'{BASE}/patients/profile-details-update', headers=headers, files=files_image)
    assert r_upload_img.status_code == 200
    profile_data = r_upload_img.json().get('profile', {})
    image_filename = profile_data.get('profile_image')
    assert image_filename is not None

    r_serve_img = requests.get(f'{BASE}/patients/uploads/{image_filename}')
    assert r_serve_img.status_code == 200
    assert r_serve_img.content == b'dummy_image_bytes'

    # 2. Test Report Upload and Download
    report_content = BytesIO(b'dummy_report_bytes')
    files_report = {'file': ('report.pdf', report_content, 'application/pdf')}
    r_upload_rep = requests.post(f'{BASE}/patients/report/upload', headers=headers, files=files_report)
    assert r_upload_rep.status_code == 201
    report_filename = r_upload_rep.json().get('filename')
    assert report_filename is not None
    
    r_download_rep = requests.get(f'{BASE}/patients/report/download/{report_filename}')
    assert r_download_rep.status_code == 200
    assert "attachment" in r_download_rep.headers['Content-Disposition']
    assert r_download_rep.content == b'dummy_report_bytes'


def test_issue_submit_and_list(patient_token_and_mobile):
    """
    Tests submitting a new text-based issue and then verifying
    that it appears in the user's issue list.
    """
    token, _ = patient_token_and_mobile
    headers = {'Authorization': f'Bearer {token}'}
    issue_text = f"Test issue for listing at {random.randint(1000, 9999)}"
    
    r_submit = requests.post(f'{BASE}/patients/issue', headers=headers, data={'text': issue_text})
    assert r_submit.status_code == 201
    assert r_submit.json()['message'] == 'Issue submitted'

    r_list = requests.get(f'{BASE}/patients/issue/list', headers=headers)
    assert r_list.status_code == 200
    issues = r_list.json().get('issues')
    assert isinstance(issues, list)
    assert any(issue.get('text') == issue_text for issue in issues)


def test_ai_prompt_endpoint(patient_token_and_mobile):
    """
    Tests the hybrid AI prompt endpoint with its different logic branches.
    """
    token, _ = patient_token_and_mobile
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    # Case 1: Test the emergency keyword rule
    payload_emergency = {'prompt': 'I am having severe chest pain'}
    r_emergency = requests.post(f'{BASE}/patients/prompt', headers=headers, json=payload_emergency)
    assert r_emergency.status_code == 200
    assert "consult a doctor immediately" in r_emergency.json()['response']

    # Case 2: Test a feature keyword rule
    payload_feature = {'prompt': 'How do I book an appointment?'}
    r_feature = requests.post(f'{BASE}/patients/prompt', headers=headers, json=payload_feature)
    assert r_feature.status_code == 200
    assert "preferred date and specialty" in r_feature.json()['response']

    # Case 3: Test the general AI fallback
    payload_general = {'prompt': 'What are some remedies for a common cold?'}
    r_general = requests.post(f'{BASE}/patients/prompt', headers=headers, json=payload_general)
    assert r_general.status_code == 200
    response_data = r_general.json()
    assert 'response' in response_data
    assert isinstance(response_data['response'], str)
    assert len(response_data['response']) > 10

