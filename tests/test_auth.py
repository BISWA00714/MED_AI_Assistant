import json

def test_patient_registration(client):
    """Test successful patient registration and login."""
    # 1. Register Patient
    response = client.post('/auth/register/patient', json={
        'name': 'Test Patient',
        'age': 30,
        'gender': 'Male',
        'email': 'patient@test.com',
        'phone': '1234567890',
        'password': 'password123'
    })
    assert response.status_code == 201
    assert b'Patient registered successfully' in response.data

    # 2. Prevent Duplicate Registration
    response2 = client.post('/auth/register/patient', json={
        'name': 'Test Duplicate',
        'age': 25,
        'gender': 'Female',
        'email': 'patient@test.com',
        'phone': '1234567890',
        'password': 'password123'
    })
    assert response2.status_code == 400

    # 3. Secure Patient Login
    login_response = client.post('/auth/login', json={
        'role': 'patient',
        'identifier': 'patient@test.com',
        'password': 'password123'
    })
    assert login_response.status_code == 200
    data = json.loads(login_response.data)
    assert 'access_token' in data
    assert data['role'] == 'patient'

def test_admin_registration(client):
    """Test successful admin registration and bad login paths."""
    # 1. Register Admin
    response = client.post('/auth/register/admin', json={
        'name': 'Test Admin',
        'gender': 'Female',
        'email': 'admin@test.com',
        'phone': '9876543210',
        'password': 'secureadmin123'
    })
    assert response.status_code == 201

    # 2. Login Failure (Wrong password)
    fail_login = client.post('/auth/login', json={
        'role': 'admin',
        'identifier': 'admin@test.com',
        'password': 'wrongpassword'
    })
    assert fail_login.status_code == 401
    assert b'Invalid credentials' in fail_login.data

def test_doctor_verification_request(client):
    """Test the doctor verification request pipeline mapping correctly."""
    response = client.post('/auth/request_doctor', json={
        'name': 'Dr. Test Provider',
        'specialization': 'Cardiologist',
        'email': 'doctor@medical.com',
        'phone': '5556667777',
        'education': 'MD, Board Certified',
        'experience_years': 10,
        'online_treatment_fee': 150,
        'password': 'DocPassword!23'
    })
    assert response.status_code == 201
    assert b'Verification request submitted successfully' in response.data
