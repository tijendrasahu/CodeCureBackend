import os
import random
import pytest
import requests
from io import BytesIO

BASE = os.environ.get('TEST_BASE', 'http://localhost:5000')

def get_unique_mobile():
    return str(random.randint(9000000000, 9999999999))

@pytest.fixture(scope="module")
def patient_token_and_mobile():
    """Register and login a patient; return (token, mobile)"""
    mobile = get_unique_mobile()

    # Register
    payload = {
        'first_name': 'Test',
        'last_name': 'User',
        'age': '30',
        'dob': '1995-01-01',
        'sex': 'M',
        'mobile': mobile,
        'password': 'testpass',
        'confirm_password': 'testpass',
        'otp': '4444'
    }
    r = requests.post(f'{BASE}/patients/register', json=payload)
    assert r.status_code in (200, 201)

    # Login
    r2 = requests.post(f'{BASE}/patients/login', json={'mobile': mobile, 'password': 'testpass'})
    assert r2.status_code == 200
    token = r2.json().get('access_token')
    assert token
    return token, mobile


def test_register_and_login(patient_token_and_mobile):
    token, _ = patient_token_and_mobile
    assert isinstance(token, str)
    assert len(token) > 20


def test_profile_details(patient_token_and_mobile):
    token, _ = patient_token_and_mobile
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.get(f'{BASE}/patients/profile-details', headers=headers)
    assert r.status_code == 200
    data = r.json().get('profile')
    assert 'mobile' in data
    assert 'first_name' in data


def test_profile_update(patient_token_and_mobile):
    token, _ = patient_token_and_mobile
    headers = {'Authorization': f'Bearer {token}'}
    payload = {
        'blood_group': 'O+',
        'email': 'test@example.com',
        'category': 'General',
        'father': 'Father Name',
        'mother': 'Mother Name',
        'address': 'Test Address'
    }
    # send as form-data
    r = requests.put(f'{BASE}/patients/profile-details-update', headers=headers, data=payload)
    assert r.status_code == 200
    profile = r.json().get('profile')
    assert profile['blood_group'] == 'O+'
    assert profile['email'] == 'test@example.com'


def test_events():
    r = requests.get(f'{BASE}/patients/events')
    assert r.status_code == 200
    data = r.json()
    assert 'events' in data
    assert isinstance(data['events'], list)


def test_report_upload_and_list(patient_token_and_mobile):
    token, _ = patient_token_and_mobile
    headers = {'Authorization': f'Bearer {token}'}

    # Upload a dummy file using BytesIO
    file_content = BytesIO(b'Test report content')
    files = {'file': ('report.txt', file_content)}
    r = requests.post(f'{BASE}/patients/report/upload', headers=headers, files=files)
    assert r.status_code == 201
    filename = r.json()['filename']

    # List uploaded reports
    r2 = requests.get(f'{BASE}/patients/report/list', headers=headers)
    assert r2.status_code == 200
    reports = r2.json().get('reports')
    assert any(rep['filename'] == filename for rep in reports)


def test_issue_submit(patient_token_and_mobile):
    token, _ = patient_token_and_mobile
    headers = {'Authorization': f'Bearer {token}'}
    payload = {'text': 'I have a headache'}
    # send text as form-data (no files)
    r = requests.post(f'{BASE}/patients/issue', headers=headers, data=payload)
    assert r.status_code == 201
    assert r.json()['message'] == 'Issue submitted'
