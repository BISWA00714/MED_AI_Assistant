const token = localStorage.getItem('access_token');
if (!token) window.location.href = '/login';

function setActive(elem) {
    document.querySelectorAll('.list-group-item').forEach(el => el.classList.remove('active'));
    elem.classList.add('active');
}

async function loadPage(page) {
    const content = document.getElementById('content');
    if (page === 'submit_report') {
        content.innerHTML = `
            <h3 class="mb-4 text-primary"><i class="fas fa-stethoscope me-2"></i> Submit Symptoms</h3>
            <form id="reportForm" enctype="multipart/form-data">
                <div class="mb-4">
                    <label class="form-label text-muted fw-bold">Describe your symptoms in detail</label>
                    <textarea class="form-control shadow-sm" name="symptoms" rows="5" placeholder="e.g. I have been experiencing a mild headache for 2 days..." required></textarea>
                </div>
                <div class="mb-4">
                    <label class="form-label text-muted fw-bold">Upload Image (optional, max 5MB)</label>
                    <input type="file" class="form-control shadow-sm" name="image" accept="image/*">
                </div>
                <div class="mb-4">
                    <label class="form-label text-muted fw-bold">Preferred Language for Report</label>
                    <select class="form-select form-control shadow-sm" name="language">
                        <option value="English">English</option>
                        <option value="Hindi">Hindi</option>
                        <option value="Telugu">Telugu</option>
                        <option value="Marathi">Marathi</option>
                        <option value="Odia">Odia</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-primary px-4 py-2 w-100">Submit for AI Triage <i class="fas fa-paper-plane ms-2"></i></button>
            </form>
        `;
        document.getElementById('reportForm').addEventListener('submit', submitReport);
    } else if (page === 'history') {
        loadHistory();
    } else if (page === 'appointments') {
        loadAppointments();
    } else if (page === 'chat') {
        content.innerHTML = `
            <h3 class="mb-4 text-primary"><i class="fas fa-robot me-2"></i> General AI Chat Assistant</h3>
            <div id="chatMessages" class="bg-light shadow-sm rounded p-3 mb-3" style="height:350px; overflow-y:auto; border: 1px solid var(--glass-border);">
                <div class="text-center text-muted mt-5"><i class="fas fa-comment-dots fa-3x mb-2"></i><br>Ask me a general health question!</div>
            </div>
            <div class="d-flex gap-2">
                <input type="text" id="chatInput" class="form-control shadow-sm" placeholder="Ask a question..." onkeypress="if(event.key === 'Enter') sendChat()">
                <button class="btn btn-primary px-4 shadow-sm" onclick="sendChat()"><i class="fas fa-paper-plane"></i></button>
            </div>
        `;
    }
}

