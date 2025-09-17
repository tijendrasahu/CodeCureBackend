import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from pymongo import MongoClient

# Blueprints
from blueprints.patients import patients_bp
from blueprints.doctor import doctors_bp
from blueprints.pharma import pharma_bp

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
jwt = JWTManager(app)

# Ensure upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Mongo client accessible via app
client = MongoClient(app.config['MONGO_URI'])
# Explicitly pick DB name from config instead of get_database()
app.db = client[Config.MONGO_DB_NAME]

# Register blueprints
app.register_blueprint(patients_bp, url_prefix='/patients')
app.register_blueprint(doctors_bp, url_prefix='/doctors')
app.register_blueprint(pharma_bp, url_prefix='/pharma')

@app.route('/ping')
def ping():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
