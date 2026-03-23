from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import os
from datetime import datetime
from models import Patient

def generate_pdf_report(report):
    filename = f"report_{report.report_id}.pdf"
    # Store in static/uploads so it works across OS (instead of /tmp)
    upload_dir = os.path.join(os.getcwd(), 'static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Fetch Patient 
    patient = Patient.query.get(report.patient_id)
    patient_name = patient.name if patient else "Unknown Patient"
    
    # Title
    story.append(Paragraph("<b>MedAI - Official Medical Report</b>", styles['Title']))
    story.append(Spacer(1, 12))
    
    # Metadata
    story.append(Paragraph(f"<b>Report ID:</b> {report.report_id}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {report.created_at.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Paragraph(f"<b>Patient Name:</b> {patient_name}", styles['Normal']))
    story.append(Paragraph(f"<b>Severity Level:</b> {report.severity_level}", styles['Normal']))
    story.append(Spacer(1, 24))
    
    # Content sections
    story.append(Paragraph("<b>Patient's Reported Symptoms:</b>", styles['Heading3']))
    story.append(Paragraph(str(report.symptoms_text).replace('\n', '<br/>'), styles['Normal']))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>AI Structured Analysis:</b>", styles['Heading3']))
    analysis_text = str(report.ai_generated_report).replace('\n', '<br/>')
    story.append(Paragraph(analysis_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>Doctor's Official Response:</b>", styles['Heading3']))
    doc_response = str(report.doctor_response) if report.doctor_response else "<i>Pending Review</i>"
    story.append(Paragraph(doc_response.replace('\n', '<br/>'), styles['Normal']))
    
    # Build PDF
    doc.build(story)
    return filepath