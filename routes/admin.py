from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
from models import db, Doctor, PatientReport, Patient, DoctorVerificationRequest

admin_bp = Blueprint('admin', __name__)

ALLOWED_SPECIALIZATIONS = [
    'Cardiologist', 'Neurologist', 'Dermatologist', 'Orthopedic',
    'General Physician', 'Pediatrician', 'ENT Specialist',
    'Gastroenterologist', 'Pulmonologist', 'Endocrinologist',
    'Psychiatrist', 'Ophthalmologist', 'Nephrologist', 'Urologist',
    'Gynecologist', 'Rheumatologist', 'Oncologist', 'Hematologist', 'Dentist'
]

@admin_bp.route('/doctors', methods=['GET'])
@jwt_required()
def get_doctors():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'msg': 'Unauthorized'}), 403
    doctors = Doctor.query.all()
    return jsonify([{
        'doctor_id': d.doctor_id,
        'name': d.name,
        'specialization': d.specialization,
        'email': d.email,
        'phone': d.phone,
        'available': d.available
    } for d in doctors]), 200

@admin_bp.route('/doctor', methods=['POST'])
@jwt_required()
def add_doctor():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'msg': 'Unauthorized'}), 403
    data = request.get_json()
    if data['specialization'] not in ALLOWED_SPECIALIZATIONS:
        return jsonify({'msg': 'Invalid specialization'}), 400
    if Doctor.query.filter_by(email=data['email']).first() or Doctor.query.filter_by(phone=data['phone']).first():
        return jsonify({'msg': 'Doctor with this email/phone already exists'}), 400
    doctor = Doctor(
        name=data['name'],
        age=data['age'],
        gender=data['gender'],
        education=data['education'],
        experience_years=data['experience_years'],
        specialization=data['specialization'],
        email=data['email'],
        phone=data['phone']
    )
    doctor.set_password(data['password'])  # default password, can be changed later
    db.session.add(doctor)
    db.session.commit()
    return jsonify({'msg': 'Doctor added successfully'}), 201

@admin_bp.route('/doctor/<int:doctor_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def manage_doctor(doctor_id):
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'msg': 'Unauthorized'}), 403
    doctor = Doctor.query.get_or_404(doctor_id)
    if request.method == 'DELETE':
        from models import DoctorFeedback, Appointment, ChatSession
        db.session.query(DoctorFeedback).filter_by(doctor_id=doctor_id).delete()
        db.session.query(Appointment).filter_by(doctor_id=doctor_id).delete()
        db.session.query(PatientReport).filter_by(assigned_doctor_id=doctor_id).update({'assigned_doctor_id': None})
        db.session.query(ChatSession).filter_by(assigned_doctor_id=doctor_id).update({'assigned_doctor_id': None})
        db.session.delete(doctor)
        db.session.commit()
        return jsonify({'msg': 'Doctor deleted'}), 200
    else:  # PUT
        data = request.get_json()
        if 'specialization' in data and data['specialization'] not in ALLOWED_SPECIALIZATIONS:
            return jsonify({'msg': 'Invalid specialization'}), 400
        for key, value in data.items():
            if hasattr(doctor, key) and key not in ['doctor_id', 'password_hash', 'created_at']:
                setattr(doctor, key, value)
        db.session.commit()
        return jsonify({'msg': 'Doctor updated'}), 200

@admin_bp.route('/reports', methods=['GET'])
@jwt_required()
def view_reports():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'msg': 'Unauthorized'}), 403
    reports = PatientReport.query.all()
    # Return reports with patient details etc.
    return jsonify([{
        'report_id': r.report_id,
        'patient_id': r.patient_id,
        'symptoms': r.symptoms_text,
        'severity': r.severity_level,
        'status': r.status
    } for r in reports]), 200

@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'msg': 'Unauthorized'}), 403
    total_patients = Patient.query.count()
    total_doctors = Doctor.query.count()
    total_reports = PatientReport.query.count()
    critical = PatientReport.query.filter_by(severity_level='Critical').count()
    moderate = PatientReport.query.filter_by(severity_level='Moderate').count()
    normal = PatientReport.query.filter_by(severity_level='Normal').count()
    pending = PatientReport.query.filter_by(status='pending').count()
    reviewed = PatientReport.query.filter_by(status='reviewed').count()
    return jsonify({
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_reports': total_reports,
        'severity': {'Critical': critical, 'Moderate': moderate, 'Normal': normal},
        'status': {'pending': pending, 'reviewed': reviewed}
    }), 200

@admin_bp.route('/patients', methods=['GET'])
@jwt_required()
def get_patients():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'msg': 'Unauthorized'}), 403
    patients = Patient.query.all()
    return jsonify([{
        'patient_id': p.patient_id,
        'name': p.name,
        'email': p.email,
        'phone': p.phone,
        'age': p.age,
        'gender': p.gender,
        'joined': p.created_at.strftime('%Y-%m-%d')
    } for p in patients]), 200

@admin_bp.route('/verification_requests', methods=['GET'])
@jwt_required()
def get_verification_requests():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'msg': 'Unauthorized'}), 403
    reqs = DoctorVerificationRequest.query.filter_by(status='pending').all()
    return jsonify([{
        'id': r.id,
        'name': r.name,
        'specialization': r.specialization,
        'email': r.email,
        'phone': r.phone,
        'education': r.education,
        'experience_years': r.experience_years,
        'online_treatment_fee': r.online_treatment_fee,
        'created_at': r.created_at.isoformat()
    } for r in reqs]), 200

@admin_bp.route('/approve_doctor/<int:req_id>', methods=['POST'])
@jwt_required()
def approve_doctor(req_id):
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'msg': 'Unauthorized'}), 403
    req = DoctorVerificationRequest.query.get_or_404(req_id)
    doc = Doctor(
        name=req.name,
        specialization=req.specialization,
        email=req.email,
        phone=req.phone,
        education=req.education,
        experience_years=req.experience_years
    )
    if req.password_hash:
        doc.password_hash = req.password_hash
    else:
        doc.set_password('password123') # fallback for old requests
        
    req.status = 'approved'
    db.session.add(doc)
    db.session.commit()
    return jsonify({'msg': 'Doctor approved and custom password applied.'}), 200

@admin_bp.route('/reject_doctor/<int:req_id>', methods=['DELETE'])
@jwt_required()
def reject_doctor(req_id):
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'msg': 'Unauthorized'}), 403
    req = DoctorVerificationRequest.query.get_or_404(req_id)
    req.status = 'rejected'
    db.session.commit()
    return jsonify({'msg': 'Rejected'}), 200