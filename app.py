from flask import Flask, render_template, request, jsonify
import os
import tempfile
import json
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
import openai
import datetime
import sqlite3
import numpy as np
import re

# OpenAI API key from environment variable (Vercel)
openai.api_key = os.environ.get('OPENAI_API_KEY', '')

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Database setup (using temporary database for web app)
DB_PATH = os.path.join(tempfile.gettempdir(), "safety_reports.db")
EMBED_MODEL = "text-embedding-3-large"

SEVERITY_OPTIONS = ["Minor", "Moderate", "Major", "Critical"]
PROB_OPTIONS = ["Rare", "Unlikely", "Possible", "Likely", "Frequent"]

# Transport Canada (CADORS/SMS) Occurrence List
OCCURRENCE_LIST = [
    "Accident - crash", "Aerodrome - foreign authorities involved", "Aerodrome - labour action",
    "Aerodrome - operations", "Aerodrome - other", "Aerodrome - power failure",
    "Aerodrome - runway or taxiway surface condition", "Aerodrome - visual aids", "Aerodrome noise",
    "Aerodrome property - death/injury", "Aerodrome, runway or taxiway shutdown",
    "Aircraft incident - conflict - unsafe operation", "Aircraft incident - fuel - other",
    "Aircraft incident - minor damage", "Aircraft navigation/communication equipment", "Airframe failure",
    "Airspeed Limitations - Deviation from CARs", "Alleged Canadian Aviation Regulations (CARs) infraction",
    "Animal strike (or risk of collision with animal)", "ATM - ILS irregularity",
    "ATM - inaccurate aeronautical information", "ATM - NAVAIDS/radar", "ATM - operations", "ATM - other",
    "ATM - weather observation systems", "ATS operating irregularity", "Bird presence", "Bird strike",
    "Blown tire/wheel failure", "Blue ice", "Brakes - failure", "Brakes - frozen", "Brakes - other",
    "Brakes - overheated", "Brakes", "Class F airspace violation", "Collision midair",
    "Collision on ground with aircraft", "Collision on ground with person", "Collision on ground",
    "Collision with object", "Collision with terrain", "Communication error",
    "Communication navigation surveillance/air traffic system", "Conflict - IFR & VFR",
    "Conflict - loss of separation", "Conflict - near collision  (VFR or IFR)", "Conflict - potential",
    "Controlled airspace - unauthorized entry", "Crew incapacitation", "Dangerous cargo problems (on board)",
    "Dangerous goods/hazardous materials", "Declared emergency/priority", "Decompression/pressurization",
    "Disruptive passenger", "Diversion", "Door/canopy openings indications", "Electrical problem", "ELT",
    "Engine - malfunction", "Engine failure", "Engine oil problem", "Engine shut down", "Evacuation (aircraft)",
    "External load", "False indication warning", "False warning - smoke or fire",
    "Fire - aircraft (cockpit, cargo or passenger area)", "Fire - engine", "Fire/smoke (warning)",
    "Flight control systems (ailerons, rudder, rotors, flaps, main, tail)", "Flight instrument failure",
    "Flight plan – activation", "Flight plan – information", "Flight plan – route", "FOD (foreign object debris)",
    "Forced landing", "Fuel - contamination", "Fuel - dumping", "Fuel - exhaustion", "Fuel - incorrect fuel",
    "Fuel - leak", "Fuel - low/declared minimum", "Fuel - other", "Fuel - spill", "Fuel - starvation",
    "Fuel management", "GPWS/TAWS alert", "Ground handling services", "Hard landing", "Hydraulic problem",
    "IFR operations below minimum", "Incursion - manoeuvring area", "Incursion - runway - aircraft",
    "Incursion - runway - animal", "Incursion - runway - pedestrian", "Incursion - runway - vehicle",
    "Landing gear - incorrect configuration", "Landing gear", "Landing in proximity of the intended surface",
    "Laser interference", "Loss of control - inflight", "Loss of control - on ground", "Loss of power",
    "Mechanical/technical malfunction of aircraft - other", "Medical emergency", "Missing aircraft",
    "Natural disaster (environment)", "Navigation assistance", "Navigation error", "Nose over",
    "Object dropped from aircraft", "Other operational incident", "Overshoot/missed approach", "Overturn",
    "Parachute-related event", "Parked aircraft damage", "Part or pieces separate from an aircraft",
    "Precautionary landing", "Propeller/rotor strike", "Public complaint", "Regulatory - other infraction",
    "Regulatory - weather infraction", "Rejected take-off", "Roll over", "Runway excursion", "SAR/comm search",
    "Security acts", "Smoke/fumes - aircraft", "Tail strike", "Take-off without clearance", "TCAS alert",
    "Transmission problem", "Wake turbulence/vortices", "Weather - clear air turbulence (CAT)/turbulence",
    "Weather - icing", "Weather - lightning", "Weather - other", "Weather - precipitation",
    "Weather - visibility", "Weather - wind shear", "Weather - wind",
    "Weather balloon, meteor, rocket, CIRVIS/UFO", "Windshield/window (aircraft)", "Wing strike", "Wire strike",
    "Regulatory - Altitude infraction", "Regulatory - 500 ft Alt infraction training",
    "School - Training manuel respect", "Carburator icing"
]

