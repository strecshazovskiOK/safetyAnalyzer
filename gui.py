# gui.py

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import fitz  # PyMuPDF
import openai
import os, re, json, datetime, sqlite3
import numpy as np
import threading

from config import API_KEY
openai.api_key = API_KEY

# ---- Optional deps for export ----
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import cm
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    PANDAS_AVAILABLE = False


# =========================
# Globals
# =========================
selected_file_path = ""
latest_feedback_result = None
original_report_text = None

save_updated_btn = None
search_btn = None

DB_PATH = os.path.join(os.path.dirname(__file__), "safety_reports.db")
EMBED_MODEL = "text-embedding-3-large"

SEVERITY_OPTIONS = ["Minor", "Moderate", "Major", "Critical"]
PROB_OPTIONS     = ["Rare", "Unlikely", "Possible", "Likely", "Frequent"]

# --- Transport Canada (CADORS/SMS) Occurrence List (tam) ---
OCCURRENCE_LIST = [
    "Accident - crash","Aerodrome - foreign authorities involved","Aerodrome - labour action",
    "Aerodrome - operations","Aerodrome - other","Aerodrome - power failure",
    "Aerodrome - runway or taxiway surface condition","Aerodrome - visual aids","Aerodrome noise",
    "Aerodrome property - death/injury","Aerodrome, runway or taxiway shutdown",
    "Aircraft incident - conflict - unsafe operation","Aircraft incident - fuel - other",
    "Aircraft incident - minor damage","Aircraft navigation/communication equipment","Airframe failure",
    "Airspeed Limitations - Deviation from CARs","Alleged Canadian Aviation Regulations (CARs) infraction",
    "Animal strike (or risk of collision with animal)","ATM - ILS irregularity",
    "ATM - inaccurate aeronautical information","ATM - NAVAIDS/radar","ATM - operations","ATM - other",
    "ATM - weather observation systems","ATS operating irregularity","Bird presence","Bird strike",
    "Blown tire/wheel failure","Blue ice","Brakes - failure","Brakes - frozen","Brakes - other",
    "Brakes - overheated","Brakes","Class F airspace violation","Collision midair",
    "Collision on ground with aircraft","Collision on ground with person","Collision on ground",
    "Collision with object","Collision with terrain","Communication error",
    "Communication navigation surveillance/air traffic system","Conflict - IFR & VFR",
    "Conflict - loss of separation","Conflict - near collision  (VFR or IFR)","Conflict - potential",
    "Controlled airspace - unauthorized entry","Crew incapacitation","Dangerous cargo problems (on board)",
    "Dangerous goods/hazardous materials","Declared emergency/priority","Decompression/pressurization",
    "Disruptive passenger","Diversion","Door/canopy openings indications","Electrical problem","ELT",
    "Engine - malfunction","Engine failure","Engine oil problem","Engine shut down","Evacuation (aircraft)",
    "External load","False indication warning","False warning - smoke or fire",
    "Fire - aircraft (cockpit, cargo or passenger area)","Fire - engine","Fire/smoke (warning)",
    "Flight control systems (ailerons, rudder, rotors, flaps, main, tail)","Flight instrument failure",
    "Flight plan – activation","Flight plan – information","Flight plan – route","FOD (foreign object debris)",
    "Forced landing","Fuel - contamination","Fuel - dumping","Fuel - exhaustion","Fuel - incorrect fuel",
    "Fuel - leak","Fuel - low/declared minimum","Fuel - other","Fuel - spill","Fuel - starvation",
    "Fuel management","GPWS/TAWS alert","Ground handling services","Hard landing","Hydraulic problem",
    "IFR operations below minimum","Incursion - manoeuvring area","Incursion - runway - aircraft",
    "Incursion - runway - animal","Incursion - runway - pedestrian","Incursion - runway - vehicle",
    "Landing gear - incorrect configuration","Landing gear","Landing in proximity of the intended surface",
    "Laser interference","Loss of control - inflight","Loss of control - on ground","Loss of power",
    "Mechanical/technical malfunction of aircraft - other","Medical emergency","Missing aircraft",
    "Natural disaster (environment)","Navigation assistance","Navigation error","Nose over",
    "Object dropped from aircraft","Other operational incident","Overshoot/missed approach","Overturn",
    "Parachute-related event","Parked aircraft damage","Part or pieces separate from an aircraft",
    "Precautionary landing","Propeller/rotor strike","Public complaint","Regulatory - other infraction",
    "Regulatory - weather infraction","Rejected take-off","Roll over","Runway excursion","SAR/comm search",
    "Security acts","Smoke/fumes - aircraft","Tail strike","Take-off without clearance","TCAS alert",
    "Transmission problem","Wake turbulence/vortices","Weather - clear air turbulence (CAT)/turbulence",
    "Weather - icing","Weather - lightning","Weather - other","Weather - precipitation",
    "Weather - visibility","Weather - wind shear","Weather - wind",
    "Weather balloon, meteor, rocket, CIRVIS/UFO","Windshield/window (aircraft)","Wing strike","Wire strike",
    "Regulatory - Altitude infraction","Regulatory - 500 ft Alt infraction training",
    "School - Training manuel respect","Carburator icing"
]


