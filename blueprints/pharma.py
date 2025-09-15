from flask import Blueprint, jsonify
pharma_bp = Blueprint('pharma', __name__)

@pharma_bp.route('/login', methods=['POST'])
def login():
    return jsonify({'message':'Pharma login placeholder'}), 200
