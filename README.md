# GestureBridge — Advanced Clinical Telehealth Suite

A real-time, hospital-grade telehealth and assistive clinical telemetry platform built for non-verbal, motor-restricted, and ICU bedside patients.

---

## 🌟 Key Features

* **Dual-Trace Hardware Oscilloscope:** Continuous synchronized Lead-II Cardiac ECG (Green) and Arterial Photoplethysmograph (PPG, Cyan) with dicrotic notch pulse emulation.
* **Multilingual Audio & UI (EN / हिन्दी / मराठी):** Full Devanagari regional support. Translates the UI instantly and synthesizes spoken alerts in authentic Indian regional voices (`hi-IN`, `mr-IN`).
* **Clinical Decision Support (CDS) Safety:** Drug-allergy cross-reactivity engine that flags and blocks contraindications (e.g., Penicillin/Sulfa cross-sensitivities) when prescribing.
* **National Early Warning Score (NEWS2) & AI Sentinel:** Real-time physiological deterioration prediction correlating Mean Arterial Pressure (MAP), respiratory rate, and heart rate.
* **Multi-Bed Central ICU Matrix:** Charge nurse command view overseeing multiple ward beds concurrently with instant drill-down bedside express control.
* **Standards-Compliant HL7 FHIR R4 Export:** Export patient observations and vitals codified under international LOINC standards (`8867-4`, `2708-6`, `85354-9`).
* **SBAR Handover Reporting:** Generates print-ready clinical shift handover documents (Situation, Background, Assessment, Recommendation).
* **Clinical Crisis Simulator:** Interactive emergency drill triggers (Ventilator Apnea, V-Tach Arrhythmia, Septic Shock, and Baseline Stabilization).

---

## 🛠 Tech Stack

* **Backend:** Python, Flask, SQLAlchemy, SQLite
* **Frontend:** HTML5, Tailwind CSS, JavaScript (ES6+)
* **Data Visualization:** HTML5 Canvas API (dual oscilloscopes), Chart.js (12-hour trends)
* **Audio & Assistive Interfaces:** Web Speech API, Web Audio API, Single-Switch Auto-Scanning

---

## 🚀 Local Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/shrutibawankule15/GestureBridge.git](https://github.com/shrutibawankule15/GestureBridge.git)
   cd GestureBridge
