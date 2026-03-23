from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from models import db, PatientReport, Appointment, Doctor, ChatSession, DoctorFeedback
from agents import process_patient_input, agent_triage_chat, generate_report_from_chat, get_greeting
from sockets import socketio

patient_bp = Blueprint('patient', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@patient_bp.route('/submit_report', methods=['POST'])
@jwt_required()
def submit_report():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'patient':
        return jsonify({'msg': 'Unauthorized'}), 403
    patient_id = identity['id']
    
    symptoms = request.form.get('symptoms')
    language = request.form.get('language', 'English')
    image_file = request.files.get('image')
    
    if not symptoms:
        return jsonify({'msg': 'Symptoms text required'}), 400
    
    # Save image if provided
    image_filename = None
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        image_filename = f"patient_{patient_id}_{datetime.utcnow().timestamp()}_{filename}"
        image_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], image_filename))
    
    # Run AI agents
    result = process_patient_input(patient_id, symptoms, image_filename, language)
    
    # Save report to database (agents.py will create report entry)
    # For now, assume agents.py returns a dict and we save
    
    report = PatientReport(
        patient_id=patient_id,
        symptoms_text=symptoms,
        uploaded_image=image_filename,
        ai_generated_report=result.get('ai_report'),
        severity_level=result.get('severity'),
        assigned_doctor_id=result.get('assigned_doctor_id'),
        status='pending' if result.get('severity') in ['Moderate', 'Critical'] else 'reviewed'  # AI doctor handled
    )
    db.session.add(report)
    db.session.commit()
    
    # If AI doctor handled, we can store its response directly in doctor_response? Or create a separate field?
    if result.get('severity') == 'Normal':
        # AI doctor generated advice; we can store it as doctor_response
        report.doctor_response = result.get('ai_advice')
        db.session.commit()
    
    return jsonify({
        'report_id': report.report_id,
        'severity': result.get('severity'),
        'message': 'Report submitted successfully',
        'result': result.get('final_output')  # simplified and translated
    }), 201

@patient_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'patient':
        return jsonify({'msg': 'Unauthorized'}), 403
    patient_id = identity['id']
    reports = PatientReport.query.filter_by(patient_id=patient_id).order_by(PatientReport.created_at.desc()).all()
    return jsonify([{
        'report_id': r.report_id,
        'date': r.created_at.strftime('%Y-%m-%d %H:%M'),
        'symptoms': r.symptoms_text,
        'severity': r.severity_level,
        'doctor_response': r.doctor_response,
        'status': r.status
    } for r in reports]), 200

@patient_bp.route('/download_report/<int:report_id>', methods=['GET'])
@jwt_required()
def download_report(report_id):
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'patient':
        return jsonify({'msg': 'Unauthorized'}), 403
    patient_id = identity['id']
    report = PatientReport.query.filter_by(report_id=report_id, patient_id=patient_id).first_or_404()
    # Generate PDF using utils.py
    from utils import generate_pdf_report
    pdf_path = generate_pdf_report(report)
    return send_file(pdf_path, as_attachment=True, download_name=f"report_{report_id}.pdf")

@patient_bp.route('/appointments', methods=['GET', 'POST'])
@jwt_required()
def appointments():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'patient':
        return jsonify({'msg': 'Unauthorized'}), 403
    patient_id = identity['id']
    if request.method == 'POST':
        data = request.get_json()
        doctor_id = data['doctor_id']
        appointment_date = datetime.fromisoformat(data['appointment_date'])
        # Check doctor availability
        doctor = Doctor.query.get(doctor_id)
        if not doctor or not doctor.available:
            return jsonify({'msg': 'Doctor not available'}), 400
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=appointment_date
        )
        db.session.add(appointment)
        db.session.commit()
        return jsonify({'msg': 'Appointment requested'}), 201
    else:
        # GET: list patient's appointments
        apps = Appointment.query.filter_by(patient_id=patient_id).all()
        return jsonify([{
            'appointment_id': a.appointment_id,
            'doctor_name': a.doctor.name,
            'date': a.appointment_date.isoformat(),
            'status': a.status
        } for a in apps]), 200

@patient_bp.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    # Simple AI chat assistant (mock)
    data = request.get_json()
    query = data.get('query')
    # In reality, you might call an LLM or rule-based system
    response = f"AI Assistant: Regarding '{query}', please consult a doctor for accurate advice."
    return jsonify({'response': response}), 200

