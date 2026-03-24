from flask import Flask, jsonify, request, render_template, send_file
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from config import Config
from models import db, bcrypt, Patient, Doctor, Admin, PatientReport, Appointment, DoctorFeedback
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.patient import patient_bp
from routes.doctor import doctor_bp
from sockets import socketio

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)
CORS(app)
socketio.init_app(app)

# 🔥 IMPORTANT FIX: Create tables on app startup (WORKS ON RAILWAY)
with app.app_context():
    db.create_all()

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(patient_bp, url_prefix='/patient')
app.register_blueprint(doctor_bp, url_prefix='/doctor')

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register/patient')
def register_patient_page():
    return render_template('register_patient.html')

@app.route('/register/admin')
def register_admin_page():
    return render_template('register_admin.html')

@app.route('/register_doctor.html')
def register_doctor_page():
    return render_template('register_doctor.html')

@app.route('/patient_dashboard.html')
def patient_dashboard():
    return render_template('patient_dashboard.html')

@app.route('/doctor_dashboard.html')
def doctor_dashboard():
    return render_template('doctor_dashboard.html')

@app.route('/admin_dashboard.html')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/request_verification.html')
def request_verification_page():
    return render_template('request_verification.html')

@app.route('/video_call')
def video_call_page():
    return render_template('video_call.html')

@app.route('/appointment.html')
def appointment_page():
    return render_template('appointment.html')

@app.route('/find_doctors.html')
def find_doctors_page():
    return render_template('find_doctors.html')


# 🚀 Run server (for local only, Railway uses gunicorn)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)