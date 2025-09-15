# Flask Backend (Patients, Doctor, OPD-Pharma)
## Overview
This project implements a Flask backend with JWT auth, CORS, MongoDB (pymongo), password hashing (werkzeug),
file uploads, and endpoints for the **patients** role. Placeholders/blueprints exist for `doctor` and `pharma` roles.

## Provided features (patients)
- POST /patients/register  -> Register with OTP (default 4444)
- POST /patients/verify-otp -> Verify OTP to activate account
- POST /patients/login -> Login (mobile + password) returns JWT
- GET  /patients/profile-details -> Get patient profile
- PUT  /patients/profile-details-update -> Update profile & upload profile image
- GET  /patients/events -> List events
- POST /patients/report/upload -> Upload report (image/pdf)
- GET  /patients/report/list -> List reports for user
- GET  /patients/report/download/<filename> -> Download/serve file
- POST /patients/issue -> Submit issue (text or audio). Dummy translate/audio-to-text utilities provided.

## Dev & Test
- `dummy_populate.py` to add test data
- `tests/test_patients_api.py` pytest tests (assumes server running at http://localhost:5000)

## How to run
1. Create venv: `python -m venv venv`
2. Activate it and install: `pip install -r requirements.txt`
3. Run: `python app.py`
4. (Optional) Run dummy populate: `python dummy_populate.py`
5. Run tests (server must be running): `pytest -q`

## Notes
- MongoDB URI is placed in `config.py` as provided.
- OTP is a simple check against '4444' for now.
