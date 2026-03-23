const token = localStorage.getItem('access_token');
if (!token) window.location.href = '/login';

// Initialize WebSocket connection
const socket = io();

socket.on('connect', () => {
    // Doctors join the global 'doctors' room for alerts
    socket.emit('join', { room: 'doctors' });
});

socket.on('emergency_broadcast', (data) => {
    // Play a sound or show a highly visible alert
    alert(`🚨 EMERGENCY TRIAGE ALERT 🚨\nSession ID: ${data.session_id || 'Unknown'}\nA patient has triggered the emergency protocol. Please refresh or check your pending reports immediately.`);
    // Automatically violently refresh the report lists
    loadReports();
});

async function loadReports() {
    try {
        const res = await fetch('/doctor/reports', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const reports = await res.json();
        const container = document.getElementById('reportsList');
        if (reports.length === 0) {
            container.innerHTML = '<div class="col-12"><div class="glass-card text-center p-5 text-muted"><i class="fas fa-check-circle fa-4x mb-3 text-success"></i><h4>All caught up!</h4><p>No pending reports to review.</p></div></div>';
            return;
        }
        container.innerHTML = reports.map(r => `
            <div class="col-md-6 mb-4">
                <div class="glass-card h-100">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <h5 class="mb-0 text-dark">Patient: ${r.patient_name}</h5>
                            <small class="text-muted">Report #${r.report_id}</small>
                        </div>
                        <span class="badge bg-${r.severity === 'Critical' ? 'danger' : r.severity === 'Moderate' ? 'warning text-dark' : 'success'} shadow-sm">${r.severity}</span>
                    </div>
                    <div class="mb-3">
                        <small class="d-block"><i class="fas fa-envelope me-2 text-primary"></i> <a href="mailto:${r.patient_email}" class="text-decoration-none">${r.patient_email}</a></small>
                        <small class="d-block"><i class="fas fa-phone me-2 text-primary"></i> <a href="tel:${r.patient_phone}" class="text-decoration-none">${r.patient_phone}</a></small>
                    </div>
                    <div class="bg-light p-3 rounded mb-3" style="max-height:100px; overflow-y:auto; border: 1px solid var(--glass-border);">
                        <strong>Symptoms:</strong><br>${r.symptoms}
                    </div>
                    ${r.image ? `<div class="mb-3 text-center"><img src="/static/uploads/${r.image}" alt="Patient attachment" class="img-fluid rounded" style="max-height:150px; border:1px solid #ddd;"></div>` : ''}
                    <button class="btn btn-primary w-100 mt-auto shadow-sm" onclick="openResponseModal(${r.report_id}, '${r.symptoms.replace(/'/g, "\\'")}')"><i class="fas fa-edit me-2"></i> Provide Diagnosis</button>
                </div>
            </div>
        `).join('');
    } catch(e) {
         document.getElementById('reportsList').innerHTML = '<div class="alert alert-danger mx-3">Error loading reports</div>';
     }
}

function openResponseModal(reportId, symptoms) {
    document.getElementById('currentReportId').value = reportId;
    document.getElementById('reportDetails').innerHTML = `<p class="mb-0"><strong>Patient Symptoms:</strong><br>${symptoms}</p>`;
    document.getElementById('doctorResponse').value = '';
    new bootstrap.Modal(document.getElementById('responseModal')).show();
}

async function submitResponse() {
    const reportId = document.getElementById('currentReportId').value;
    const response = document.getElementById('doctorResponse').value;
    if(!response.trim()) { alert('Please provide a diagnosis.'); return; }
    
    const btn = document.querySelector('#responseModal .btn-success');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Submitting...';
    btn.disabled = true;

    const res = await fetch(`/doctor/report/${reportId}`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ response })
    });
    if (res.ok) {
        bootstrap.Modal.getInstance(document.getElementById('responseModal')).hide();
        loadReports();
    } else {
        alert('Failed to submit response.');
    }
    btn.innerHTML = originalText;
    btn.disabled = false;
}

