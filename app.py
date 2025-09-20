import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

# .env file se saari keys (jaise OPENAI_API_KEY, AGORA_APP_ID) ko load karta hai
load_dotenv()

# --- BLUEPRINTS ---
# Saare blueprints ko import karein
from blueprints.patients import patients_bp
from blueprints.doctor import doctors_bp
from blueprints.pharma import pharma_bp
from blueprints.video import video_bp

def create_app():
    """App factory to create and configure the Flask app."""
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object('config.Config')
    CORS(app, resources={r"/*": {"origins": "*"}})
    jwt = JWTManager(app)

    # Ensure the upload folder exists
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Database connection with SSL fix
    client = MongoClient(app.config['MONGO_URI'], tlsCAFile=certifi.where())
    app.db = client[app.config['MONGO_DB_NAME']]

    # --- BLUEPRINTS KO REGISTER KAREIN ---
    app.register_blueprint(patients_bp, url_prefix='/patients')
    app.register_blueprint(doctors_bp, url_prefix='/doctors')
    app.register_blueprint(pharma_bp, url_prefix='/pharma')
    app.register_blueprint(video_bp, url_prefix='/video')

    # Central file server for all uploaded content
    @app.route('/uploads/<path:filename>')
    def serve_central_uploads(filename):
        uploads_dir = os.path.join(app.root_path, upload_folder)
        return send_from_directory(uploads_dir, filename)

    @app.route('/ping')
    def ping():
        return jsonify({'status': 'ok'})

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

