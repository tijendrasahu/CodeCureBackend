from flask import Blueprint, jsonify
doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/login', methods=['POST'])
def login():
    return jsonify({'message':'Doctor login placeholder'}), 200