# =========================
# DB helpers (latest-only per doc_key)
# =========================
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

def db_migrate_add_columns():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(reports)")}
        for name, typ in [
            ("summary","TEXT"), ("root_cause","TEXT"), ("short_term","TEXT"),
            ("long_term","TEXT"), ("doc_key","TEXT"), ("version","INTEGER"),
            ("is_current","INTEGER")
        ]:
            if name not in cols:
                con.execute(f"ALTER TABLE reports ADD COLUMN {name} {typ}")
        con.commit()
    finally:
        con.close()

def compute_doc_key(file_name: str) -> str:
    base = os.path.basename(file_name or "").strip()
    for tag in [" (updated)", " (final)"]:
        if base.lower().endswith(tag):
            base = base[: -len(tag)]
    return base

def get_clean_body_from_output(text: str) -> str:
    lines = text.splitlines()
    if lines and ("📄" in lines[0] or "Method:" in lines[0] or "Language:" in lines[0]):
        return "\n".join(lines[1:]).strip()
    return text.strip()

def extract_sections(md_text: str):
    sections = {"summary":"", "root":"", "short7":"", "long30":"", "severity":""}
    current = None
    for line in md_text.splitlines():
        l = line.strip().lower()
        if l.startswith("### incident summary"):        current = "summary";  continue
        if l.startswith("### root cause analysis"):      current = "root";     continue
        if l.startswith("### short-term solution"):      current = "short7";   continue
        if l.startswith("### long-term solution"):       current = "long30";   continue
        if l.startswith("### severity"):                 current = "severity"; continue
        if current:
            sections[current] += line + "\n"
    for k in sections: sections[k] = sections[k].strip()
    return sections

def compose_similarity_text(md_text: str) -> str:
    secs = extract_sections(md_text)
    parts = []
    if secs.get("summary"): parts.append(secs["summary"])
    if secs.get("short7"):  parts.append(secs["short7"])
    if secs.get("long30"):  parts.append(secs["long30"])
    return ("\n\n".join(parts).strip()) or get_clean_body_from_output(md_text)

def get_embedding(text: str) -> np.ndarray:
    try:
        resp = openai.Embedding.create(model=EMBED_MODEL, input=[text])
        vec = np.array(resp["data"][0]["embedding"], dtype="float32")
        n = np.linalg.norm(vec) + 1e-9
        return vec / n
    except Exception as e:
        print("Embedding error:", e)
        return np.empty((0,), dtype="float32")

def db_insert_report(file_name, method, language, full_markdown):
    db_init(); db_migrate_add_columns()
    body = get_clean_body_from_output(full_markdown)
    secs = extract_sections(body)

    embed_text = compose_similarity_text(body)
    vec = get_embedding(embed_text)
    embed_json = json.dumps(vec.tolist()) if vec.size else None

    doc_key = compute_doc_key(file_name)
    con = sqlite3.connect(DB_PATH)
    try:
        row = con.execute("SELECT MAX(version) FROM reports WHERE doc_key=?", (doc_key,)).fetchone()
        next_ver = (row[0] or 0) + 1

        con.execute("DELETE FROM reports WHERE doc_key=?", (doc_key,))
        con.execute("""
            INSERT INTO reports
              (created_at,file_name,method,language,severity,summary,root_cause,short_term,long_term,
               full_markdown,embed_model,embed_json,doc_key,version,is_current)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
        """, (
            datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            file_name, method, language, secs.get("severity",""), secs.get("summary",""),
            secs.get("root",""), secs.get("short7",""), secs.get("long30",""),
            body, EMBED_MODEL, embed_json, doc_key, next_ver
        ))
        con.commit()
    finally:
        con.close()

def db_fetch_all():
    db_init(); db_migrate_add_columns()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("""
            SELECT id,created_at,file_name,method,language,severity,summary,root_cause,short_term,long_term,
                   full_markdown,embed_json,doc_key,version,is_current
            FROM reports WHERE IFNULL(is_current,1)=1
        """).fetchall()
        out = []
        for r in rows:
            v = np.array(json.loads(r["embed_json"])) if r["embed_json"] else np.empty((0,), dtype="float32")
            out.append({
                "id": r["id"], "created_at": r["created_at"], "file_name": r["file_name"],
                "method": r["method"], "language": r["language"], "severity": r["severity"],
                "summary": r["summary"], "root_cause": r["root_cause"], "short_term": r["short_term"],
                "long_term": r["long_term"], "full_markdown": r["full_markdown"], "vec": v,
                "doc_key": r["doc_key"], "version": r["version"], "is_current": r["is_current"]
            })
        return out
    finally:
        con.close()