async function submitReport(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Processing with AI...';
    btn.disabled = true;

    const formData = new FormData(e.target);
    try {
        const res = await fetch('/patient/submit_report', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        const result = await res.json();
        if (res.ok) {
            alert('Submission Successful! Please refer to the result page or history.');
            // Optionally, redirect to a report detail page if implemented
        } else {
            alert('Error: ' + result.msg);
        }
    } catch (err) {
        alert('An error occurred.');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function loadHistory() {
    document.getElementById('content').innerHTML = '<div class="text-center my-5"><i class="fas fa-spinner fa-spin fa-3x text-primary"></i></div>';
    try {
        const res = await fetch('/patient/history', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if(!res.ok) throw new Error("Failed to load");
        const reports = await res.json();
        let html = '<h3 class="mb-4 text-primary"><i class="fas fa-history me-2"></i> Medical History</h3>';
        if(reports.length === 0) {
            html += '<p class="text-muted">No reports found.</p>';
        } else {
            html += '<div class="row">';
            reports.forEach(r => {
                html += `
                <div class="col-12 mb-3">
                    <div class="p-3 border rounded bg-white shadow-sm d-flex justify-content-between align-items-center flex-wrap">
                        <div>
                            <h5 class="mb-1 text-dark">Severity: <span class="badge bg-${r.severity === 'Critical' ? 'danger' : r.severity === 'Moderate' ? 'warning text-dark' : 'success'}">${r.severity}</span></h5>
                            <p class="text-muted mb-1 small">${new Date(r.date).toLocaleString()}</p>
                            <p class="mb-0 text-truncate" style="max-width:400px;">${r.symptoms}</p>
                        </div>
                        <div class="mt-2 mt-md-0">
                            <span class="badge bg-${r.status === 'Completed' ? 'success' : 'secondary'} me-2">${r.status}</span>
                            <button onclick="downloadPDF(${r.report_id})" class="btn btn-sm btn-outline-primary"><i class="fas fa-download me-1"></i> PDF</button>
                        </div>
                    </div>
                </div>`;
            });
            html += '</div>';
        }
        document.getElementById('content').innerHTML = html;
    } catch (err) {
        document.getElementById('content').innerHTML = '<p class="text-danger">Failed to load history.</p>';
    }
}

async function loadAppointments() {
    document.getElementById('content').innerHTML = '<div class="text-center my-5"><i class="fas fa-spinner fa-spin fa-3x text-primary"></i></div>';
    try {
        const res = await fetch('/patient/appointments', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if(!res.ok) throw new Error("Failed");
        const apps = await res.json();
        let html = '<h3 class="mb-4 text-primary"><i class="fas fa-calendar-check me-2"></i> Appointments</h3>';
        if(apps.length === 0) {
            html += '<p class="text-muted">No appointments scheduled.</p>';
        } else {
            html += '<ul class="list-group shadow-sm mb-4">';
            apps.forEach(a => {
                html += `<li class="list-group-item d-flex justify-content-between align-items-center p-3">
                    <div>
                        <h6 class="mb-0">Dr. ${a.doctor_name}</h6>
                        <small class="text-muted">${new Date(a.date).toLocaleString()}</small>
                    </div>
                    <span class="badge bg-primary rounded-pill px-3 py-2">${a.status}</span>
                </li>`;
            });
            html += '</ul>';
        }
        html += '<button class="btn btn-primary px-4 shadow-sm" onclick="showBookAppointment()"><i class="fas fa-plus me-2"></i> Book New Appointment</button>';
        document.getElementById('content').innerHTML = html;
    } catch (err) {
        document.getElementById('content').innerHTML = '<p class="text-danger">Failed to load appointments.</p>';
    }
}

function showBookAppointment() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <h3 class="mb-4 text-primary"><i class="fas fa-calendar-plus me-2"></i> Book Appointment</h3>
        <p class="text-muted">Select a doctor and time. (Demo UI implementation)</p>
        <button class="btn btn-outline-secondary mt-3" onclick="loadPage('appointments')"><i class="fas fa-arrow-left me-2"></i> Back</button>
    `;
}

async function sendChat() {
    const input = document.getElementById('chatInput');
    const query = input.value.trim();
    if(!query) return;
    
    const chatDiv = document.getElementById('chatMessages');
    if(chatDiv.innerHTML.includes('Ask me a general')) chatDiv.innerHTML = '';

    chatDiv.innerHTML += `
        <div class="d-flex justify-content-end mb-3">
            <div class="bg-primary text-white rounded p-3 shadow-sm" style="max-width:75%; border-bottom-right-radius:0;">
                ${query}
            </div>
        </div>`;
    
    input.value = '';
    chatDiv.scrollTop = chatDiv.scrollHeight;

    try {
        const res = await fetch('/patient/chat', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await res.json();
        
        chatDiv.innerHTML += `
            <div class="d-flex justify-content-start mb-3 fade-in">
                <div class="bg-white text-dark rounded border p-3 shadow-sm" style="max-width:75%; border-bottom-left-radius:0;">
                    <strong>MedAI:</strong><br>${data.response}
                </div>
            </div>`;
        chatDiv.scrollTop = chatDiv.scrollHeight;
    } catch (err) {
        chatDiv.innerHTML += `<div class="text-danger text-center small my-2">Failed to get response</div>`;
    }
}

function logout() {
    localStorage.clear();
    window.location.href = '/login';
}

async function downloadPDF(reportId) {
    try {
        const res = await fetch(`/patient/download_report/${reportId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Failed to download");
        
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `report_${reportId}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (err) {
        alert("Error downloading PDF");
    }
}

// Initialize empty content
loadPage('');