async function loadAppointments() {
    try {
        const res = await fetch('/doctor/appointments', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const apps = await res.json();
        const container = document.getElementById('appointmentsList');
        if (apps.length === 0) {
            container.innerHTML = '<div class="text-center p-4 text-muted"><p class="mb-0">No appointment requests.</p></div>';
            return;
        }
        container.innerHTML = apps.map(a => {
            const roomName = `MedAI-Apt-${a.appointment_id}`;
            return `
            <div class="list-group-item d-flex flex-column flex-md-row justify-content-between align-items-md-center py-3" style="background:transparent; border-color:var(--glass-border);">
                <div class="mb-2 mb-md-0">
                    <h6 class="fw-bold mb-1"><i class="fas fa-user ms-1 me-2 text-primary"></i>${a.patient_name}</h6>
                    <small class="text-muted d-block mb-1">
                        <a href="mailto:${a.patient_email}" class="text-decoration-none text-muted me-3"><i class="fas fa-envelope me-1"></i>${a.patient_email}</a>
                        <a href="tel:${a.patient_phone}" class="text-decoration-none text-muted"><i class="fas fa-phone me-1"></i>${a.patient_phone}</a>
                    </small>
                    <small class="text-muted"><i class="far fa-clock me-1 text-info"></i>${new Date(a.date).toLocaleString()}</small>
                    <span class="badge bg-${a.status === 'requested' ? 'warning text-dark' : a.status === 'confirmed' ? 'success' : 'secondary'} ms-2">${a.status}</span>
                </div>
                <div class="d-flex align-items-center gap-2">
                    ${a.status === 'confirmed' ? `<button class="btn btn-sm btn-success" onclick="window.open('/video_call?room=${roomName}','_blank')"><i class="fas fa-video me-1"></i>Video Call</button>` : ''}
                    <select class="form-select form-select-sm shadow-sm" style="width:auto;" id="status-select-${a.appointment_id}">
                        <option value="requested" ${a.status === 'requested' ? 'selected' : ''}>Requested</option>
                        <option value="confirmed" ${a.status === 'confirmed' ? 'selected' : ''}>Confirm</option>
                        <option value="cancelled" ${a.status === 'cancelled' ? 'selected' : ''}>Cancel</option>
                    </select>
                    <button class="btn btn-sm btn-outline-primary" onclick="updateAppointment(${a.appointment_id})">Update</button>
                </div>
            </div>
        `}).join('');
    } catch(e) {}
}

async function updateAppointment(appointmentId) {
    const status = document.getElementById(`status-select-${appointmentId}`).value;
    const res = await fetch(`/doctor/appointment/${appointmentId}`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status })
    });
    if (res.ok) {
        loadAppointments();
    } else {
        alert("Failed to update appointment");
    }
}

async function updateAvailability() {
    const available = document.getElementById('availabilitySwitch').checked;
    const res = await fetch('/doctor/availability', {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ available })
    });
    if (res.ok) {
        const badge = document.getElementById('availabilityBadge');
        if(available) {
             badge.className = "badge bg-success me-3 py-2 px-3 shadow-sm";
             badge.innerHTML = '<i class="fas fa-circle ms-1 me-1 text-white" style="font-size:8px; vertical-align:middle;"></i> Available';
        } else {
             badge.className = "badge bg-secondary me-3 py-2 px-3 shadow-sm";
             badge.innerHTML = '<i class="fas fa-circle ms-1 me-1 text-white" style="font-size:8px; vertical-align:middle;"></i> Unavailable';
        }
        alert('Availability updated successfully.');
    } else {
        alert('Update failed.');
    }
}

// Load initial data
loadReports();
loadAppointments();
loadFeedback();

async function loadFeedback() {
    try {
        const res = await fetch('/doctor/feedback', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        document.getElementById('avgRating').textContent = data.average_rating.toFixed(1);
        document.getElementById('totalReviewsText').textContent = `${data.total_reviews} review${data.total_reviews !== 1 ? 's' : ''}`;
        
        let starsHtml = '';
        for (let i = 1; i <= 5; i++) {
            if (i <= Math.floor(data.average_rating)) starsHtml += '<i class="fas fa-star"></i>';
            else if (i - data.average_rating < 1 && i - data.average_rating > 0) starsHtml += '<i class="fas fa-star-half-alt"></i>';
            else starsHtml += '<i class="far fa-star" style="opacity:0.4;"></i>';
        }
        document.getElementById('avgStars').innerHTML = starsHtml;
        
        const reviewsList = document.getElementById('reviewsList');
        if (data.reviews.length === 0) {
            reviewsList.innerHTML = '<div class="glass-card text-center p-4 text-muted"><i class="fas fa-comment-slash fa-3x mb-3" style="opacity:0.3;"></i><p>No reviews yet.</p></div>';
        } else {
            reviewsList.innerHTML = data.reviews.map(r => {
                let stars = '';
                for (let i = 1; i <= 5; i++) stars += `<i class="fas fa-star" style="color:${i <= r.rating ? '#f59e0b' : '#d1d5db'};font-size:0.85rem;"></i>`;
                return `
                <div class="glass-card mb-3">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div>
                            <strong>${r.patient_name}</strong>
                            <small class="text-muted ms-2">${r.date}</small>
                        </div>
                        <div>${stars}</div>
                    </div>
                    <p class="mb-0 text-muted" style="font-size:0.9rem;">${r.comment || '<em>No comment provided</em>'}</p>
                </div>
            `}).join('');
        }
    } catch(e) {
        console.error('Failed to load feedback:', e);
    }
}

function logout() {
    localStorage.clear();
    window.location.href = '/login';
}