def search_similar_in_db(query_markdown: str, top_k: int = 5):
    q_vec = get_embedding(compose_similarity_text(query_markdown)[:4000])
    if q_vec.size == 0:
        return []
    all_items = db_fetch_all()
    scored = []
    for it in all_items:
        if it["vec"].size == 0: 
            continue
        scored.append((float(np.dot(q_vec, it["vec"])), it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]
# =========================
# GPT: analysis & rationale
# =========================
def build_prompt(text, method, session_id, out_lang, sector_hint=True):
    lang_map = {
        "English": "Write the full analysis in clear, professional English.",
        "Français": "Rédige toute l’analyse en français professionnel et clair."
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
    resp = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role":"user","content":build_prompt(text, method, session_id, out_lang, True)}],
        max_tokens=1200
    )
    return resp.choices[0].message.content.strip()

def explain_similarity_gpt(query_md: str, cand_md: str, out_lang: str = "English"):
    secs_q = extract_sections(query_md)
    secs_c = extract_sections(cand_md)

    def pick(s): return (s or "").strip()
    q_text = "\n".join(filter(None,[pick(secs_q.get("summary")),pick(secs_q.get("short7")),pick(secs_q.get("long30"))]))
    c_text = "\n".join(filter(None,[pick(secs_c.get("summary")),pick(secs_c.get("short7")),pick(secs_c.get("long30"))]))

    lang_hint = "Write the answer in clear, professional English." if out_lang=="English" else \
                "Répondez en français clair et professionnel."

    prompt = f"""
You are an aviation safety analyst. Compare two safety analyses (query vs. candidate),
considering ONLY: Incident Summary, 7-day actions, 30-day actions.

Return a very short justification (max 2 sentences) of why they are similar or not,
focused on concrete overlaps (e.g., missing POH, checklist not done, dispatch/document control, training gaps).
Also return a confidence from 0.0 to 1.0 reflecting how strong the overlap is.

{lang_hint}
Respond in strict JSON with keys: why (string), confidence (number).

# QUERY
{q_text}

# CANDIDATE
{c_text}
"""
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role":"user","content":prompt}],
            max_tokens=180,
            temperature=0.2
        )
        raw = resp.choices[0].message.content.strip()
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        why  = str(data.get("why","")).strip()
        conf = float(data.get("confidence",0.0))
        return {"why":why, "confidence":max(0.0,min(1.0,conf))}
    except Exception:
        return {"why":"", "confidence":0.0}


# =========================
# Classification helpers (apply to report)
# =========================
def _remove_or_replace_section(md: str, title: str, new_block: str) -> str:
    """### Title ile başlayan bölümü (varsa) kaldırıp new_block'ı ekler; yoksa sona ekler."""
    lines = md.splitlines()
    out, i, n = [], 0, len(lines)
    found = False
    while i < n:
        if lines[i].strip().lower().startswith(f"### {title.lower()}"):
            found = True
            # mevcut blok sonuna atla
            i += 1
            while i < n and not lines[i].strip().startswith("### "):
                i += 1
            # yeni bloğu ekle
            out.append(f"### {title}")
            out.extend(new_block.splitlines())
            continue
        out.append(lines[i]); i += 1
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append(f"### {title}")
        out.extend(new_block.splitlines())
    return "\n".join(out)

def apply_classification():
    """UI'daki Occurrence + Severity + Probability değerlerini rapora işler/yeniler."""
    md = report_output.get("1.0", tk.END).strip()
    if not md:
        messagebox.showerror("Apply", "Please run an analysis first.")
        return
    body = get_clean_body_from_output(md)

    occ = occurrence_var.get().strip()
    sev = sev_var.get().strip()
    prob= prob_var.get().strip()

    class_block = f"- **Occurrence**: {occ}"
    risk_block  = f"- **Risk Severity**: {sev}\n- **Risk Probability**: {prob}"

    body = _remove_or_replace_section(body, "Classification (TC / SMS)", class_block)
    body = _remove_or_replace_section(body, "Risk Assessment", risk_block)

    # Başlıktaki meta'yı koruyarak yaz
    header_line = ""
    lines = md.splitlines()
    if lines and ("📄" in lines[0] or "Method:" in lines[0]):
        header_line = lines[0]

    report_output.configure(state="normal")
    report_output.delete("1.0", tk.END)
    if header_line:
        report_output.insert(tk.END, header_line + "\n\n")
    report_output.insert(tk.END, body)
    set_status("Classification applied to report.")