@patient_bp.route('/doctors', methods=['GET'])
@jwt_required()
def get_available_doctors():
    # Only patients can access
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'patient':
        return jsonify({'msg': 'Unauthorized'}), 403
    doctors = Doctor.query.filter_by(available=True).all()
    return jsonify([{
        'doctor_id': d.doctor_id,
        'name': d.name,
        'specialization': d.specialization,
        'education': d.education or '',
        'experience_years': d.experience_years or 0,
        'email': d.email or '',
        'phone': d.phone or '',
        'average_rating': d.average_rating,
        'total_reviews': len(d.feedbacks)
    } for d in doctors]), 200


# ─────────────────────────────────────────────────────────────
#  TRIAGE CHAT ENDPOINTS
# ─────────────────────────────────────────────────────────────

@patient_bp.route('/triage/start', methods=['POST'])
@jwt_required()
def triage_start():
    """Start a new triage chat session; returns session_id + AI greeting."""
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'patient':
        return jsonify({'msg': 'Unauthorized'}), 403
    patient_id = identity['id']
    data = request.get_json()
    language = data.get('language', 'English')

    # Close any previous active session for this patient
    old = ChatSession.query.filter_by(patient_id=patient_id, status='active').all()
    for s in old:
        s.status = 'completed'
    db.session.commit()

    greeting = get_greeting(language)
    session = ChatSession(
        patient_id=patient_id,
        language=language,
        history=json.dumps([{"role": "assistant", "content": greeting}])
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        'session_id': session.session_id,
        'message': greeting,
        'language': language
    }), 201


@patient_bp.route('/triage/message', methods=['POST'])
@jwt_required()
def triage_message():
    """Send a patient message; get AI reply. Returns is_complete=True when done."""
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'patient':
        return jsonify({'msg': 'Unauthorized'}), 403

    data = request.get_json()
    session_id = data.get('session_id')
    user_message = data.get('message', '').strip()
    image_b64 = data.get('image')

    if not user_message and not image_b64:
        return jsonify({'msg': 'Message or Image cannot be empty'}), 400

    session = ChatSession.query.filter_by(
        session_id=session_id, patient_id=json.loads(get_jwt_identity())['id']
    ).first_or_404()

    if session.status != 'active':
        return jsonify({'msg': 'Session already completed'}), 400

    history = json.loads(session.history)

    ai_reply, is_complete = agent_triage_chat(history, user_message, session.language, image_b64)

    # Append both turns to history
    user_content_str = user_message
    if image_b64:
        user_content_str = f"[Patient uploaded an image] {user_message}"
        
    history.append({"role": "user", "content": user_content_str})
    history.append({"role": "assistant", "content": ai_reply})
    session.history = json.dumps(history)

    if is_complete:
        session.status = 'completed'

    db.session.commit()

    return jsonify({
        'message': ai_reply,
        'is_complete': is_complete,
        'session_id': session_id
    }), 200


@patient_bp.route('/triage/finalize', methods=['POST'])
@jwt_required()
def triage_finalize():
    """Generate the full medical report from the completed chat session."""
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'patient':
        return jsonify({'msg': 'Unauthorized'}), 403
    patient_id = identity['id']

    data = request.get_json()
    session_id = data.get('session_id')

    session = ChatSession.query.filter_by(
        session_id=session_id, patient_id=patient_id
    ).first_or_404()

    history = json.loads(session.history)

    # Generate the full report using the chat history
    result = generate_report_from_chat(history, session.language)

    # Save to PatientReport
    report = PatientReport(
        patient_id=patient_id,
        symptoms_text=" | ".join(m['content'] for m in history if m['role'] == 'user'),
        ai_generated_report=result.get('ai_report'),
        severity_level=result.get('severity'),
        assigned_doctor_id=result.get('assigned_doctor_id'),
        status='pending' if result.get('severity') in ['Moderate', 'Critical'] else 'reviewed'
    )
    if result.get('severity') == 'Normal':
        report.doctor_response = result.get('ai_advice')
    db.session.add(report)

    # Update session with result
    session.severity = result.get('severity')
    session.assigned_doctor_id = result.get('assigned_doctor_id')
    db.session.commit()

    # Build doctor contact info for severe cases
    doctor_info = None
    if result.get('assigned_doctor_id'):
        doc = Doctor.query.get(result['assigned_doctor_id'])
        if doc:
            # Jitsi Meet link — unique per report, no signup needed
            room_name = f"MedAI-{patient_id}-{report.report_id}"
            doctor_info = {
                'doctor_id': doc.doctor_id,
                'name': doc.name,
                'specialization': doc.specialization,
                'email': doc.email,
                'phone': doc.phone,
                'video_url': f"https://meet.jit.si/{room_name}",
                'room_name': room_name
            }

    return jsonify({
        'report_id': report.report_id,
        'severity': result.get('severity'),
        'ai_report': result.get('ai_report'),
        'ai_advice': result.get('ai_advice'),
        'final_output': result.get('final_output'),
        'audio_file': result.get('audio_file'),
        'doctor': doctor_info
    }), 201

