import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'supersecretkey')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-super-secret')
    MONGO_URI = os.environ.get(
        'MONGO_URI',
        'mongodb+srv://sahutijendra9_db_user:yTZWtc7S4QAE7oHS@cluster0.hhtzrtj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
    )
    # Set a default DB name to use (change 'sih_db' to your preferred DB name)
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'sih_db')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
