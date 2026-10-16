import os
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'gesturebridge.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CLINICAL_ACCESS_PIN = "4421"

class Patient(db.Model):
    __tablename__ = 'patients'
    bed_id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    diagnosis = db.Column(db.String(255), nullable=False)
    attending_dr = db.Column(db.String(100), nullable=False)
    prescriptions = db.Column(db.Text, nullable=False)
    allergies = db.Column(db.String(100), nullable=False)
    diet = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default="Stable")
    hr = db.Column(db.Integer, default=75)
    spo2 = db.Column(db.Integer, default=98)
    systolic = db.Column(db.Integer, default=120)
    diastolic = db.Column(db.Integer, default=80)
    resp_rate = db.Column(db.Integer, default=16)
    pain = db.Column(db.Integer, default=2)
    body_part = db.Column(db.String(50), default="Chest")
    alert_level = db.Column(db.String(20), default="normal")

class TriageEvent(db.Model):
    __tablename__ = 'triage_events'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bed_id = db.Column(db.String(10), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    key = db.Column(db.String(50), nullable=False)
    region = db.Column(db.String(50), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    phrase = db.Column(db.Text, nullable=False)
    urgency = db.Column(db.String(20), nullable=False)
    pain = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.String(50), nullable=False)
    source = db.Column(db.String(100), nullable=False)

def seed_database():
    if Patient.query.count() == 0:
        initial_patients = [
            Patient(bed_id="BED-01", name="Robert Chen", age=58, gender="Male", diagnosis="Post-Coronary Angioplasty", attending_dr="Dr. Sarah Jenkins, MD", prescriptions="Aspirin 75mg OD;Atorvastatin 40mg HS;Metoprolol 25mg BD", allergies="Penicillin", diet="Low Sodium Cardiac Diet", status="Stable", hr=72, spo2=98, systolic=118, diastolic=76, resp_rate=15, pain=1, body_part="None"),
            Patient(bed_id="BED-02", name="Elena Vance", age=42, gender="Female", diagnosis="Acute Bronchospasm & Asthma Exacerbation", attending_dr="Dr. A. K. Sharma, MD", prescriptions="Salbutamol Nebulization QDS;Budesonide Inhaler BD;Hydrocortisone 100mg IV", allergies="Sulfa Drugs", diet="Soft Diet", status="Observation", hr=89, spo2=94, systolic=134, diastolic=86, resp_rate=22, pain=4, body_part="Chest"),
            Patient(bed_id="BED-03", name="Marcus Aurel", age=67, gender="Male", diagnosis="Cerebrovascular Recovery & Hemiparesis", attending_dr="Dr. R. Mehta, Neurologist", prescriptions="Clopidogrel 75mg OD;Citicoline 500mg BD;Physiotherapy BID", allergies="NKDA", diet="Dysphagia Pureed Diet", status="Stable", hr=66, spo2=99, systolic=122, diastolic=78, resp_rate=14, pain=2, body_part="Head"),
            Patient(bed_id="BED-04", name="Patient Alpha", age=21, gender="Female", diagnosis="Non-Verbal ICU Telemetry & Vocal Rehabilitation", attending_dr="Dr. Emily Watson, Chief Intensivist", prescriptions="IV Paracetamol 1g SOS;Ceftriaxone 1g IV BD;Multivitamin Infusion OD", allergies="NKDA", diet="NPO (Nil Per Os) / IV Fluids Only", status="Active Monitored", hr=80, spo2=98, systolic=120, diastolic=80, resp_rate=16, pain=2, body_part="Chest")
        ]
        db.session.bulk_save_objects(initial_patients)
        db.session.commit()

with app.app_context():
    db.create_all()
    seed_database()

active_bed_id = "BED-02"

ALLERGY_CONFLICTS = {
    "penicillin": ["amoxicillin", "ampicillin", "augmentin", "piperacillin", "penicillin"],
    "sulfa": ["sulfamethoxazole", "bactrim", "sulfadiazine", "co-trimoxazole"],
    "nsaid": ["ibuprofen", "aspirin", "naproxen", "ketorolac", "diclofenac"]
}

# Multilingual Clinical Trigger Dictionary (EN, HI, MR)
CLINICAL_TRIGGERS = {
    "OXYGEN": {
        "label": {"en": "Oxygen / Dyspnea", "hi": "ऑक्सीजन / सांस की तकलीफ", "mr": "ऑक्सिजन / धाप लागणे"},
        "category": "Respiratory", "urgency": "critical",
        "phrase": {
            "en": "Patient reports acute respiratory distress. Verify oxygen cannula and flow rate.",
            "hi": "मरीज को सांस लेने में तीव्र कठिनाई हो रही है। कृपया तुरंत ऑक्सीजन की जांच करें।",
            "mr": "रुग्णाला श्वास घेण्यास तीव्र त्रास होत आहे. ऑक्सिजन पुरवठा त्वरित तपासा."
        }
    },
    "ACUTE_PAIN": {
        "label": {"en": "Severe Pain Surge", "hi": "तीव्र दर्द का दौरा", "mr": "तीव्र वेदनांची लाट"},
        "category": "Urgent", "urgency": "critical",
        "phrase": {
            "en": "Acute localized pain spike reported. Clinical analgesic evaluation requested.",
            "hi": "तीव्र दर्द की सूचना मिली है। दर्द निवारक दवा की आवश्यकता है।",
            "mr": "तीव्र वेदना होत असल्याची नोंद झाली आहे. वेदनाशामक औषधाची गरज आहे."
        }
    },
    "SUCTION": {
        "label": {"en": "Airway Suction", "hi": "वायुमार्ग सक्शन", "mr": "श्वासनलिका सक्शन"},
        "category": "Respiratory", "urgency": "critical",
        "phrase": {
            "en": "Tracheal airway clearance assistance requested at bedside.",
            "hi": "वायुमार्ग साफ करने के लिए सक्शन सहायता की आवश्यकता है।",
            "mr": "श्वासनलिका स्वच्छ करण्यासाठी सक्शन मदतीची आवश्यकता आहे."
        }
    },
    "MEDICATION": {
        "label": {"en": "Medication Due", "hi": "दवा का समय", "mr": "औषधाची वेळ"},
        "category": "Clinical", "urgency": "moderate",
        "phrase": {
            "en": "Patient requesting administration of scheduled pain or maintenance dose.",
            "hi": "मरीज निर्धारित समय की दवा देने का अनुरोध कर रहा है।",
            "mr": "रुग्ण ठरलेली वेळेची औषधे देण्याची विनंती करत आहे."
        }
    },
    "IV_ISSUE": {
        "label": {"en": "IV Line Discomfort", "hi": "आईवी ड्रिप में समस्या", "mr": "सलाईन / आयव्ही त्रास"},
        "category": "Infusion", "urgency": "moderate",
        "phrase": {
            "en": "Occlusion or discomfort reported at venous catheter site.",
            "hi": "आईवी सुई की जगह पर दर्द या रुकावट की सूचना है।",
            "mr": "आयव्ही सलाईनच्या जागेवर दुखत किंवा सूज आल्याची नोंद आहे."
        }
    },
    "RESTROOM": {
        "label": {"en": "Washroom Assist", "hi": "शौचालय सहायता", "mr": "शौचालय मदत"},
        "category": "Basic Care", "urgency": "moderate",
        "phrase": {
            "en": "Patient requires immediate sanitation or bedpan transfer support.",
            "hi": "मरीज को तुरंत शौचालय या बेडपैन सहायता की आवश्यकता है।",
            "mr": "रुग्णाला त्वरित वॉशरूम किंवा बेडपॅन मदतीची आवश्यकता आहे."
        }
    },
    "HYDRATION": {
        "label": {"en": "Drinking Water", "hi": "पीने का पानी", "mr": "पिण्याचे पाणी"},
        "category": "Basic Care", "urgency": "normal",
        "phrase": {
            "en": "Patient is requesting assistance with water intake.",
            "hi": "मरीज को पीने के लिए पानी चाहिए।",
            "mr": "रुग्णाला पिण्यासाठी पाणी हवे आहे."
        }
    },
    "REPOSITION": {
        "label": {"en": "Bed Reposition", "hi": "करवट बदलना", "mr": "कुशी बदलणे"},
        "category": "Comfort", "urgency": "normal",
        "phrase": {
            "en": "Patient requests posture repositioning to relieve pressure points.",
            "hi": "मरीज आराम के लिए करवट बदलने का अनुरोध कर रहा है।",
            "mr": "रुग्ण आराम मिळण्यासाठी कुशी बदलण्याची विनंती करत आहे."
        }
    },
    "FEELING_COLD": {
        "label": {"en": "Thermal Blanket", "hi": "कंबल / ठंड लगना", "mr": "थंडी वाजणे / ब्लँकेट"},
        "category": "Comfort", "urgency": "normal",
        "phrase": {
            "en": "Patient reports chills; warming blanket requested.",
            "hi": "मरीज को ठंड लग रही है, कंबल की आवश्यकता है।",
            "mr": "रुग्णाला थंडी वाजत आहे, गरम ब्लँकेटची गरज आहे."
        }
    },
    "PHYSICIAN": {
        "label": {"en": "Call Attending MD", "hi": "डॉक्टर को बुलाएं", "mr": "डॉक्टरांना बोलवा"},
        "category": "Clinical", "urgency": "critical",
        "phrase": {
            "en": "Attending medical officer requested at bedside for evaluation.",
            "hi": "उपचार कर रहे डॉक्टर को तुरंत मरीज के पास आने का अनुरोध है।",
            "mr": "तपासणीसाठी ड्युटी डॉक्टरांना त्वरित बोलावले आहे."
        }
    },
    "DIZZINESS": {
        "label": {"en": "Dizziness / Faint", "hi": "चक्कर आना / बेहोशी", "mr": "चक्कर येणे / अंधारी"},
        "category": "Neurological", "urgency": "moderate",
        "phrase": {
            "en": "Patient reports sudden postural dizziness and lightheadedness.",
            "hi": "मरीज को अचानक तेज चक्कर और कमजोरी महसूस हो रही है।",
            "mr": "रुग्णाला अचानक चक्कर आणि अंधारी येत आहे."
        }
    },
    "CODE_BLUE": {
        "label": {"en": "CODE BLUE", "hi": "कोड ब्लू (आपातकाल)", "mr": "कोड ब्लू (तातडी)"},
        "category": "Emergency", "urgency": "critical",
        "phrase": {
            "en": "CODE BLUE: Emergency medical resuscitation team required at bedside immediately!",
            "hi": "कोड ब्लू: आपातकालीन पुनर्जीवन टीम तुरंत मरीज के पास पहुंचे!",
            "mr": "कोड ब्लू: तातडीच्या पुनरुज्जीवन वैद्यकीय पथकाने त्वरित उपस्थित राहावे!"
        }
    }
}

BODY_REGIONS = {
    "HEAD": "Cranial / Head", "CHEST": "Retrosternal Chest", "ABDOMEN": "Abdominal Core",
    "L_ARM": "Left Upper Extremity", "R_ARM": "Right Upper Extremity",
    "SPINE": "Lumbar / Spine", "L_LEG": "Left Lower Extremity", "R_LEG": "Right Lower Extremity"
}

def calculate_news2(patient):
    score = 0
    if patient.resp_rate >= 25 or patient.resp_rate <= 8: score += 3
    elif patient.resp_rate >= 21: score += 2
    if patient.spo2 <= 91: score += 3
    elif patient.spo2 <= 93: score += 2
    if patient.hr >= 131 or patient.hr <= 40: score += 3
    elif patient.hr >= 111: score += 2
    if patient.pain >= 7: score += 2
    return score

def compute_ai_triage(patient, news2):
    map_val = round(patient.diastolic + (patient.systolic - patient.diastolic) / 3, 1)
    if news2 >= 5 or patient.hr > 130 or patient.spo2 < 90:
        return {"level": "CRITICAL", "prediction": "Immediate hemodynamic decompensation risk. Stat arterial blood gas (ABG) & rapid response recommended.", "color": "rose"}
    elif news2 >= 3 or map_val < 65 or patient.pain >= 7:
        return {"level": "MODERATE", "prediction": "Elevated early deterioration trajectory. Recommended: titrate supplemental oxygen and assess fluid responsiveness.", "color": "amber"}
    return {"level": "OPTIMAL", "prediction": "Physiological baseline stable. Hemodynamic parameters well within target therapeutic window.", "color": "emerald"}

@app.route('/')
def home():
    return render_template('index.html', triggers=CLINICAL_TRIGGERS, regions=BODY_REGIONS)

@app.route('/api/state', methods=['GET'])
def get_state():
    global active_bed_id
    patient = Patient.query.get(active_bed_id)
    if not patient:
        first = Patient.query.first()
        if first:
            active_bed_id = first.bed_id
            patient = first
        else:
            return jsonify({"status": "no_patients"}), 200

    patient.hr = max(45, min(150, patient.hr + random.choice([-1, 0, 0, 1])))
    patient.spo2 = max(85, min(100, patient.spo2 + random.choice([-1, 0, 0, 1])))
    db.session.commit()

    map_val = round(patient.diastolic + (patient.systolic - patient.diastolic) / 3, 1)
    news2_val = calculate_news2(patient)
    ai_risk = compute_ai_triage(patient, news2_val)

    all_patients = Patient.query.all()
    ward_overview = {
        p.bed_id: {
            "name": p.name, "age": p.age, "gender": p.gender,
            "status": p.status, "alert": p.alert_level,
            "hr": p.hr, "spo2": p.spo2, "bp": f"{p.systolic}/{p.diastolic}",
            "diagnosis": p.diagnosis, "attending_dr": p.attending_dr,
            "news2": calculate_news2(p)
        } for p in all_patients
    }

    recent_events = TriageEvent.query.order_by(TriageEvent.id.desc()).limit(15).all()
    logs = [{
        "id": e.id, "bed": e.bed_id, "patient_name": e.patient_name,
        "key": e.key, "phrase": e.phrase, "urgency": e.urgency,
        "pain": e.pain, "timestamp": e.timestamp, "source": e.source
    } for e in recent_events]

    patient_dict = {
        "bed_id": patient.bed_id, "name": patient.name, "age": patient.age,
        "gender": patient.gender, "diagnosis": patient.diagnosis,
        "attending_dr": patient.attending_dr, "prescriptions": [x.strip() for x in patient.prescriptions.split(";") if x.strip()],
        "allergies": patient.allergies, "diet": patient.diet, "status": patient.status,
        "hr": patient.hr, "spo2": patient.spo2, "systolic": patient.systolic,
        "diastolic": patient.diastolic, "resp_rate": patient.resp_rate,
        "pain": patient.pain, "body_part": patient.body_part, "alert_level": patient.alert_level
    }

    return jsonify({
        "active_bed_id": active_bed_id,
        "patient": patient_dict,
        "map_val": map_val,
        "news2_score": news2_val,
        "ai_risk": ai_risk,
        "ward_overview": ward_overview,
        "audit_logs": logs
    })

@app.route('/api/fhir_export', methods=['GET'])
def fhir_export():
    """Generates official HL7 FHIR Release 4 Diagnostic Bundle."""
    global active_bed_id
    patient = Patient.query.get(active_bed_id)
    if not patient: return jsonify({"error": "No active patient"}), 404

    now_iso = datetime.utcnow().isoformat() + "Z"
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": now_iso,
        "entry": [
            {
                "fullUrl": f"urn:uuid:patient-{patient.bed_id}",
                "resource": {
                    "resourceType": "Patient",
                    "id": patient.bed_id,
                    "identifier": [{"system": "http://hospital.org/bed-tracker", "value": patient.bed_id}],
                    "name": [{"use": "official", "text": patient.name}],
                    "gender": patient.gender.lower(),
                    "birthDate": str(datetime.now().year - patient.age) + "-01-01"
                }
            },
            {
                "fullUrl": f"urn:uuid:observation-hr-{patient.bed_id}",
                "resource": {
                    "resourceType": "Observation",
                    "status": "final",
                    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
                    "subject": {"reference": f"Patient/{patient.bed_id}"},
                    "effectiveDateTime": now_iso,
                    "valueQuantity": {"value": patient.hr, "unit": "beats/minute", "system": "http://unitsofmeasure.org", "code": "/min"}
                }
            },
            {
                "fullUrl": f"urn:uuid:observation-spo2-{patient.bed_id}",
                "resource": {
                    "resourceType": "Observation",
                    "status": "final",
                    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
                    "code": {"coding": [{"system": "http://loinc.org", "code": "2708-6", "display": "Oxygen saturation in Arterial blood"}]},
                    "subject": {"reference": f"Patient/{patient.bed_id}"},
                    "effectiveDateTime": now_iso,
                    "valueQuantity": {"value": patient.spo2, "unit": "%", "system": "http://unitsofmeasure.org", "code": "%"}
                }
            },
            {
                "fullUrl": f"urn:uuid:observation-bp-{patient.bed_id}",
                "resource": {
                    "resourceType": "Observation",
                    "status": "final",
                    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
                    "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
                    "subject": {"reference": f"Patient/{patient.bed_id}"},
                    "effectiveDateTime": now_iso,
                    "component": [
                        {"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]}, "valueQuantity": {"value": patient.systolic, "unit": "mmHg"}},
                        {"code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]}, "valueQuantity": {"value": patient.diastolic, "unit": "mmHg"}}
                    ]
                }
            }
        ]
    }
    return jsonify(bundle)

@app.route('/api/crisis_sim', methods=['POST'])
def crisis_sim():
    """Live interactive clinical crisis drill simulator for judges."""
    global active_bed_id
    data = request.get_json() or {}
    mode = data.get("mode", "stabilize")
    patient = Patient.query.get(active_bed_id)
    if not patient: return jsonify({"status": "error"}), 404

    if mode == "vent_disconnect":
        patient.spo2 = 81
        patient.resp_rate = 34
        patient.hr = 132
        patient.status = "Critical (Apnea/Desat)"
        patient.alert_level = "critical"
        label = "CRITICAL DRILL: Ventilator Circuit Disconnect (SpO2 81%, RR 34)"
    elif mode == "vtach":
        patient.hr = 175
        patient.systolic = 85
        patient.diastolic = 50
        patient.status = "Cardiac Emergency (V-Tach)"
        patient.alert_level = "critical"
        label = "CRITICAL DRILL: Ventricular Tachycardia (HR 175 bpm, Hypotension)"
    elif mode == "septic_shock":
        patient.hr = 128
        patient.systolic = 78
        patient.diastolic = 44
        patient.resp_rate = 28
        patient.status = "Decompensated Septic Shock"
        patient.alert_level = "critical"
        label = "CRITICAL DRILL: Severe Septic Shock Collapse (MAP < 55 mmHg)"
    else:
        patient.hr = 74
        patient.spo2 = 99
        patient.systolic = 120
        patient.diastolic = 80
        patient.resp_rate = 15
        patient.status = "Stable (Restored)"
        patient.alert_level = "normal"
        label = "Patient Resuscitated: Normal Baseline Vitals Restored"

    event = TriageEvent(
        bed_id=active_bed_id, patient_name=patient.name, key="CRISIS_DRILL",
        region="Crisis Simulator", label="Emergency Drill",
        phrase=label, urgency="critical" if mode != "stabilize" else "normal",
        pain=patient.pain, timestamp=datetime.now().strftime("%I:%M:%S %p"),
        source="Crisis Simulator"
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({"status": "success", "mode": mode, "label": label})

@app.route('/api/trends', methods=['GET'])
def get_trends():
    global active_bed_id
    patient = Patient.query.get(active_bed_id)
    now = datetime.now()
    labels, hr_data, spo2_data, map_data = [], [], [], []

    base_hr = patient.hr if patient else 75
    base_spo2 = patient.spo2 if patient else 98
    base_map = 90

    for i in range(12, 0, -1):
        t = now - timedelta(hours=i)
        labels.append(t.strftime("%H:00"))
        hr_data.append(int(base_hr + random.randint(-6, 8)))
        spo2_data.append(int(min(100, max(88, base_spo2 + random.randint(-3, 2)))))
        map_data.append(int(base_map + random.randint(-4, 6)))

    labels.append("Now")
    hr_data.append(patient.hr if patient else 75)
    spo2_data.append(patient.spo2 if patient else 98)
    map_data.append(round(patient.diastolic + (patient.systolic - patient.diastolic) / 3, 1) if patient else 90)

    return jsonify({
        "bed_id": active_bed_id, "labels": labels,
        "hr": hr_data, "spo2": spo2_data, "map": map_data
    })

@app.route('/api/switch_bed', methods=['POST'])
def switch_bed():
    global active_bed_id
    data = request.get_json() or {}
    new_bed = data.get("bed_id", "")
    if Patient.query.get(new_bed):
        active_bed_id = new_bed
        return jsonify({"status": "success", "active_bed_id": active_bed_id})
    return jsonify({"status": "error"}), 404

@app.route('/api/trigger', methods=['POST'])
def trigger_action():
    global active_bed_id
    data = request.get_json() or {}
    key = data.get("key", "")
    pain = int(data.get("pain", 0))
    body_region = data.get("body_region", "General")
    lang = data.get("lang", "en")

    patient = Patient.query.get(active_bed_id)
    if not patient: return jsonify({"status": "error"}), 404

    patient.pain = pain
    patient.body_part = body_region

    if key in CLINICAL_TRIGGERS:
        action = CLINICAL_TRIGGERS[key]
        patient.alert_level = action["urgency"]
        patient.status = "Critical" if action["urgency"] == "critical" else "Attention"

        region_name = BODY_REGIONS.get(body_region, "General Bedside")
        phrase = action["phrase"].get(lang, action["phrase"]["en"])
        label_text = action["label"].get(lang, action["label"]["en"])

        full_audit = f"[{region_name}] {phrase} (Pain: {pain}/10)"

        event = TriageEvent(
            bed_id=active_bed_id, patient_name=patient.name, key=key,
            region=region_name, label=label_text, phrase=full_audit,
            urgency=action["urgency"], pain=pain,
            timestamp=datetime.now().strftime("%I:%M:%S %p"),
            source=f"Bedside Express ({active_bed_id})"
        )
        db.session.add(event)
        db.session.commit()
        return jsonify({"status": "success", "phrase": phrase, "urgency": action["urgency"]})
    return jsonify({"status": "error"}), 400

@app.route('/api/doctor_verify_pin', methods=['POST'])
def doctor_verify_pin():
    data = request.get_json() or {}
    pin = data.get("pin", "").strip()
    if pin == CLINICAL_ACCESS_PIN:
        return jsonify({"status": "authorized"}), 200

    patient = Patient.query.get(active_bed_id)
    event = TriageEvent(
        bed_id=active_bed_id, patient_name=patient.name if patient else "Unknown",
        key="SECURITY_WARNING", region="Security", label="Passcode Violation",
        phrase="Unauthorized attempt to access Attending Physician Portal with invalid PIN.",
        urgency="critical", pain=0, timestamp=datetime.now().strftime("%I:%M:%S %p"),
        source="Security Gate"
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({"status": "unauthorized"}), 403

@app.route('/api/doctor_update_chart', methods=['POST'])
def doctor_update_chart():
    global active_bed_id
    data = request.get_json() or {}
    pin = data.get("pin", "").strip()
    if pin != CLINICAL_ACCESS_PIN:
        return jsonify({"status": "unauthorized"}), 403

    patient = Patient.query.get(active_bed_id)
    if not patient: return jsonify({"status": "error"}), 404

    new_rx = data.get("new_prescription", "").strip().lower()
    if new_rx:
        patient_allergy = patient.allergies.lower()
        for class_name, drug_list in ALLERGY_CONFLICTS.items():
            if class_name in patient_allergy:
                for drug in drug_list:
                    if drug in new_rx:
                        return jsonify({
                            "status": "contraindication",
                            "message": f"CRITICAL CONTRAINDICATION: Patient has documented allergy '{patient.allergies}'. The prescribed agent '{new_rx.upper()}' belongs to this cross-reactive drug class. Order blocked."
                        }), 400

    if data.get("diagnosis"): patient.diagnosis = data["diagnosis"].strip()
    if data.get("attending_dr"): patient.attending_dr = data["attending_dr"].strip()
    if data.get("diet"): patient.diet = data["diet"].strip()
    if data.get("allergies"): patient.allergies = data["allergies"].strip()
    if data.get("status"): patient.status = data["status"].strip()

    if new_rx:
        existing = [x.strip() for x in patient.prescriptions.split(";") if x.strip()]
        existing.append(data.get("new_prescription").strip())
        patient.prescriptions = ";".join(existing)

    doctor_note = data.get("doctor_note", "").strip()
    event = TriageEvent(
        bed_id=active_bed_id, patient_name=patient.name, key="EHR_CHART_UPDATE",
        region="Clinical EHR", label="Physician Modification",
        phrase=f"Verified Physician ({patient.attending_dr}) modified record. Note: {doctor_note or 'Updated orders'}",
        urgency="normal", pain=patient.pain, timestamp=datetime.now().strftime("%I:%M:%S %p"),
        source="Authenticated MD Portal"
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/staff_reply', methods=['POST'])
def staff_reply():
    global active_bed_id
    data = request.get_json() or {}
    msg = data.get("message", "").strip()

    patient = Patient.query.get(active_bed_id)
    if msg and patient:
        patient.alert_level = "normal"
        patient.status = "Monitored"
        event = TriageEvent(
            bed_id=active_bed_id, patient_name=patient.name, key="STAFF_DISPATCH",
            region="Intercom", label="Staff Broadcast", phrase=msg,
            urgency="normal", pain=patient.pain,
            timestamp=datetime.now().strftime("%I:%M:%S %p"),
            source="Central Nurse Station"
        )
        db.session.add(event)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route('/api/clear_alert', methods=['POST'])
def clear_alert():
    global active_bed_id
    patient = Patient.query.get(active_bed_id)
    if patient:
        patient.alert_level = "normal"
        patient.status = "Stable"
        db.session.commit()
    return jsonify({"status": "cleared"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)