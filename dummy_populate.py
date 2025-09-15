from pymongo import MongoClient
from config import Config
import datetime
import os
import uuid
import random

# This is a placeholder for your actual password hashing function.
# In a real scenario, you would import this from your utils.auth file.
def hash_password_placeholder(password):
    return f"hashed_{password}"

client = MongoClient(Config.MONGO_URI)
db = client[Config.MONGO_DB_NAME]

print("Clearing old dummy data...")
# Clear all relevant collections for a clean slate
db.patients.delete_many({})
db.events.delete_many({})
db.reports.delete_many({})
db.issues.delete_many({})

# --- Data for Punjabi Names and Addresses ---
punjabi_male_names = ["Jaspreet", "Gurpreet", "Manpreet", "Harpreet", "Sukhdeep", "Navdeep"]
punjabi_female_names = ["Jasleen", "Kirandeep", "Simran", "Navjot", "Gurleen", "Priya"]
punjabi_addresses = [
    {"city": "Amritsar", "address": "25, Lawrence Road, Amritsar, Punjab - 143001"},
    {"city": "Ludhiana", "address": "112, Sarabha Nagar, Ludhiana, Punjab - 141001"},
    {"city": "Jalandhar", "address": "45, Model Town, Jalandhar, Punjab - 144003"},
    {"city": "Patiala", "address": "7, Leela Bhawan, Patiala, Punjab - 147001"},
    {"city": "Mohali", "address": "House No. 345, Phase 7, Mohali, Punjab - 160061"}
]

# ---------------------------
# 1. CREATE DUMMY PATIENTS
# ---------------------------
# We create two patients for better data diversity.
# Patient 1: Male
male_name = random.choice(punjabi_male_names)
male_address = random.choice(punjabi_addresses)
patient_1_id = os.urandom(8).hex()
patient_1_mobile = "9876543210"

db.patients.insert_one({
    'first_name': male_name,
    'last_name': 'Singh',
    'age': 35,
    'dob': '1990-07-15',
    'sex': 'M',
    'mobile': patient_1_mobile,
    'password_hash': hash_password_placeholder('pass123'),
    'created_at': datetime.datetime.utcnow(),
    'profile': {
        'blood_group': 'O+',
        'email': f'{male_name.lower()}.singh@example.com',
        'category': 'General',
        'father': 'Balwinder Singh',
        'mother': 'Harjeet Kaur',
        'address': male_address['address']
    },
    'unique_id': patient_1_id
})
print(f"Created dummy patient: {male_name} Singh with user_id: {patient_1_id}")

# Patient 2: Female
female_name = random.choice(punjabi_female_names)
female_address = random.choice(punjabi_addresses)
patient_2_id = os.urandom(8).hex()
patient_2_mobile = "9876543211"

db.patients.insert_one({
    'first_name': female_name,
    'last_name': 'Kaur',
    'age': 28,
    'dob': '1997-02-20',
    'sex': 'F',
    'mobile': patient_2_mobile,
    'password_hash': hash_password_placeholder('pass456'),
    'created_at': datetime.datetime.utcnow(),
    'profile': {
        'blood_group': 'B+',
        'email': f'{female_name.lower()}.kaur@example.com',
        'category': 'OBC',
        'father': 'Sukhdev Singh',
        'mother': 'Manjit Kaur',
        'address': female_address['address']
    },
    'unique_id': patient_2_id
})
print(f"Created dummy patient: {female_name} Kaur with user_id: {patient_2_id}")


# ---------------------------
# 2. DUMMY EVENTS
# ---------------------------
events = [
    {"title": "Free Health Camp", "date": "2025-09-22", "location": random.choice(punjabi_addresses)['city'], "description": "Complete health checkup by certified doctors."},
    {"title": "Eye Checkup Drive", "date": "2025-10-05", "location": random.choice(punjabi_addresses)['city'], "description": "Free eye examinations and spectacle distribution."},
    {"title": "Blood Donation Camp", "date": "2025-10-18", "location": random.choice(punjabi_addresses)['city'], "description": "Donate blood and save a life. Refreshments will be provided."},
]
db.events.insert_many(events)

# ---------------------------
# 3. DUMMY REPORTS
# ---------------------------
reports = [
    {
        'user_id': patient_1_id,
        'mobile': patient_1_mobile,
        'filename': f'{uuid.uuid4().hex}.pdf',
        'original_name': 'blood_test_report.pdf',
        'uploaded_at': datetime.datetime.utcnow()
    },
    {
        'user_id': patient_2_id,
        'mobile': patient_2_mobile,
        'filename': f'{uuid.uuid4().hex}.png',
        'original_name': 'chest_xray.png',
        'uploaded_at': datetime.datetime.utcnow()
    },
]
db.reports.insert_many(reports)

# ---------------------------
# 4. DUMMY ISSUES
# ---------------------------
issues = [
    # A text-based issue in Punjabi from Patient 2
    {
        'user_id': patient_2_id,
        'mobile': patient_2_mobile,
        'created_at': datetime.datetime.utcnow(),
        'text': "ਮੈਨੂੰ ਖੰਘ ਅਤੇ ਛਾਤੀ ਵਿੱਚ ਦਰਦ ਹੈ।", # "I have a cough and chest pain."
        'translated': "[translated to en] I have a cough and chest pain."
    },
    # An audio-based issue from Patient 1
    {
        'user_id': patient_1_id,
        'mobile': patient_1_mobile,
        'created_at': datetime.datetime.utcnow(),
        'audio_filename': 'dummy_fever_audio.wav',
        'audio_transcript': "[transcribed audio text] For two days, I have had a high fever and body aches."
    },
]
db.issues.insert_many(issues)

print("✅ Dummy patient data with Punjabi names/addresses inserted into", Config.MONGO_DB_NAME)