@patient_bp.route('/triage/emergency', methods=['POST'])
@jwt_required()
def triage_emergency():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'patient':
        return jsonify({'msg': 'Unauthorized'}), 403
    patient_id = identity['id']
    data = request.get_json()
    session_id = data.get('session_id')
    
    session = ChatSession.query.filter_by(session_id=session_id, patient_id=patient_id).first_or_404()
    session.status = 'completed'
    session.severity = 'Critical'
    
    doctor = Doctor.query.filter_by(specialization='General Physician', available=True).first()
    if not doctor:
        doctor = Doctor.query.filter_by(available=True).first()
        
    doctor_info = None
    if doctor:
        session.assigned_doctor_id = doctor.doctor_id
        room_name = f"MedAI-EMERGENCY-{patient_id}"
        doctor_info = {
            'doctor_id': doctor.doctor_id,
            'name': doctor.name,
            'specialization': doctor.specialization,
            'email': doctor.email,
            'phone': doctor.phone,
            'video_url': f"https://meet.jit.si/{room_name}",
            'room_name': room_name
        }
        
        
    db.session.commit()
    
    # Broadcast the emergency to all connected doctors instantly
    try:
        socketio.emit('emergency_broadcast', {
            'session_id': session_id,
            'patient_id': patient_id,
            'patient_name': identity.get('name', 'Unknown'),
            'symptoms': "Patient triggered the Emergency Protocol button from their triage chat!"
        }, room='doctors')
    except Exception as e:
        print(f"WebSocket emit failed: {e}")
        
    return jsonify({
        'severity': 'Critical',
        'doctor': doctor_info
    }), 200


# ─────────────────────────────────────────────────────────────
#  FEEDBACK ENDPOINTS
# ─────────────────────────────────────────────────────────────

@patient_bp.route('/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    """Patient submits a rating + comment for a doctor after a consultation."""
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'patient':
        return jsonify({'msg': 'Unauthorized'}), 403
    patient_id = identity['id']

    data = request.get_json()
    doctor_id = data.get('doctor_id')
    rating = data.get('rating')
    comment = data.get('comment', '')
    appointment_id = data.get('appointment_id')

    if not doctor_id or not rating:
        return jsonify({'msg': 'doctor_id and rating are required'}), 400
    if not (1 <= int(rating) <= 5):
        return jsonify({'msg': 'Rating must be between 1 and 5'}), 400

    if appointment_id:
        existing = DoctorFeedback.query.filter_by(
            patient_id=patient_id, appointment_id=appointment_id
        ).first()
        if existing:
            return jsonify({'msg': 'You have already reviewed this appointment'}), 400

    feedback = DoctorFeedback(
        doctor_id=doctor_id,
        patient_id=patient_id,
        appointment_id=appointment_id,
        rating=int(rating),
        comment=comment
    )
    db.session.add(feedback)
    db.session.commit()
    return jsonify({'msg': 'Feedback submitted successfully'}), 201


@patient_bp.route('/doctor/<int:doctor_id>/feedback', methods=['GET'])
@jwt_required()
def get_doctor_feedback(doctor_id):
    """Get all feedback for a specific doctor."""
    feedbacks = DoctorFeedback.query.filter_by(doctor_id=doctor_id).order_by(DoctorFeedback.created_at.desc()).all()
    return jsonify([{
        'feedback_id': f.feedback_id,
        'rating': f.rating,
        'comment': f.comment,
        'patient_name': f.patient.name if f.patient else 'Anonymous',
        'date': f.created_at.strftime('%Y-%m-%d')
    } for f in feedbacks]), 200
