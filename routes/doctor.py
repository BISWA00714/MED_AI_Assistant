from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
from models import db, PatientReport, Doctor, Appointment
from datetime import datetime

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/reports', methods=['GET'])
@jwt_required()
def get_reports():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'doctor':
        return jsonify({'msg': 'Unauthorized'}), 403
    doctor_id = identity['id']
    reports = PatientReport.query.filter_by(assigned_doctor_id=doctor_id, status='pending').all()
    return jsonify([{
        'report_id': r.report_id,
        'patient_id': r.patient_id,
        'patient_name': r.patient.name,
        'patient_email': r.patient.email,
        'patient_phone': r.patient.phone,
        'symptoms': r.symptoms_text,
        'image': r.uploaded_image,
        'ai_report': r.ai_generated_report,
        'severity': r.severity_level
    } for r in reports]), 200

@doctor_bp.route('/report/<int:report_id>', methods=['POST'])
@jwt_required()
def respond_report(report_id):
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'doctor':
        return jsonify({'msg': 'Unauthorized'}), 403
    doctor_id = identity['id']
    report = PatientReport.query.filter_by(report_id=report_id, assigned_doctor_id=doctor_id).first_or_404()
    data = request.get_json()
    report.doctor_response = data.get('response')
    report.status = 'reviewed'
    db.session.commit()
    return jsonify({'msg': 'Response submitted'}), 200

@doctor_bp.route('/availability', methods=['PUT'])
@jwt_required()
def set_availability():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'doctor':
        return jsonify({'msg': 'Unauthorized'}), 403
    doctor_id = identity['id']
    data = request.get_json()
    doctor = Doctor.query.get(doctor_id)
    doctor.available = data.get('available', True)
    db.session.commit()
    return jsonify({'msg': 'Availability updated'}), 200

@doctor_bp.route('/appointments', methods=['GET'])
@jwt_required()
def view_appointments():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'doctor':
        return jsonify({'msg': 'Unauthorized'}), 403
    doctor_id = identity['id']
    appointments = Appointment.query.filter_by(doctor_id=doctor_id).all()
    return jsonify([{
        'appointment_id': a.appointment_id,
        'patient_name': a.patient.name,
        'patient_email': a.patient.email,
        'patient_phone': a.patient.phone,
        'date': a.appointment_date.isoformat(),
        'status': a.status
    } for a in appointments]), 200

@doctor_bp.route('/appointment/<int:appointment_id>', methods=['PUT'])
@jwt_required()
def update_appointment(appointment_id):
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'doctor':
        return jsonify({'msg': 'Unauthorized'}), 403
    doctor_id = identity['id']
    appointment = Appointment.query.filter_by(appointment_id=appointment_id, doctor_id=doctor_id).first_or_404()
    data = request.get_json()
    appointment.status = data.get('status', appointment.status)
    db.session.commit()
    return jsonify({'msg': 'Appointment updated'}), 200


@doctor_bp.route('/feedback', methods=['GET'])
@jwt_required()
def get_my_feedback():
    """Doctor views their own feedback/reviews from patients."""
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'doctor':
        return jsonify({'msg': 'Unauthorized'}), 403
    doctor_id = identity['id']

    from models import DoctorFeedback
    feedbacks = DoctorFeedback.query.filter_by(doctor_id=doctor_id).order_by(DoctorFeedback.created_at.desc()).all()
    
    # Calculate average
    avg = 0.0
    if feedbacks:
        avg = round(sum(f.rating for f in feedbacks) / len(feedbacks), 1)

    return jsonify({
        'average_rating': avg,
        'total_reviews': len(feedbacks),
        'reviews': [{
            'feedback_id': f.feedback_id,
            'rating': f.rating,
            'comment': f.comment,
            'patient_name': f.patient.name if f.patient else 'Anonymous',
            'date': f.created_at.strftime('%Y-%m-%d')
        } for f in feedbacks]
    }), 200