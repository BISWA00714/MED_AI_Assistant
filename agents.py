import os
import json
import uuid
import time
import base64
from gtts import gTTS
from groq import Groq
from models import db, Doctor, PatientReport

# Initialize the Groq client
try:
    # Requires GROQ_API_KEY environment variable
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    GROQ_ENABLED = True
except Exception as e:
    print(f"Groq Client initialization failed: {e}")
    GROQ_ENABLED = False

# Gemini Setup for Vision Fallback
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except ImportError:
        pass

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

SPECIALIZATION_KEYWORDS = {
    'Cardiologist': [
        'heart', 'chest pain', 'chest tightness', 'palpitations', 'irregular heartbeat',
        'high blood pressure', 'low blood pressure', 'hypertension', 'heart attack',
        'shortness of breath', 'angina', 'arrhythmia', 'heart failure', 'congestive heart failure',
        'coronary artery', 'elevated cholesterol', 'edema', 'swollen ankles', 'cardiovascular',
        'atherosclerosis', 'pericarditis', 'myocarditis', 'heart pounding'
    ],
    'Neurologist': [
        'headache', 'severe headache', 'migraine', 'brain', 'seizure', 'epilepsy',
        'dizziness', 'vertigo', 'numbness', 'tingling', 'memory loss', 'confusion',
        'tremor', 'shaking', 'weakness in limbs', 'stroke', 'paralysis', 'fainting',
        'loss of consciousness', 'cognitive decline', 'dementia', 'parkinson', 'multiple sclerosis',
        'nerve pain', 'neuropathy', 'slurred speech', 'balance problems', 'head injury',
        'concussion', 'twitching', 'restless legs'
    ],
    'Dermatologist': [
        'skin', 'rash', 'acne', 'pimples', 'eczema', 'psoriasis', 'hair loss', 'alopecia',
        'itching', 'hives', 'urticaria', 'dry skin', 'oily skin', 'dandruff', 'fungal infection',
        'ringworm', 'warts', 'moles', 'birthmark', 'skin discoloration', 'pigmentation',
        'sunburn', 'blisters', 'boils', 'abscess', 'skin lesion', 'dermatitis', 'redness',
        'peeling skin', 'nail infection', 'nail fungus', 'vitiligo', 'scabies', 'skin allergy',
        'chickenpox', 'cold sore', 'herpes', 'skin tag', 'cellulitis', 'wound not healing'
    ],
    'Orthopedic': [
        'bone', 'joint', 'fracture', 'broken bone', 'sprain', 'strain', 'back pain',
        'lower back pain', 'upper back pain', 'knee pain', 'knee swelling', 'hip pain',
        'shoulder pain', 'elbow pain', 'wrist pain', 'ankle pain', 'foot pain', 'neck pain',
        'stiff neck', 'arthritis', 'osteoporosis', 'scoliosis', 'slipped disc', 'herniated disc',
        'sciatica', 'muscle cramps', 'muscle weakness', 'tennis elbow', 'carpal tunnel',
        'plantar fasciitis', 'tendonitis', 'ligament tear', 'dislocation', 'bone pain',
        'joint stiffness', 'difficulty walking', 'limping', 'sports injury'
    ],
    'General Physician': [
        'fever', 'high temperature', 'cold', 'common cold', 'cough', 'flu', 'influenza',
        'fatigue', 'tiredness', 'weakness', 'body ache', 'mild pain', 'general checkup',
        'loss of appetite', 'weight loss', 'weight gain', 'dehydration', 'vomiting', 'nausea',
        'diarrhea', 'loose stools', 'constipation', 'bloating', 'indigestion', 'heartburn',
        'acid reflux', 'night sweats', 'chills', 'malaise', 'sore throat', 'runny nose',
        'sneezing', 'allergies', 'food poisoning', 'typhoid', 'malaria', 'dengue', 'jaundice'
    ],
    'Pediatrician': [
        'child', 'infant', 'baby', 'newborn', 'toddler', 'adolescent', 'vaccination',
        'immunization', 'growth delay', 'developmental delay', 'childhood fever', 'teething',
        'colic', 'bed wetting', 'attention deficit', 'adhd', 'autism', 'learning disability',
        'school performance', 'childhood asthma', 'childhood allergies', 'pediatric rash',
        'diaper rash', 'cradle cap', 'ear infection in child', 'tonsillitis in child',
        'feeding problems', 'weight in child', 'height in child', 'measles', 'mumps', 'rubella'
    ],
    'ENT Specialist': [
        'ear', 'ear pain', 'earache', 'ear infection', 'hearing loss', 'ringing in ears',
        'tinnitus', 'nose', 'nasal congestion', 'runny nose', 'nosebleed', 'loss of smell',
        'throat', 'sore throat', 'throat pain', 'difficulty swallowing', 'hoarseness',
        'voice change', 'tonsils', 'tonsillitis', 'adenoids', 'sinusitis', 'sinus pain',
        'sinus pressure', 'nasal polyp', 'snoring', 'sleep apnea', 'blocked nose',
        'postnasal drip', 'laryngitis', 'swollen glands', 'neck lump'
    ],
    'Gastroenterologist': [
        'stomach pain', 'abdominal pain', 'stomach cramps', 'nausea', 'vomiting', 'diarrhea',
        'constipation', 'blood in stool', 'black stool', 'rectal bleeding', 'irritable bowel',
        'ibs', 'crohns disease', 'ulcerative colitis', 'stomach ulcer', 'peptic ulcer',
        'gerd', 'gastrointestinal', 'liver pain', 'liver disease', 'fatty liver', 'hepatitis',
        'cirrhosis', 'jaundice', 'gallbladder', 'gallstones', 'pancreatitis', 'bloating',
        'gas', 'acidity', 'colon', 'colonoscopy', 'endoscopy', 'food intolerance',
        'celiac', 'swallowing difficulty', 'abdominal swelling', 'ascites'
    ],
    'Pulmonologist': [
        'breathing difficulty', 'shortness of breath', 'breathlessness', 'wheezing', 'asthma',
        'chronic cough', 'cough with blood', 'hemoptysis', 'lung pain', 'chest congestion',
        'bronchitis', 'pneumonia', 'copd', 'emphysema', 'pulmonary fibrosis', 'tuberculosis',
        'tb', 'pleural effusion', 'lung cancer', 'oxygen saturation', 'low oxygen', 'sputum',
        'phlegm', 'productive cough', 'respiratory infection', 'covid', 'post covid',
        'hyperventilation', 'sleep apnea', 'snoring', 'respiratory distress'
    ],
    'Endocrinologist': [
        'diabetes', 'high blood sugar', 'low blood sugar', 'insulin', 'thyroid', 'hypothyroidism',
        'hyperthyroidism', 'goiter', 'obesity', 'weight gain without reason', 'hormonal imbalance',
        'adrenal', 'pituitary', 'cushing syndrome', 'addisons disease', 'polycystic ovary',
        'pcos', 'insulin resistance', 'metabolic syndrome', 'growth hormone', 'excessive thirst',
        'frequent urination', 'sweating', 'heat intolerance', 'cold intolerance', 'calcium',
        'parathyroid', 'electrolyte imbalance', 'hypoglycemia', 'hyperglycemia'
    ],
    'Psychiatrist': [
        'depression', 'anxiety', 'panic attack', 'stress', 'mental health', 'suicidal thoughts',
        'self harm', 'mood swings', 'bipolar', 'schizophrenia', 'hallucinations', 'delusions',
        'obsessive compulsive', 'ocd', 'phobia', 'social anxiety', 'post traumatic stress',
        'ptsd', 'eating disorder', 'anorexia', 'bulimia', 'insomnia', 'sleep disorder',
        'nightmares', 'psychosis', 'personality disorder', 'attention deficit', 'adhd',
        'addiction', 'substance abuse', 'alcohol abuse', 'drug abuse', 'emotional instability',
        'crying spells', 'hopelessness', 'worthlessness', 'concentration problems'
    ],
    'Ophthalmologist': [
        'eye', 'eye pain', 'eye redness', 'red eye', 'itchy eyes', 'watery eyes', 'dry eyes',
        'blurred vision', 'double vision', 'vision loss', 'partial vision loss', 'floaters',
        'flashes of light', 'glaucoma', 'cataract', 'conjunctivitis', 'pink eye',
        'retinal detachment', 'macular degeneration', 'night blindness', 'light sensitivity',
        'photophobia', 'eye discharge', 'eye infection', 'stye', 'chalazion', 'squint',
        'crossed eyes', 'glasses', 'lens', 'pupil', 'corneal ulcer', 'uveitis', 'eye strain'
    ],
    'Nephrologist': [
        'kidney', 'kidney pain', 'kidney stone', 'kidney failure', 'renal', 'dialysis',
        'blood in urine', 'hematuria', 'protein in urine', 'swollen legs', 'urinary tract infection',
        'uti', 'cloudy urine', 'dark urine', 'reduced urine output', 'frequent urination at night',
        'nocturia', 'hypertension related to kidney', 'creatinine', 'elevated creatinine',
        'glomerulonephritis', 'nephritis', 'cysts in kidney', 'polycystic kidney', 'foamy urine'
    ],
    'Urologist': [
        'urinary', 'urine', 'painful urination', 'burning urination', 'frequent urination',
        'difficulty urinating', 'weak urine stream', 'bladder', 'bladder pain', 'bladder infection',
        'prostate', 'enlarged prostate', 'prostate cancer', 'erectile dysfunction', 'testicular pain',
        'testicular swelling', 'male infertility', 'vasectomy', 'kidney stone passing',
        'urinary incontinence', 'overactive bladder', 'urethral discharge', 'penile discharge'
    ],
    'Gynecologist': [
        'menstruation', 'irregular periods', 'missed period', 'heavy bleeding', 'painful periods',
        'dysmenorrhea', 'pcos', 'polycystic ovary', 'vaginal discharge', 'vaginal itching',
        'vaginal infection', 'pregnancy', 'pregnancy test', 'fertility', 'infertility',
        'contraception', 'birth control', 'menopause', 'hot flashes', 'ovarian cyst',
        'fibroid', 'endometriosis', 'pelvic pain', 'cervical cancer', 'ovarian cancer',
        'uterine cancer', 'breast lump', 'breast pain', 'nipple discharge', 'abnormal pap smear',
        'sexually transmitted infection', 'sti', 'vulvar itching', 'premature menopause'
    ],
    'Rheumatologist': [
        'rheumatoid arthritis', 'autoimmune', 'lupus', 'sle', 'joint inflammation',
        'joint swelling', 'stiff joints in morning', 'morning stiffness', 'gout', 'uric acid',
        'fibromyalgia', 'chronic pain all over', 'ankylosing spondylitis', 'sjogrens syndrome',
        'vasculitis', 'polymyalgia', 'scleroderma', 'myositis', 'muscle inflammation',
        'raynaud phenomenon', 'blue fingers in cold', 'dry eyes dry mouth', 'positive ana test'
    ],
    'Oncologist': [
        'cancer', 'tumor', 'malignant', 'lump', 'unexplained weight loss', 'night sweats cancer',
        'lymph node swelling', 'blood cancer', 'leukemia', 'lymphoma', 'chemotherapy',
        'radiation therapy', 'biopsy', 'metastasis', 'stage cancer', 'carcinoma', 'sarcoma',
        'melanoma', 'bone marrow', 'abnormal growth', 'unexplained fatigue', 'anemia cancer',
        'prostate cancer', 'breast cancer', 'cervical cancer', 'colon cancer', 'lung cancer'
    ],
    'Hematologist': [
        'anemia', 'low hemoglobin', 'low rbc', 'pale skin', 'fatigue anemia', 'sickle cell',
        'thalassemia', 'blood clot', 'deep vein thrombosis', 'dvt', 'pulmonary embolism',
        'bleeding disorder', 'hemophilia', 'low platelets', 'thrombocytopenia', 'high wbc',
        'leukocytosis', 'polycythemia', 'blood transfusion', 'easy bruising', 'prolonged bleeding',
        'iron deficiency', 'vitamin b12', 'folate deficiency', 'bone marrow failure'
    ],
    'Dentist': [
        'tooth pain', 'toothache', 'cavity', 'dental caries', 'gum pain', 'gum swelling',
        'bleeding gums', 'bad breath', 'halitosis', 'tooth sensitivity', 'broken tooth',
        'cracked tooth', 'missing tooth', 'wisdom tooth', 'jaw pain', 'mouth ulcer',
        'canker sore', 'teeth grinding', 'bruxism', 'tooth abscess', 'dental infection',
        'loose tooth', 'white spots on teeth', 'mouth sores', 'oral thrush'
    ]
}

