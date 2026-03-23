const token = localStorage.getItem('access_token');
if (!token) window.location.href = '/login';

async function loadDoctors() {
    try {
        const res = await fetch('/admin/doctors', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const doctors = await res.json();
        const tbody = document.getElementById('doctorTableBody');
        if(doctors.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No doctors registered.</td></tr>';
            return;
        }
        tbody.innerHTML = doctors.map(d => `
            <tr>
                <td class="fw-bold">#${d.doctor_id}</td>
                <td>${d.name}</td>
                <td><span class="badge bg-light text-dark border">${d.specialization}</span></td>
                <td>${d.email}</td>
                <td>${d.phone}</td>
                <td><i class="fas fa-circle ${d.available ? 'text-success' : 'text-danger'} me-2" style="font-size: 10px;"></i>${d.available ? 'Active' : 'Offline'}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary shadow-sm me-1" onclick="editDoctor(${d.doctor_id}, '${d.name.replace(/'/g,"\\'")}', '${d.specialization}', '${d.email}', '${d.phone}')"><i class="fas fa-edit"></i></button>
                    <button class="btn btn-sm btn-outline-danger shadow-sm" onclick="deleteDoctor(${d.doctor_id})"><i class="fas fa-trash"></i></button>
                </td>
            </tr>
        `).join('');
    } catch(e) { console.error(e); }
}

function editDoctor(id, name, specialization, email, phone) {
    document.getElementById('editDoctorId').value = id;
    document.getElementById('editName').value = name;
    document.getElementById('editSpecialization').value = specialization;
    document.getElementById('editEmail').value = email;
    document.getElementById('editPhone').value = phone;
    new bootstrap.Modal(document.getElementById('editDoctorModal')).show();
}

async function updateDoctor() {
    const id = document.getElementById('editDoctorId').value;
    const data = {
        name: document.getElementById('editName').value,
        specialization: document.getElementById('editSpecialization').value,
        email: document.getElementById('editEmail').value,
        phone: document.getElementById('editPhone').value
    };
    const btn = document.querySelector("#editDoctorModal .btn-primary");
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;

    const res = await fetch(`/admin/doctor/${id}`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    if (res.ok) {
        bootstrap.Modal.getInstance(document.getElementById('editDoctorModal')).hide();
        loadDoctors();
    } else {
        alert('Update failed');
    }
    btn.innerHTML = '<i class="fas fa-save me-2"></i> Save Changes';
    btn.disabled = false;
}

async function deleteDoctor(id) {
    if (!confirm('Are you absolutely sure you want to delete this doctor?')) return;
    const res = await fetch(`/admin/doctor/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
        loadDoctors();
    } else {
        alert('Delete failed');
    }
}

async function loadReports() {
    try {
        const res = await fetch('/admin/reports', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const reports = await res.json();
        const tbody = document.getElementById('reportsTableBody');
        if(reports.length === 0) {
             tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No reports in system.</td></tr>';
             return;
        }
        tbody.innerHTML = reports.map(r => `
            <tr>
                <td class="fw-bold">#${r.report_id}</td>
                <td>${r.patient_id}</td>
                <td class="text-truncate" style="max-width: 250px;">${r.symptoms}</td>
                <td><span class="badge bg-${r.severity==='Critical' ? 'danger' : r.severity==='Moderate' ? 'warning text-dark' : 'success'} shadow-sm">${r.severity}</span></td>
                <td><span class="badge ${r.status==='Completed'?'bg-success':'bg-secondary'}">${r.status}</span></td>
            </tr>
        `).join('');
    } catch(e) {}
}

function escHtml(unsafe) {
    if(!unsafe) return '';
    return unsafe.toString()
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

async function loadApprovals() {
    try {
        const res = await fetch('/admin/verification_requests', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const reqs = await res.json();
        const container = document.getElementById('approvalsList');
        if (reqs.length === 0) {
            container.innerHTML = '<div class="col-12 text-center text-muted p-4"><i class="fas fa-check-circle fa-3x mb-3 text-success"></i><br>No pending approvals.</div>';
            return;
        }
        container.innerHTML = reqs.map(r => `
            <div class="col-md-6 mb-3">
                <div class="card shadow-sm" style="border-radius:12px; border:none; border-left: 4px solid var(--primary);">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <h5 class="fw-bold mb-1">${escHtml(r.name)}</h5>
                            <small class="text-muted">${new Date(r.created_at).toLocaleDateString()}</small>
                        </div>
                        <div class="mb-2"><span class="badge bg-primary text-white shadow-sm">${escHtml(r.specialization)}</span></div>
                        <small class="text-muted d-block"><i class="fas fa-envelope me-2"></i>${escHtml(r.email)}</small>
                        <small class="text-muted d-block mb-2"><i class="fas fa-phone me-2"></i>${escHtml(r.phone)}</small>
                        <hr class="my-2 text-muted">
                        <small class="d-block mb-1"><strong>Education:</strong> ${escHtml(r.education)}</small>
                        <small class="d-block mb-1"><strong>Experience:</strong> ${r.experience_years} years</small>
                        <small class="d-block mb-3"><strong>Consultation Fee:</strong> $${r.online_treatment_fee}</small>
                        <div class="d-flex gap-2">
                            <button class="btn btn-sm btn-success w-50" onclick="approveDoctor(${r.id})"><i class="fas fa-check me-1"></i> Approve</button>
                            <button class="btn btn-sm btn-outline-danger w-50" onclick="rejectDoctor(${r.id})"><i class="fas fa-times me-1"></i> Reject</button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    } catch(e) {}
}

async function approveDoctor(id) {
    const res = await fetch(`/admin/approve_doctor/${id}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    if (res.ok) {
        alert(data.msg);
        loadApprovals();
        loadDoctors();
    } else {
        alert(data.msg || "Approval failed.");
    }
}

async function rejectDoctor(id) {
    if(!confirm("Are you sure you want to reject this request?")) return;
    const res = await fetch(`/admin/reject_doctor/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
        loadApprovals();
    }
}

async function loadAnalytics() {
    try {
        const res = await fetch('/admin/stats', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const stats = await res.json();
        const container = document.getElementById('statsCards');
        container.innerHTML = `
            <div class="col-md-4 mb-3">
                <div class="card bg-primary text-white p-3 shadow-sm h-100" style="border-radius:15px; border:none;">
                    <h3><i class="fas fa-users mb-2"></i><br>${stats.total_patients}</h3>
                    <p class="mb-0">Total Patients</p>
                </div>
            </div>
            <div class="col-md-4 mb-3">
                <div class="card bg-success text-white p-3 shadow-sm h-100" style="border-radius:15px; border:none;">
                    <h3><i class="fas fa-user-md mb-2"></i><br>${stats.total_doctors}</h3>
                    <p class="mb-0">Total Doctors</p>
                </div>
            </div>
            <div class="col-md-4 mb-3">
                <div class="card bg-warning text-dark p-3 shadow-sm h-100" style="border-radius:15px; border:none;">
                    <h3><i class="fas fa-file-medical-alt mb-2"></i><br>${stats.total_reports}</h3>
                    <p class="mb-0">Total Reports</p>
                </div>
            </div>
            <div class="col-md-6 mb-3">
                <div class="card shadow-sm p-3 h-100" style="border-radius:15px; border:none;">
                    <h5 class="text-muted border-bottom pb-2">Report Severities</h5>
                    <div class="d-flex justify-content-around mt-3">
                        <div class="text-center"><h4 class="text-danger">${stats.severity.Critical || 0}</h4><small>Critical</small></div>
                        <div class="text-center"><h4 class="text-warning">${stats.severity.Moderate || 0}</h4><small>Moderate</small></div>
                        <div class="text-center"><h4 class="text-success">${stats.severity.Normal || 0}</h4><small>Normal</small></div>
                    </div>
                </div>
            </div>
            <div class="col-md-6 mb-3">
                <div class="card shadow-sm p-3 h-100" style="border-radius:15px; border:none;">
                    <h5 class="text-muted border-bottom pb-2">Processing Status</h5>
                    <div class="d-flex justify-content-around mt-3">
                        <div class="text-center"><h4 class="text-primary">${stats.status.pending || 0}</h4><small>Pending</small></div>
                        <div class="text-center"><h4 class="text-success">${stats.status.reviewed || 0}</h4><small>Reviewed</small></div>
                    </div>
                </div>
            </div>
        `;
    } catch(e) {}
}

loadDoctors();
loadReports();
loadApprovals();
loadAnalytics();

function logout() {
    localStorage.clear();
    window.location.href = '/login';
}