# Database functions (same as GUI version)
def db_init():
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            file_name TEXT,
            method TEXT,
            language TEXT,
            severity TEXT,
            summary TEXT,
            root_cause TEXT,
            short_term TEXT,
            long_term TEXT,
            full_markdown TEXT NOT NULL,
            embed_model TEXT,
            embed_json TEXT,
            doc_key TEXT,
            version INTEGER DEFAULT 1,
            is_current INTEGER DEFAULT 1
        )
        """)
        con.commit()
    finally:
        con.close()

def extract_text_from_pdf(pdf_path):
    with fitz.open(pdf_path) as doc:
        text = ""
        for p in doc:
            text += p.get_text()
        return text.strip()

def build_prompt(text, method, session_id, out_lang, sector_hint=True):
    lang_map = {
        "English": "Write the full analysis in clear, professional English.",
        "Français": "Rédige toute l'analyse en français professionnel et clair."
    }
    lang_line = lang_map.get(out_lang, lang_map["English"])

    aviation_line = ""
    if sector_hint:
        aviation_line = (
            "Use standard aviation terminology aligned with ICAO and Transport Canada language conventions. "
            "Keep units, acronyms, and severity labels consistent with aviation safety reporting practices. "
        )

    return f"""
You are an aviation safety analyst. Analyze the following safety report using the "{method}" method.

Session ID: {session_id}

{aviation_line}{lang_line}

Return a detailed markdown-formatted analysis with the following structure:

### Incident Summary
- Brief summary of the incident in 2-3 lines.

### Root Cause Analysis ({method})
- Explain the cause(s) of the incident using the selected method.

### Short-term Solution (7 days)
- Actionable recommendations that can be implemented within a week. Prefer checklist-like bullet points.

### Long-term Solution (30 days)
- Preventative strategies and systemic improvements. Prefer checklist-like bullet points.

### Severity Level
- Categorize severity as: Minor / Moderate / Major / Critical

Here is the full report text:
{text}
"""

def analyze_report_with_gpt(text, method, out_lang="English", session_id="001"):
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role":"user","content":build_prompt(text, method, session_id, out_lang, True)}],
            max_tokens=1200
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Error analyzing report: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_report():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Check file size (16MB limit)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 16 * 1024 * 1024:  # 16MB
            return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 400
        
        if file_size == 0:
            return jsonify({'error': 'File is empty'}), 400
        
        method = request.form.get('method', 'Five Whys')
        language = request.form.get('language', 'English')
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_path)
        
        try:
            # Extract text from PDF
            text = extract_text_from_pdf(temp_path)
            
            if not text.strip():
                return jsonify({'error': 'No text found in PDF. Please check if the PDF contains readable text or is not password-protected.'}), 400
            
            if len(text.strip()) < 50:
                return jsonify({'error': 'PDF contains very little text. Please ensure the PDF has sufficient content for analysis.'}), 400
            
            # Analyze with GPT
            result = analyze_report_with_gpt(text, method, language)
            
            # Save to database
            try:
                db_insert_report(filename, method, language, result)
            except Exception as db_error:
                print(f"Database error: {db_error}")
            
            return jsonify({
                'success': True,
                'result': result,
                'filename': filename,
                'method': method,
                'language': language
            })
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/classify', methods=['POST'])
def auto_classify():
    try:
        data = request.get_json()
        markdown_text = data.get('text', '')
        
        if not markdown_text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Simple classification logic (can be enhanced with GPT)
        text_lower = markdown_text.lower()
        
        occurrence = "Other operational incident"
        if "runway excursion" in text_lower or "veer" in text_lower:
            occurrence = "Runway excursion"
        elif "bird" in text_lower:
            occurrence = "Bird strike"
        elif "engine failure" in text_lower or "engine shut down" in text_lower:
            occurrence = "Engine failure"
        elif "hard landing" in text_lower:
            occurrence = "Hard landing"
        
        severity = "Moderate"
        if any(x in text_lower for x in ["evacuat", "injur", "fire"]):
            severity = "Major"
        
        probability = "Possible"
        
        return jsonify({
            'success': True,
            'classification': {
                'occurrence': occurrence,
                'severity': severity,
                'probability': probability
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Initialize database on startup
db_init()

if __name__ == '__main__':
    app.run(debug=True)