def agent1_report_generator(symptoms, image_path=None):
    """Convert raw input to structured report using Groq"""
    if not GROQ_ENABLED:
        return (
            f"CLINICAL OBSERVATION\n"
            f"--------------------\n"
            f"Presenting Symptoms: {symptoms}\n"
            f"Duration / Onset: Not explicitly stated\n"
            f"Primary Assessment: General presentation based on provided symptoms.\n"
            f"Recommended Next Steps: Consult assigned specialist for detailed clinical evaluation.\n\n"
            f"[System Note: Groq AI API Key not configured. Using standard template.]"
        )
    
    prompt = (
        f"You are a highly experienced medical documentation specialist. Convert the following patient-reported symptoms "
        f"into a formal, structured clinical observation report.\n\n"
        f"Patient Symptoms: {symptoms}\n\n"
        f"Generate the report with the following clearly labeled sections:\n"
        f"1. PRESENTING SYMPTOMS - List all observed symptoms clearly\n"
        f"2. ONSET & DURATION - Note any time-related information if mentioned, otherwise state 'Not specified'\n"
        f"3. POSSIBLE CONDITIONS - List 2-3 potential medical conditions based on the symptoms, ordered by likelihood\n"
        f"4. RISK FACTORS - Any relevant risk factors to note\n"
        f"5. RECOMMENDED INVESTIGATIONS - Suggest relevant diagnostic tests or examinations\n"
        f"6. CLINICAL SUMMARY - A brief, professional overall assessment\n\n"
        f"Be thorough, professional, and use standard medical terminology where appropriate."
    )

    messages = [{"role": "user", "content": prompt}]
    model = "llama-3.3-70b-versatile"

    if image_path and os.path.exists(image_path):
        try:
            vision_context = ""
            if gemini_client:
                from google.genai.types import Part
                with open(image_path, "rb") as img_f:
                    img_bytes = img_f.read()
                vision_resp = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=["Analyze this medical image in detail. List the visible symptoms and possible dermatological or physical conditions.", Part.from_bytes(data=img_bytes, mime_type='image/jpeg')]
                )
                vision_context = f"\n\n[Google Gemini Vision Analysis of patient's uploaded image: {vision_resp.text}]"
            else:
                vision_context = "\n\n[System Notice: Patient uploaded an image, but GEMINI_API_KEY is missing. Ignore the image.]"
                
            messages[0]["content"] = (
                f"You are a highly experienced medical documentation specialist. The patient has uploaded a medical image. "
                f"Review the provided text symptoms and the detailed Vision Analysis from the image below.\n\n"
                f"Patient Text Symptoms: {symptoms}{vision_context}\n\n"
                f"Generate a structured clinical observation report with these clearly labeled sections:\n"
                f"1. PRESENTING SYMPTOMS - List all observed symptoms from the text and image analysis\n"
                f"2. ONSET & DURATION - Note any time-related information if mentioned, otherwise state 'Not specified'\n"
                f"3. POSSIBLE CONDITIONS - List 2-3 potential medical conditions, ordered by likelihood\n"
                f"4. RISK FACTORS - Any relevant risk factors to note\n"
                f"5. RECOMMENDED INVESTIGATIONS - Suggest relevant diagnostic tests\n"
                f"6. CLINICAL SUMMARY - A brief, professional overall assessment\n\n"
                f"Be thorough, professional, and use standard medical terminology where appropriate."
            )
        except Exception as e:
            print(f"Error processing image for text fallback: {e}")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"SYMPTOMS: {symptoms}\nError generating report: {str(e)}"