# =========================
# Auto-Classify (GPT + fallback)
# =========================
def auto_classify():
    md = report_output.get("1.0", tk.END).strip()
    if not md:
        messagebox.showerror("Auto-Classify", "Please run an analysis first.")
        return

    body = get_clean_body_from_output(md)
    occ_list = "\n".join([f"- {name}" for name in OCCURRENCE_LIST])
    prompt = f"""
You are an aviation safety analyst. Read the markdown below and pick:
1) exactly ONE occurrence from this controlled list:
{occ_list}

2) risk severity: one of [Minor, Moderate, Major, Critical]
3) risk probability: one of [Rare, Unlikely, Possible, Likely, Frequent]

Return STRICT JSON with keys: occurrence, severity, probability.

Markdown to read:
{body}
"""
    picked = None
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role":"user","content":prompt}],
            max_tokens=180,
            temperature=0.2
        )
        raw = resp.choices[0].message.content.strip()
        m = re.search(r"\{.*\}", raw, re.S)
        picked = json.loads(m.group(0) if m else raw)
    except Exception as e:
        print("auto_classify GPT error:", e)
        picked = None

    # Fallback basit
    if not picked:
        t = body.lower()
        occ = "Other operational incident"
        if "runway excursion" in t or "veer" in t:
            occ = "Runway excursion"
        elif "bird" in t:
            occ = "Bird strike"
        elif "engine failure" in t or "engine shut down" in t:
            occ = "Engine failure"
        elif "hard landing" in t:
            occ = "Hard landing"
        sev = "Moderate"
        if any(x in t for x in ["evacuat","injur","fire"]): sev = "Major"
        prob = "Possible"
        picked = {"occurrence":occ,"severity":sev,"probability":prob}

    occ_value = picked.get("occurrence","").strip()
    sev_value = picked.get("severity","").strip().title()
    prob_value= picked.get("probability","").strip().title()

    if occ_value in OCCURRENCE_LIST: occurrence_var.set(occ_value)
    if sev_value in SEVERITY_OPTIONS:  sev_var.set(sev_value)
    if prob_value in PROB_OPTIONS:     prob_var.set(prob_value)

    apply_classification()
    messagebox.showinfo("Auto-Classify",
        f"Done.\nOccurrence: {occurrence_var.get()}\nSeverity: {sev_var.get()}\nProbability: {prob_var.get()}")
# =========================
# UI Action Handlers
# =========================
def set_status(text):
    status_var.set(text)
    status_bar.update_idletasks()

def extract_text_from_pdf(pdf_path):
    with fitz.open(pdf_path) as doc:
        text = ""
        for p in doc:
            text += p.get_text()
        return text.strip()

def run_analysis():
    if not selected_file_path:
        messagebox.showerror("Error", "Please select a PDF file first.")
        return
    method   = method_var.get()
    out_lang = lang_var.get()
    text     = extract_text_from_pdf(selected_file_path)

    report_output.configure(state="normal")
    report_output.delete("1.0", tk.END)
    report_output.insert(tk.END, "⏳ Running analysis. Please wait...\n")
    set_status("Analyzing report...")

    def _work():
        global original_report_text
        result = analyze_report_with_gpt(text, method, out_lang=out_lang)
        original_report_text = result.strip()

        header = f"📄 {os.path.basename(selected_file_path)}  |  🧭 Method: {method}  |  🌐 Language: {out_lang}\n\n"
        report_output.configure(state="normal")
        report_output.delete("1.0", tk.END)
        report_output.insert(tk.END, header + result)
        report_output.see(tk.END)
        set_status("Analysis completed.")

        try:
            db_insert_report(
                file_name=os.path.basename(selected_file_path),
                method=method, language=out_lang, full_markdown=result
            )
            set_status("Analysis completed. Saved to local DB.")
        except Exception as e:
            set_status(f"Saved output (DB error: {e})")
    threading.Thread(target=_work, daemon=True).start()

def select_pdf_file():
    global selected_file_path
    path = filedialog.askopenfilename(filetypes=[("PDF files","*.pdf")])
    if path:
        selected_file_path = path
        selected_label_var.set(f"Selected: {os.path.basename(path)}")
        set_status("File selected.")

