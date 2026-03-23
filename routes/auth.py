from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from models import db, Patient, Doctor, Admin, bcrypt, DoctorVerificationRequest
from datetime import timedelta
import json

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('identifier')  # email or phone
    password = data.get('password')
    role = data.get('role')  # 'patient', 'doctor', 'admin'

    user = None
    if role == 'patient':
        user = Patient.query.filter((Patient.email == identifier) | (Patient.phone == identifier)).first()
    elif role == 'doctor':
        user = Doctor.query.filter((Doctor.email == identifier) | (Doctor.phone == identifier)).first()
    elif role == 'admin':
        user = Admin.query.filter((Admin.email == identifier) | (Admin.phone == identifier)).first()

    if user and bcrypt.check_password_hash(user.password_hash, password):
        identity_str = json.dumps({'id': getattr(user, f'{role}_id'), 'role': role})
        access_token = create_access_token(identity=identity_str, expires_delta=timedelta(days=1))
        return jsonify(access_token=access_token, role=role), 200
    return jsonify({'msg': 'Invalid credentials'}), 401

@auth_bp.route('/register/patient', methods=['POST'])
def register_patient():
    data = request.get_json()
    # Validate required fields
    if Patient.query.filter_by(email=data['email']).first() or Patient.query.filter_by(phone=data['phone']).first():
        return jsonify({'msg': 'Email or phone already exists'}), 400
    patient = Patient(
        name=data['name'],
        age=data['age'],
        gender=data['gender'],
        email=data['email'],
        phone=data['phone']
    )
    patient.set_password(data['password'])
    db.session.add(patient)
    db.session.commit()
    return jsonify({'msg': 'Patient registered successfully'}), 201

@auth_bp.route('/register/admin', methods=['POST'])
def register_admin():
    data = request.get_json()
    if Admin.query.filter_by(email=data['email']).first() or Admin.query.filter_by(phone=data['phone']).first():
        return jsonify({'msg': 'Email or phone already exists'}), 400
    admin = Admin(
        name=data['name'],
        gender=data['gender'],
        email=data['email'],
        phone=data['phone']
    )
    admin.set_password(data['password'])
    db.session.add(admin)
    db.session.commit()
    return jsonify({'msg': 'Admin registered successfully'}), 201

@auth_bp.route('/request_doctor', methods=['POST'])
def request_doctor():
    data = request.get_json()
    if Doctor.query.filter((Doctor.email == data.get('email')) | (Doctor.phone == data.get('phone'))).first():
        return jsonify({'msg': 'Doctor with this email/phone already exists'}), 400
    if DoctorVerificationRequest.query.filter((DoctorVerificationRequest.email == data.get('email')) | (DoctorVerificationRequest.phone == data.get('phone'))).first():
        return jsonify({'msg': 'Verification request already submitted for this email/phone'}), 400
        
    req = DoctorVerificationRequest(
        name=data.get('name'),
        specialization=data.get('specialization'),
        email=data.get('email'),
        phone=data.get('phone'),
        education=data.get('education'),
        experience_years=int(data.get('experience_years', 0)),
        online_treatment_fee=int(data.get('online_treatment_fee', 0)),
        password_hash=bcrypt.generate_password_hash(data.get('password')).decode('utf-8') if data.get('password') else None
    )
    db.session.add(req)
    db.session.commit()
    return jsonify({'msg': 'Verification request submitted successfully. Our team will review it shortly.'}), 201