def agent2_decision_agent(symptoms, ai_report):
    """Classify severity using Groq"""
    if not GROQ_ENABLED:
        symptoms_lower = symptoms.lower()
        if 'chest pain' in symptoms_lower or 'unconscious' in symptoms_lower: return 'Critical'
        if 'pain' in symptoms_lower: return 'Moderate'
        return 'Normal'
        
    prompt = (
        f"You are a medical triage expert. Based on the patient's symptoms and AI-generated clinical report below, "
        f"classify the severity of the case into exactly ONE of these categories:\n"
        f"- Normal: Minor, non-urgent symptoms that can be managed with basic self-care or standard OTC medication\n"
        f"- Moderate: Symptoms that require professional medical attention soon but are not immediately life-threatening\n"
        f"- Critical: Potentially life-threatening symptoms requiring urgent or emergency medical care\n\n"
        f"Patient Symptoms: {symptoms}\n"
        f"AI Clinical Report:\n{ai_report}\n\n"
        f"Respond with ONLY a single word: Normal, Moderate, or Critical."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a senior medical triage specialist. You always respond with exactly one word: Normal, Moderate, or Critical."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        text = response.choices[0].message.content.strip()
        text = text.strip('.,;!"\'-').capitalize()
        if 'Critical' in text: return 'Critical'
        if 'Normal' in text: return 'Normal'
        return 'Moderate'
    except Exception:
        return 'Moderate'

def agent3_ai_doctor(symptoms, ai_report):
    """Provide basic guidance for normal cases"""
    if not GROQ_ENABLED:
        return "Rest and stay hydrated. Consult a doctor if symptoms persist."
        
    prompt = (
        f"You are a compassionate and knowledgeable AI health assistant helping a patient with minor symptoms. "
        f"Based on the reported symptoms and clinical report, provide clear, structured, and practical health guidance.\n\n"
        f"Patient Symptoms: {symptoms}\n"
        f"Clinical Report Summary:\n{ai_report}\n\n"
        f"Please provide your response in the following format:\n"
        f"**IMMEDIATE CARE TIPS**\n"
        f"- List 3-4 immediate self-care steps the patient can take right now\n\n"
        f"**SUGGESTED OTC REMEDIES**\n"
        f"- Suggest safe, commonly available over-the-counter medications or remedies (avoid brand names, use generic names)\n\n"
        f"**LIFESTYLE RECOMMENDATIONS**\n"
        f"- List 2-3 lifestyle tips such as rest, diet, or activity modifications\n\n"
        f"**WHEN TO SEE A DOCTOR**\n"
        f"- Clearly state warning signs that should prompt the patient to seek professional help\n\n"
        f"End your response with this exact disclaimer:\n"
        f"⚕️ DISCLAIMER: This AI guidance is for general informational purposes only and does not constitute professional medical advice. Please consult a qualified healthcare professional for personalized medical care."
    )
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful, empathetic, and knowledgeable AI health assistant. You provide safe, practical, and well-structured health guidance for minor medical issues."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception:
        return "Rest and stay hydrated. Monitor your symptoms. Consult a doctor if symptoms worsen or persist."

def agent4_doctor_selector(symptoms, ai_report):
    """Map symptoms to specialization and return a doctor ID"""
    if not GROQ_ENABLED:
        return _fallback_selector(symptoms)
        
    specialties_str = "\n".join(f"- {s}" for s in SPECIALIZATION_KEYWORDS.keys())
    prompt = (
        f"A patient has reported the following symptoms. Based on your medical expertise, determine the single most "
        f"appropriate specialist from the list below who should handle this case.\n\n"
        f"Patient Symptoms: {symptoms}\n\n"
        f"Clinical Report:\n{ai_report}\n\n"
        f"Available Specializations:\n{specialties_str}\n\n"
        f"Rules:\n"
        f"1. Select the ONE specialization that best matches the primary complaint.\n"
        f"2. Your response must be ONLY the exact specialization name from the list above — nothing else.\n"
        f"3. If truly unclear, respond with: General Physician"
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a senior medical triage specialist who assigns patients to the correct medical department. You only respond with the exact specialization name and nothing else."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        chosen_specialization = response.choices[0].message.content.strip().strip('.,;!"\'-')
        # Validate the response is in our known list
        if chosen_specialization not in SPECIALIZATION_KEYWORDS:
            chosen_specialization = 'General Physician'
    except Exception:
        chosen_specialization = 'General Physician'

    doctor = Doctor.query.filter_by(specialization=chosen_specialization, available=True).first()
    if not doctor:
        doctor = Doctor.query.filter_by(available=True).first()
    return doctor.doctor_id if doctor else None

def _fallback_selector(symptoms):
    """Score-based fallback: picks specialization with the most keyword matches"""
    symptoms_lower = symptoms.lower()
    scores = {spec: 0 for spec in SPECIALIZATION_KEYWORDS}
    for spec, keywords in SPECIALIZATION_KEYWORDS.items():
        for kw in keywords:
            if kw in symptoms_lower:
                scores[spec] += 1
    # Pick the specialization with the highest score
    best_spec = max(scores, key=scores.get)
    chosen_specialization = best_spec if scores[best_spec] > 0 else 'General Physician'
    doctor = Doctor.query.filter_by(specialization=chosen_specialization, available=True).first()
    if not doctor:
        doctor = Doctor.query.filter_by(available=True).first()
    return doctor.doctor_id if doctor else None

def agent5_translate_and_tts(text, target_lang):
    """Translate and generate TTS"""
    final_text = text
    if target_lang != 'English' and GROQ_ENABLED:
        prompt = f"Translate the following medical text into {target_lang}. Keep it simple and easy to understand. ONLY return the translated text.\nText: {text}"
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            final_text = response.choices[0].message.content.strip()
        except Exception:
            pass
            
    audio_filename = f"audio_{uuid.uuid4().hex[:8]}.mp3"
    audio_path = os.path.join('static', 'uploads', audio_filename)
    try:
        lang_code = {'English': 'en', 'Hindi': 'hi', 'Telugu': 'te', 'Marathi': 'mr', 'Odia': 'or'}.get(target_lang, 'en')
        tts = gTTS(text=final_text, lang=lang_code)
        tts.save(audio_path)
    except Exception as e:
        print(f"TTS error: {e}")
        audio_filename = None
        
    return final_text, audio_filename

def process_patient_input(patient_id, symptoms, image_filename, language):
    """Main workflow orchestrator"""
    os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
    image_path = os.path.join('static', 'uploads', image_filename) if image_filename else None
    
    ai_report = agent1_report_generator(symptoms, image_path)
    time.sleep(1) 
    severity = agent2_decision_agent(symptoms, ai_report)
    
    result = {
        'ai_report': ai_report,
        'severity': severity,
        'assigned_doctor_id': None,
        'ai_advice': None,
        'final_output': '',
        'audio_file': None
    }
    
    if severity == 'Normal':
        advice = agent3_ai_doctor(symptoms, ai_report)
        result['ai_advice'] = advice
        final_text, audio_file = agent5_translate_and_tts(advice, language)
        result['final_output'] = final_text
        result['audio_file'] = audio_file
    else:
        doctor_id = agent4_doctor_selector(symptoms, ai_report)
        result['assigned_doctor_id'] = doctor_id
        spec = Doctor.query.get(doctor_id).specialization if doctor_id else 'doctor'
        msg = f"Your report has been assigned to a {spec}. The doctor will review your case and provide a diagnosis soon."
        final_text, audio_file = agent5_translate_and_tts(msg, language)
        result['final_output'] = final_text
        result['audio_file'] = audio_file
        
    return result


# ---------------------------------------------------------------------------
# NEW: Conversational Triage Agent
# ---------------------------------------------------------------------------

LANG_GREETINGS = {
    'English': "Hello! I'm your AI health assistant. Please tell me about the symptoms you're experiencing today.",
    'Hindi': "नमस्ते! मैं आपका AI स्वास्थ्य सहायक हूँ। कृपया अपने लक्षणों के बारे में बताएं।",
    'Telugu': "హలో! నేను మీ AI ఆరోగ్య సహాయకుడిని. దయచేసి మీకు కలుగుతున్న సమస్యలు చెప్పండి.",
    'Marathi': "नमस्कार! मी तुमचा AI आरोग्य सहाय्यक आहे. कृपया तुम्हाला होत असलेल्या लक्षणांबद्दल सांगा.",
    'Tamil': "வணக்கம்! நான் உங்கள் AI சுகாதார உதவியாளர். நீங்கள் அனுபவிக்கும் அறிகுறிகளை சொல்லுங்கள்.",
    'Bengali': "হ্যালো! আমি আপনার AI স্বাস্থ্য সহকারী। আপনার উপসর্গ সম্পর্কে বলুন।",
    'Odia': "ନମସ୍କାର! ମୁଁ ଆପଣଙ୍କର AI ସ୍ୱାସ୍ଥ୍ୟ ସହାୟକ। ଦୟାକରି ଆପଣଙ୍କର ଲକ୍ଷଣ ବିଷୟରେ ଜଣାନ୍ତୁ।",
}

NO_MORE_ISSUES_KEYWORDS = [
    'no', 'nahi', 'nahi hai', 'illey', 'illa', 'ille', 'nahin', 'kuch nahi',
    'no other', 'nothing else', 'thats all', "that's all", 'bas', 'enough',
    'i am fine', "i'm fine", 'no issue', 'no more', 'no problem',
    "didn't", 'no symptom', 'nothing more', 'that is all'
]

def get_greeting(language):
    return LANG_GREETINGS.get(language, LANG_GREETINGS['English'])

def agent_triage_chat(history, new_message, language, image_b64=None):
    """
    Conversational triage agent. Maintains history and asks follow-up questions.
    Returns (ai_reply: str, is_complete: bool).
    is_complete = True when the patient confirms no more issues.
    """
    if not GROQ_ENABLED:
        lowered = new_message.lower()
        is_done = any(kw in lowered for kw in NO_MORE_ISSUES_KEYWORDS)
        if is_done:
            return "Thank you for sharing. I'll now prepare your medical report.", True
        return "I understand. Are you experiencing any other symptoms or issues?", False

    lang_instruction = (
        f"CRITICAL INSTRUCTION: You MUST reply entirely in {language} using its correct native script. "
        f"NEVER use English letters or words unless referring to a specific medication. "
        f"Ensure flawless grammar in {language}. "
        if language != 'English' else ""
    )

    system_prompt = (
        f"You are a compassionate, professional AI health triage assistant. {lang_instruction}"
        f"Your job is to gently converse with the patient to fully understand their health issue. "
        f"Ask ONE focused follow-up question at a time (e.g., duration, severity, location, associated symptoms, medical history). "
        f"Be warm, empathetic, and professional. "
        f"When the patient clearly indicates they have no more issues to report (e.g. says 'no', 'nothing else', 'that's all', or equivalent in their language), "
        f"reply with a brief, warm closing message saying you will now prepare their report, "
        f"and APPEND the exact text '[[CHAT_COMPLETE]]' at the very end of your reply on a new line. "
        f"Do NOT append '[[CHAT_COMPLETE]]' until the patient confirms no more issues."
    )

    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in history:
        # Protect against older history formats that lack text content if there's vision
        messages.append({"role": msg['role'], "content": msg['content']})

    user_text = new_message if new_message else ""
    if image_b64:
        if gemini_client:
            from google.genai.types import Part
            import base64
            try:
                img_bytes = base64.b64decode(image_b64)
                vision_resp = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=["Analyze this medical image in detail. Describe exactly what you see including any potential dermatological, ocular, or physical symptoms.", Part.from_bytes(data=img_bytes, mime_type='image/jpeg')]
                )
                user_text += f"\n\n[System Notice: The patient just uploaded an image. Here is the automated Vision Analysis report of that image:\n{vision_resp.text}\nPlease seamlessly integrate this observation into your next response.]"
            except Exception as e:
                user_text += f"\n\n[System Notice: Vision API failed: {e}]"
        else:
            user_text += "\n[System Notice: The patient uploaded an image, but visual processing requires a GEMINI_API_KEY in the .env. Please ask the patient to describe the image textually instead.]"
        
    messages.append({"role": "user", "content": user_text})
    model = "llama-3.3-70b-versatile"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.4,
            max_tokens=512
        )
        reply = response.choices[0].message.content.strip()
        is_complete = '[[CHAT_COMPLETE]]' in reply
        clean_reply = reply.replace('[[CHAT_COMPLETE]]', '').strip()
        return clean_reply, is_complete
    except Exception as e:
        return f"I'm sorry, I encountered an issue. Please try again. ({str(e)})", False


def generate_report_from_chat(history, language):
    """
    After chat is complete, summarize the conversation into symptoms text
    and run it through the full multi-agent pipeline.
    """
    # Build a plain-text conversation summary to extract symptoms
    conversation_text = "\n".join(
        f"{'Patient' if m['role'] == 'user' else 'AI'}: {m['content']}"
        for m in history
    )

    if not GROQ_ENABLED:
        # Fallback: just use user messages as symptoms
        symptoms = " ".join(m['content'] for m in history if m['role'] == 'user')
        return process_patient_input(None, symptoms, None, language)

    extraction_prompt = (
        f"Based on the following doctor-patient conversation, extract ALL symptoms, "
        f"complaints, and relevant medical information the patient mentioned. "
        f"Write it as a concise, structured symptom summary in English for use in a medical report.\n\n"
        f"Conversation:\n{conversation_text}\n\nSymptom Summary:"
    )
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0.1,
            max_tokens=512
        )
        symptoms = resp.choices[0].message.content.strip()
    except Exception:
        symptoms = " ".join(m['content'] for m in history if m['role'] == 'user')

    return process_patient_input(None, symptoms, None, language)