def send_feedback():
    fb = feedback_text.get("1.0", tk.END).strip()
    if not fb:
        messagebox.showerror("Error", "Please enter feedback before submitting.")
        return
    if not selected_file_path:
        messagebox.showerror("Error", "Please select a PDF file first.")
        return

    report_output.insert(tk.END, "\n\n🤖 AI is working on a great report...\n")
    report_output.see(tk.END)
    set_status("Processing feedback...")

    def _work():
        global latest_feedback_result
        text = extract_text_from_pdf(selected_file_path)
        method = method_var.get();  out_lang = lang_var.get()
        base_prompt = build_prompt(text, method, session_id="FEEDBACK", out_lang=out_lang, sector_hint=True)
        prompt = f"""{base_prompt}

*** Additional Reviewer Feedback to incorporate: ***
{fb}
"""
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role":"user","content":prompt}],
                max_tokens=1500
            )
            latest_feedback_result = resp.choices[0].message.content.strip()
            report_output.insert(tk.END, "\n\n✅ Thank you for your feedback!\n\n📄 Click 'Add to Report' to append the updated version.\n")
            set_status("Feedback processed. Updated version available.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            set_status("Feedback failed.")
    threading.Thread(target=_work, daemon=True).start()

def add_to_report():
    if not latest_feedback_result:
        messagebox.showerror("Error", "No updated report available. Please send feedback first.")
        return
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    report_output.insert(tk.END, "\n" + "."*80 + f"\n\n🔁 Updated version ({stamp})\n\n" + latest_feedback_result + "\n")
    report_output.see(tk.END)
    set_status("Updated report appended.")

def save_updated_to_db():
    if not latest_feedback_result:
        messagebox.showerror("Save", "No updated report to save. Please send feedback first.")
        return
    try:
        db_insert_report(
            file_name=(os.path.basename(selected_file_path) if selected_file_path else "Manual") + " (final)",
            method=method_var.get(), language=lang_var.get(), full_markdown=latest_feedback_result
        )
        set_status("Updated version saved to DB.")
        messagebox.showinfo("Saved", "Updated report has been saved to the local database.")
    except Exception as e:
        messagebox.showerror("DB Error", str(e))

def search_similar_action():
    q = report_output.get("1.0", tk.END).strip()
    if not q:
        messagebox.showerror("Search", "Please run an analysis first (no text to compare).")
        return

    # self-match filtre
    first = q.splitlines()[0] if q.splitlines() else ""
    current_file = None
    if "📄" in first:
        try: current_file = first.split("📄",1)[1].split("|",1)[0].strip()
        except Exception: current_file = None
    current_key = compute_doc_key(current_file) if current_file else None

    try:
        results = search_similar_in_db(q, top_k=10)
        if current_key:
            results = [r for r in results if r[1].get("doc_key") != current_key]
        results = results[:5]
        if not results:
            messagebox.showinfo("Search", "No similar reports found in local DB.")
            return

        out_lang = lang_var.get()
        rows = []
        for score, item in results:
            exp = explain_similarity_gpt(q, item["full_markdown"], out_lang=out_lang)
            combo = 0.7*score + 0.3*exp.get("confidence",0.0)
            rows.append((combo, score, exp, item))
        rows.sort(key=lambda x: x[0], reverse=True)

        block = ["\n" + "."*80, "\n### Comparable Cases (Local DB — Summary + 7/30 days, with rationale)\n"]
        for combo, score, exp, it in rows:
            sim_pct = int(round(score * 100))
            secs = extract_sections(it["full_markdown"])
            why  = exp.get("why","").strip()
            conf_pct = int(round(exp.get("confidence",0.0)*100))
            block.append(
                f"- **{it['created_at']} — {it['file_name'] or 'local'}** "
                f"(similarity ≈ {sim_pct}%, rationale conf. {conf_pct}%)\n"
                f"  • Summary:\n{secs.get('summary','')}\n"
                f"  • 7-day:\n{secs.get('short7','')}\n"
                f"  • 30-day:\n{secs.get('long30','')}\n"
                f"  • Why similar: {why}\n"
            )
        report_output.insert(tk.END, "\n".join(block))
        report_output.see(tk.END)
        set_status("Similar cases appended.")
    except Exception as e:
        messagebox.showerror("Search error", str(e))

def parse_markdown_to_sections(md_text):
    lines = md_text.splitlines()
    sections, current_title, buf = [], "Report", []
    for ln in lines:
        if ln.startswith("### "):
            if buf: sections.append((current_title, "\n".join(buf).strip())); buf=[]
            current_title = ln[4:].strip()
        else:
            buf.append(ln)
    if buf: sections.append((current_title, "\n".join(buf).strip()))
    return sections

def export_pdf():
    output_text = report_output.get("1.0", tk.END).strip()
    if not output_text:
        messagebox.showerror("Error", "Nothing to export."); return
    if not REPORTLAB_AVAILABLE:
        messagebox.showwarning("Missing dependency","Install reportlab:  pip install reportlab"); return

    path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                        filetypes=[("PDF","*.pdf")],
                                        initialfile="Safety_Report.pdf")
    if not path: return
    try:
        doc = SimpleDocTemplate(path, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story  = []

        story.append(Paragraph("Safety Report", styles["Title"]))
        story.append(Spacer(1, 0.4*cm))
        meta = f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Source: {os.path.basename(selected_file_path) if selected_file_path else '-'}"
        story.append(Paragraph(meta, styles["Normal"]))
        story.append(Spacer(1, 0.5*cm))

        body = output_text
        lines = body.splitlines()
        if lines and ("📄" in lines[0] or "Method:" in lines[0]): body = "\n".join(lines[1:]).strip()

        secs = parse_markdown_to_sections(body) or [("Report", body)]
        for head, content in secs:
            story.append(Paragraph(head, styles["Heading2"]))
            story.append(Spacer(1, 0.2*cm))
            for para in content.split("\n\n"):
                story.append(Paragraph(para.replace("\n", "<br/>"), styles["BodyText"]))
                story.append(Spacer(1, 0.2*cm))
            story.append(Spacer(1, 0.3*cm))
        doc.build(story)
        set_status(f"Exported PDF: {os.path.basename(path)}")
        messagebox.showinfo("Export", f"PDF exported:\n{path}")
    except Exception as e:
        messagebox.showerror("Export error", str(e))

def export_excel():
    output_text = report_output.get("1.0", tk.END).strip()
    if not output_text:
        messagebox.showerror("Error", "Nothing to export."); return
    path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                        filetypes=[("Excel Workbook","*.xlsx"),("CSV","*.csv")],
                                        initialfile="Safety_Report.xlsx")
    if not path: return
    try:
        body_lines = output_text.splitlines()
        output_text_clean = "\n".join(body_lines[1:]).strip() if (body_lines and ("📄" in body_lines[0] or "Method:" in body_lines[0])) else output_text
        sections = parse_markdown_to_sections(output_text_clean)

        if path.lower().endswith(".csv"):
            import csv
            with open(path,"w",newline="",encoding="utf-8") as f:
                w = csv.writer(f); w.writerow(["Section","Content"])
                if not sections: w.writerow(["Report", output_text_clean])
                else:
                    for h,c in sections: w.writerow([h,c])
            set_status(f"Exported CSV: {os.path.basename(path)}")
            messagebox.showinfo("Export", f"CSV exported:\n{path}")
            return

        if not PANDAS_AVAILABLE:
            messagebox.showwarning("Missing dependency",
                "For Excel export: pip install pandas openpyxl\n\nOr choose CSV in the dialog.")
            return

        rows = [{"Section":h,"Content":c} for (h,c) in (sections or [("Report",output_text_clean)])]
        df = pd.DataFrame(rows)
        try:
            with pd.ExcelWriter(path, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="Report")
        except Exception:
            with pd.ExcelWriter(path, engine="xlsxwriter") as writer: df.to_excel(writer, index=False, sheet_name="Report")
        set_status(f"Exported Excel: {os.path.basename(path)}")
        messagebox.showinfo("Export", f"Excel exported:\n{path}")
    except Exception as e:
        messagebox.showerror("Export error", str(e))
# =========================
# UI Setup (Theme + Layout)
# =========================
root = tk.Tk()
root.title("Safety Report Analyzer")
root.geometry("1280x820")
root.minsize(1180, 720)

# Theme
BG = "#0B1220"; CARD = "#111A2B"; ACCENT = "#4F8FF7"; ACCENT_2 = "#18C29C"
DANGER = "#E74C3C"; SUCCESS = "#2ECC71"; TEXT = "#E8EEF9"; MUTED = "#99A7BD"
root.configure(bg=BG)

style = ttk.Style(); style.theme_use("clam")
style.configure("TFrame", background=BG)
style.configure("Card.TFrame", background=CARD, relief="flat")
style.configure("Header.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 22, "bold"))
style.configure("SubHeader.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 11))
style.configure("CardTitle.TLabel", background=CARD, foreground=TEXT, font=("Segoe UI", 12, "bold"))
style.configure("CardHint.TLabel", background=CARD, foreground=MUTED, font=("Segoe UI", 10))
style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=10)
style.configure("Accent.TButton", background=ACCENT, foreground="white")
style.map("Accent.TButton", background=[("active", "#3A7AE0")])
style.configure("Success.TButton", background=SUCCESS, foreground="#0B1220")
style.map("Success.TButton", background=[("active", "#28B463")])
style.configure("Danger.TButton", background=DANGER, foreground="white")
style.map("Danger.TButton", background=[("active", "#CB4335")])
style.configure("Info.TButton", background=ACCENT_2, foreground="white")
style.map("Info.TButton", background=[("active", "#16A085")])
style.configure("Combo.TCombobox", fieldbackground="#0E1730", background="#0E1730", foreground=TEXT, bordercolor="#233249")
style.map("Combo.TCombobox", fieldbackground=[("readonly","#0E1730")], foreground=[("readonly",TEXT)],
          background=[("readonly","#0E1730")], selectbackground=[("readonly",ACCENT)], selectforeground=[("readonly","white")])

# Header
header = ttk.Frame(root); header.pack(side="top", fill="x", padx=16, pady=(14, 8))
ttk.Label(header, text="🛡️ Safety Report Analyzer", style="Header.TLabel").pack(anchor="w")
ttk.Label(header, text="Analyze PDF safety reports using aviation methods and generate structured recommendations.",
          style="SubHeader.TLabel").pack(anchor="w", pady=(2, 0))

# Paned main
paned = ttk.Panedwindow(root, orient="horizontal")
paned.pack(fill="both", expand=True, padx=16, pady=8)

# LEFT — scrollable card
left_outer = ttk.Frame(paned, style="Card.TFrame")
controls_canvas = tk.Canvas(left_outer, bg=CARD, highlightthickness=0, width=460)
left_scrollbar = ttk.Scrollbar(left_outer, orient="vertical", command=controls_canvas.yview)
inner_frame = ttk.Frame(controls_canvas, style="Card.TFrame")

inner_frame.bind("<Configure>", lambda e: controls_canvas.configure(scrollregion=controls_canvas.bbox("all")))
controls_canvas.create_window((0,0), window=inner_frame, anchor="nw")
controls_canvas.configure(yscrollcommand=left_scrollbar.set)

controls_canvas.pack(side="left", fill="both", expand=True)
left_scrollbar.pack(side="right", fill="y")

# Sağ panel
right = ttk.Frame(paned, style="Card.TFrame")

paned.add(left_outer, weight=0)   # solda sabit genişlik hissi
paned.add(right,      weight=1)   # sağ taraf geniş
root.update_idletasks()
try:
    paned.sashpos(0, 480)  # sol panel ~480px
except Exception:
    pass

# --- Mouse tekerleği ile sol/sağ kaydırma rahatlığı
def _bind_wheel_to_canvas(widget):
    def _on_wheel(e):
        widget.yview_scroll(int(-1*(e.delta/120)), "units")
        return "break"
    widget.bind("<Enter>", lambda e: widget.bind_all("<MouseWheel>", _on_wheel))
    widget.bind("<Leave>", lambda e: widget.unbind_all("<MouseWheel>"))
_bind_wheel_to_canvas(controls_canvas)
# ====== Inner (left) content ======
controls = ttk.Frame(inner_frame, style="Card.TFrame"); controls.pack(fill="both", expand=True, padx=18, pady=18)
ttk.Label(controls, text="Controls", style="CardTitle.TLabel").pack(anchor="w", pady=(0,8))

# Method
method_var = tk.StringVar(value="Five Whys")
row = ttk.Frame(controls, style="Card.TFrame"); row.pack(fill="x", pady=(4,12))
ttk.Label(row, text="Analysis Method", style="CardHint.TLabel").pack(anchor="w")
ttk.Combobox(row, textvariable=method_var, state="readonly",
             values=["Five Whys","Fishbone","Bowtie","Fault Tree"],
             style="Combo.TCombobox").pack(fill="x", pady=(6,0))

# Language
lang_var = tk.StringVar(value="English")
row = ttk.Frame(controls, style="Card.TFrame"); row.pack(fill="x", pady=(4,12))
ttk.Label(row, text="Report Language", style="CardHint.TLabel").pack(anchor="w")
ttk.Combobox(row, textvariable=lang_var, state="readonly",
             values=["English","Français"], style="Combo.TCombobox").pack(fill="x", pady=(6,0))

# Classification (TC/SMS)
row = ttk.Frame(controls, style="Card.TFrame"); row.pack(fill="x", pady=(6,6))
ttk.Label(row, text="Classification (TC / SMS)", style="CardHint.TLabel").pack(anchor="w")

occurrence_var = tk.StringVar(value="Accident - crash")
occ_combo = ttk.Combobox(row, textvariable=occurrence_var, values=OCCURRENCE_LIST, state="readonly", style="Combo.TCombobox")
occ_combo.pack(fill="x", pady=(6,4))

sev_var  = tk.StringVar(value="Moderate")
prob_var = tk.StringVar(value="Possible")
ttk.Combobox(row, textvariable=sev_var, values=SEVERITY_OPTIONS, state="readonly", style="Combo.TCombobox").pack(fill="x", pady=(4,4))
ttk.Combobox(row, textvariable=prob_var, values=PROB_OPTIONS,   state="readonly", style="Combo.TCombobox").pack(fill="x", pady=(0,6))

btn_row = ttk.Frame(controls, style="Card.TFrame"); btn_row.pack(fill="x", pady=(2,10))
ttk.Button(btn_row, text="❄️  Auto-Classify",  style="Accent.TButton",  command=auto_classify).pack(side="left", expand=True, fill="x", padx=(0,8))
ttk.Button(btn_row, text="🔧  Apply to Report", style="Accent.TButton",  command=apply_classification).pack(side="left", expand=True, fill="x", padx=(8,0))

# File
row = ttk.Frame(controls, style="Card.TFrame"); row.pack(fill="x", pady=(12,6))
ttk.Label(row, text="PDF File", style="CardHint.TLabel").pack(anchor="w")
ttk.Button(row, text="📄  Select PDF File", style="Accent.TButton", command=select_pdf_file).pack(fill="x", pady=(6,6))
selected_label_var = tk.StringVar(value="No file selected")
ttk.Label(row, textvariable=selected_label_var, style="CardHint.TLabel").pack(anchor="w")

# Run
row = ttk.Frame(controls, style="Card.TFrame"); row.pack(fill="x", pady=(12,6))
ttk.Button(row, text="▶️  Run Analysis", style="Success.TButton", command=run_analysis).pack(fill="x")

# Feedback (chips yok)
row = ttk.Frame(controls, style="Card.TFrame"); row.pack(fill="x", pady=(16,6))
ttk.Label(row, text="Give Feedback (improves next analysis)", style="CardHint.TLabel").pack(anchor="w")
feedback_text = tk.Text(row, height=6, font=("Segoe UI", 11), bg="#0E1730", fg=TEXT, insertbackground=TEXT, relief="flat")
feedback_text.pack(fill="x", pady=(6,8))

btns = ttk.Frame(row, style="Card.TFrame"); btns.pack(fill="x")
ttk.Button(btns, text="💬  Send Feedback", style="Info.TButton",   command=send_feedback).pack(fill="x", pady=(0,8))
ttk.Button(btns, text="➕  Add to Report", style="Danger.TButton", command=add_to_report).pack(fill="x", pady=(0,8))

save_updated_btn = ttk.Button(btns, text="💾  Save UPDATED to DB", style="Success.TButton", command=save_updated_to_db)
save_updated_btn.pack(fill="x", pady=(0,8))

search_btn = tk.Button(btns, text="🧭  Find Similar Cases (DB)", bg="#4F8FF7", fg="white",
                       activebackground="#3A7AE0", relief="flat", padx=10, pady=10,
                       command=search_similar_action)
search_btn.pack(fill="x")

# Export
row = ttk.Frame(controls, style="Card.TFrame"); row.pack(fill="x", pady=(18,0))
ttk.Label(row, text="Export", style="CardHint.TLabel").pack(anchor="w", pady=(0,6))
r2 = ttk.Frame(row, style="Card.TFrame"); r2.pack(fill="x")
ttk.Button(r2, text="🧾  Export as PDF",  style="Accent.TButton", command=export_pdf).pack(side="left", expand=True, fill="x", padx=(0,6))
ttk.Button(r2, text="📊  Export as Excel/CSV", style="Accent.TButton", command=export_excel).pack(side="left", expand=True, fill="x", padx=(6,0))

# ====== RIGHT OUTPUT ======
right_container = ttk.Frame(right, style="Card.TFrame"); right_container.pack(fill="both", expand=True, padx=18, pady=18)
ttk.Label(right_container, text="Report Output", style="CardTitle.TLabel").pack(anchor="w", pady=(0,8))

text_frame = ttk.Frame(right_container, style="Card.TFrame"); text_frame.pack(fill="both", expand=True)
report_output = tk.Text(text_frame, height=22, wrap=tk.WORD, font=("Consolas", 11),
                        bg="#0E1730", fg=TEXT, insertbackground=TEXT, relief="flat", borderwidth=0)
report_output.pack(side="left", fill="both", expand=True)
scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=report_output.yview)
scrollbar.pack(side="right", fill="y")
report_output.configure(yscrollcommand=scrollbar.set)

# Mouse wheel for right text
def _bind_wheel_to_text(widget):
    def _on_wheel(e):
        widget.yview_scroll(int(-1*(e.delta/120)), "units")
        return "break"
    widget.bind("<Enter>", lambda e: widget.bind_all("<MouseWheel>", _on_wheel))
    widget.bind("<Leave>", lambda e: widget.unbind_all("<MouseWheel>"))
_bind_wheel_to_text(report_output)

# Status bar
status_var = tk.StringVar(value="Ready.")
status_bar = ttk.Label(root, textvariable=status_var, anchor="w")
status_bar.configure(background="#0A1424", foreground=MUTED, font=("Segoe UI", 10))
status_bar.pack(side="bottom", fill="x")

# Menu
menubar = tk.Menu(root, tearoff=0); root.config(menu=menubar)
filemenu = tk.Menu(menubar, tearoff=0)
filemenu.add_command(label="Open PDF…", command=select_pdf_file)
filemenu.add_separator()
filemenu.add_command(label="Exit", command=root.destroy)
menubar.add_cascade(label="File", menu=filemenu)

def about():
    messagebox.showinfo("About",
        "Safety Report Analyzer\n"
        "• Auto-Classify (GPT) for TC/SMS occurrence + risk\n"
        "• Local SQLite DB (latest-only), Similar cases (Summary+7/30 with rationale)\n"
        "• Export PDF/Excel, English/Français\n"
        "• ICAO/TC aviation style\n")

helpmenu = tk.Menu(menubar, tearoff=0)
helpmenu.add_command(label="About", command=about)
menubar.add_cascade(label="Help", menu=helpmenu)

# Init
db_init(); db_migrate_add_columns()
set_status("Ready.")
root.mainloop()
