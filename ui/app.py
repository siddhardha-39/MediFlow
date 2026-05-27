import streamlit as st
import httpx
import pandas as pd
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import MEDIFLOW_API_URL, MEDIFLOW_LLM_MODEL

# Page settings
st.set_page_config(page_title="MediFlow AI", page_icon="M", layout="wide")

API_URL = MEDIFLOW_API_URL

# ── Custom CSS Styling ────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Gradient premium dark theme */
    .stApp {
        background: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #1e1b4b 100%);
        color: #f1f5f9;
    }
    .main-title {
        font-family: 'Outfit', 'Inter', sans-serif;
        background: linear-gradient(90deg, #38bdf8 0%, #6366f1 50%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 2px;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 16px;
        margin-bottom: 25px;
        font-weight: 400;
    }
    .metric-card {
        background-color: rgba(30, 41, 59, 0.45);
        border: 1px solid rgba(71, 85, 105, 0.4);
        border-radius: 12px;
        padding: 22px 15px;
        text-align: center;
        backdrop-filter: blur(8px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
        transition: transform 0.2s ease-in-out;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.5);
    }
    .metric-value {
        font-size: 34px;
        font-weight: 800;
        color: #38bdf8;
        margin-bottom: 2px;
    }
    .metric-label {
        font-size: 13px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .briefing-container {
        background-color: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(51, 65, 85, 0.5);
        border-radius: 12px;
        padding: 25px;
        font-family: 'Courier New', Courier, monospace;
        color: #cbd5e1;
        white-space: pre-wrap;
        line-height: 1.6;
        box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.5);
        font-size: 14px;
    }
    /* Highlight allergies & critical text */
    .critical-banner {
        background-color: rgba(239, 68, 68, 0.15);
        border-left: 5px solid #ef4444;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 15px;
        color: #fca5a5;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


# ── Backend Helper Functions ──────────────────────────────────────────────────

def check_backend_health():
    try:
        resp = httpx.get(f"{API_URL}/health", timeout=2)
        if resp.status_code == 200:
            return True, resp.json().get("version", "0.4.0")
    except:
        pass
    return False, ""


def fetch_patients():
    try:
        resp = httpx.get(f"{API_URL}/api/patients", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"Error fetching patients: {e}")
    return []


def fetch_patient_briefing(patient_id):
    try:
        resp = httpx.get(f"{API_URL}/api/patients/{patient_id}/briefing", timeout=60)
        if resp.status_code == 200:
            return resp.json().get("briefing", "")
        try:
            detail = str(resp.json().get("detail", ""))
        except Exception:
            detail = resp.text
        if "ollama" in detail.lower() or "connect" in detail.lower():
            return (
                "AI model service is offline. Start Ollama and pull the configured models "
                f"to enable RAG briefings. Current model: {MEDIFLOW_LLM_MODEL}."
            )
        return f"Backend returned status {resp.status_code}: {detail}"
    except Exception as e:
        return f"Connection error: {e}. Is the FastAPI backend running at {API_URL}?"


def fetch_patient_history(patient_id):
    try:
        resp = httpx.get(f"{API_URL}/api/patients/{patient_id}/history", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("history", "")
    except Exception as e:
        st.error(f"Error fetching patient history: {e}")
    return ""


def fetch_patient_sessions(patient_id):
    try:
        resp = httpx.get(f"{API_URL}/api/patients/{patient_id}/sessions", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"Error fetching sessions: {e}")
    return []


def start_workflow_api(patient_name, raw_transcript=None, audio_file=None):
    try:
        files = None
        data = {"patient_name": patient_name}
        if raw_transcript:
            data["raw_transcript"] = raw_transcript
        if audio_file:
            files = {"file": (audio_file.name, audio_file.getvalue(), audio_file.type)}
        
        resp = httpx.post(f"{API_URL}/api/workflow/start", data=data, files=files, timeout=120)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"Failed to start workflow: {resp.text}")
    except Exception as e:
        st.error(f"Error starting workflow: {e}")
    return None


def review_workflow_api(thread_id, approve, feedback="", soap_data=None):
    try:
        payload = {
            "thread_id": thread_id,
            "approve": approve,
            "feedback": feedback
        }
        if soap_data:
            payload.update(soap_data)
            
        resp = httpx.post(f"{API_URL}/api/workflow/review", json=payload, timeout=120)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"Failed to submit review: {resp.text}")
    except Exception as e:
        st.error(f"Error submitting review: {e}")
    return None


def fetch_dashboard_stats():
    try:
        resp = httpx.get(f"{API_URL}/api/dashboard/stats", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"Error fetching dashboard stats: {e}")
    return {}


def ask_dashboard_api(query):
    try:
        resp = httpx.post(f"{API_URL}/api/dashboard/ask", json={"query": query}, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("answer", "")
    except Exception as e:
        return f"Error connecting to dashboard Q&A: {e}"
    return "Dashboard Q&A is unavailable. Backend statistics may still be available."


def resolve_rag_patient_id(patient_info):
    """Return a linked patient document ID when one is known."""
    mrn = (patient_info.get("medical_record_number") or "").strip()
    if mrn:
        return mrn

    name = (patient_info.get("name") or "").strip().lower()
    if name == "rajesh kumar":
        return "PT-2024-001-Rajesh-Kumar"

    return None


# ── Render UI ─────────────────────────────────────────────────────────────────

# Header
col_title, col_status = st.columns([4, 1])
with col_title:
    st.markdown('<div class="main-title">MediFlow AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Hospital Intelligence Platform & Clinical Documentation Co-Pilot</div>', unsafe_allow_html=True)

with col_status:
    is_healthy, version = check_backend_health()
    if is_healthy:
        st.success(f"Connected (v{version})")
    else:
        st.error("Backend offline")

# Create Tabs
tab_clinical, tab_rag, tab_dash = st.tabs([
    "Clinical Documentation Agent",
    "Patient History Summarizer",
    "Hospital Intelligence Dashboard",
])

# ── TAB 1: Clinical Documentation Agent ────────────────────────────────────────
with tab_clinical:
    st.header("Consultation Documentation Workflow")
    
    # Initialize session state for workflow tracking
    if "active_thread_id" not in st.session_state:
        st.session_state.active_thread_id = None
        st.session_state.workflow_status = None
        st.session_state.state_data = {}

    # Discard Active Thread callback
    def discard_thread():
        st.session_state.active_thread_id = None
        st.session_state.workflow_status = None
        st.session_state.state_data = {}
        st.toast("Active session discarded.")

    # Render starting screen if no active thread
    if not st.session_state.active_thread_id:
        st.subheader("Start New Consultation Session")
        
        # Patient selector/creator
        patients = fetch_patients()
        patient_names = [p["name"] for p in patients]
        
        col_pat_sel, col_pat_new = st.columns(2)
        with col_pat_sel:
            selected_pat = st.selectbox(
                "Select Existing Patient", 
                options=["-- Create New --"] + patient_names,
                help="Choose an existing patient to fetch history, or select 'Create New'"
            )
        
        with col_pat_new:
            new_pat_name = st.text_input(
                "Or Enter New Patient Name", 
                value="",
                placeholder="First Last (e.g. John Doe)"
            )
            
        patient_name = new_pat_name if selected_pat == "-- Create New --" or not selected_pat else selected_pat
        
        # Audio / Text toggle
        input_mode = st.radio("Select Input Mode", options=["Upload Consultation Audio", "Paste Text Transcript"])
        
        audio_file = None
        text_transcript = ""
        
        if input_mode == "Upload Consultation Audio":
            audio_file = st.file_uploader(
                "Upload dictation recording (WAV, MP3, M4A)", 
                type=["wav", "mp3", "m4a", "ogg", "flac"]
            )
            st.info("Whisper model runs locally. Audio will be preprocessed to 16kHz mono.")
        else:
            text_transcript = st.text_area(
                "Paste Rough Transcript",
                placeholder="Doctor: How are you today?\nPatient: I have had a headache for 3 days...",
                height=150
            )

        if st.button("Process and Generate SOAP Draft", type="primary"):
            if not patient_name.strip():
                st.warning("Please specify a patient name.")
            elif input_mode == "Upload Consultation Audio" and not audio_file:
                st.warning("Please upload an audio file.")
            elif input_mode == "Paste Text Transcript" and not text_transcript.strip():
                st.warning("Please provide a transcript.")
            else:
                with st.spinner("Processing clinical documentation (this might take a few moments)..."):
                    res = start_workflow_api(
                        patient_name=patient_name,
                        raw_transcript=text_transcript if input_mode == "Paste Text Transcript" else None,
                        audio_file=audio_file
                    )
                    if res:
                        st.session_state.active_thread_id = res["thread_id"]
                        st.session_state.workflow_status = res["status"]
                        st.session_state.state_data = res["state"]
                        st.rerun()

    else:
        # Active Review Board
        thread_id = st.session_state.active_thread_id
        state = st.session_state.state_data
        status = st.session_state.workflow_status
        
        col_board_left, col_board_right = st.columns([3, 2])
        
        with col_board_left:
            st.subheader(f"Review SOAP Note: {state.get('patient_name')}")
            st.caption(f"Thread ID: `{thread_id}` | Correction Loops: `{state.get('retry_count', 0)}/3`")
            
            # SOAP Section Inputs
            soap_s = st.text_area("Subjective (S) - Patient History & Symptoms", value=state.get("soap_subjective", ""), height=150)
            soap_o = st.text_area("Objective (O) - Vitals & Examinations", value=state.get("soap_objective", ""), height=150)
            soap_a = st.text_area("Assessment (A) - Diagnosis & Clinical Logic", value=state.get("soap_assessment", ""), height=150)
            soap_p = st.text_area("Plan (P) - Treatment, Medications & Follow-up", value=state.get("soap_plan", ""), height=150)
            
            # Pack latest fields to submit
            soap_payload = {
                "soap_subjective": soap_s,
                "soap_objective": soap_o,
                "soap_assessment": soap_a,
                "soap_plan": soap_p
            }
            
            # Action controls
            st.write("---")
            feedback = st.text_area(
                "Feedback for Corrector Agent (e.g. 'Abnormal serum creatinine is missing from Objective' or 'Increase Metformin dose')",
                value="",
                placeholder="Provide instructions here if rejecting or requesting changes...",
                height=80
            )
            
            col_approve, col_reject, col_discard = st.columns(3)
            with col_approve:
                if st.button("Approve and Save to EHR", type="primary", use_container_width=True):
                    with st.spinner("Saving clinical record..."):
                        res = review_workflow_api(thread_id, approve=True, feedback="", soap_data=soap_payload)
                        if res and res.get("status") == "completed":
                            st.success(f"Success! Record persisted. Session ID: {res['state'].get('session_id')}")
                            st.session_state.active_thread_id = None
                            st.session_state.workflow_status = None
                            st.session_state.state_data = {}
                            st.balloons()
                            st.button("Start New Consultation")
                        else:
                            st.error("Workflow failed to complete.")
            
            with col_reject:
                if st.button("Request Regeneration", use_container_width=True):
                    if not feedback.strip():
                        st.warning("Please write feedback first before requesting correction.")
                    else:
                        with st.spinner("Regenerating clinical details..."):
                            res = review_workflow_api(thread_id, approve=False, feedback=feedback, soap_data=soap_payload)
                            if res:
                                st.session_state.workflow_status = res["status"]
                                st.session_state.state_data = res["state"]
                                if res["status"] == "completed":
                                    st.info("Maximum retry limit reached. Review the note and approve only if acceptable.")
                                st.rerun()
            
            with col_discard:
                st.button("Discard Session", on_click=discard_thread, use_container_width=True)
                
        with col_board_right:
            st.subheader("Extraction Metrics and Warnings")
            
            # Warnings/Validation display
            missing = []
            for sec, val in [("Subjective", soap_s), ("Objective", soap_o), ("Assessment", soap_a), ("Plan", soap_p)]:
                if not val.strip():
                    missing.append(sec)
            
            if missing:
                st.markdown(
                    f'<div class="critical-banner">Validation warning: The following required sections are empty: {", ".join(missing)}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.success("SOAP note conforms to clinical completeness guidelines.")
                
            # Extracted Medical Entities
            st.markdown("### Extracted Entities")
            st.write("**Known Allergies:**")
            allergies = state.get("allergies", [])
            if allergies:
                st.code(", ".join(allergies) if isinstance(allergies, list) else str(allergies))
            else:
                st.write("None detected")
                
            st.write("**Extracted Chronic Conditions:**")
            conditions = state.get("conditions", [])
            if conditions:
                st.code(", ".join(conditions) if isinstance(conditions, list) else str(conditions))
            else:
                st.write("None detected")
                
            st.write("**Current Medications:**")
            medications = state.get("medications", [])
            if medications:
                st.code(", ".join(medications) if isinstance(medications, list) else str(medications))
            else:
                st.write("None detected")
                
            # Raw transcript reference
            with st.expander("Show Consultation Transcript Reference"):
                st.write(state.get("clean_transcript") or state.get("raw_transcript") or "No transcript reference available.")


# ── TAB 2: Patient History Summarizer ─────────────────────────────────────────
with tab_rag:
    st.header("Patient Document briefing & Visit History")
    
    patients = fetch_patients()
    if not patients:
        st.info("No patients found in SQLite. Record a consultation in Tab 1 to create one.")
    else:
        patient_names = {p["name"]: p for p in patients}
        sel_pat_name = st.selectbox("Select Patient to Review", options=list(patient_names.keys()))
        patient_info = patient_names[sel_pat_name]
        
        # Display Patient Card
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.markdown(f"**MRN:** `{patient_info.get('medical_record_number') or 'N/A'}`")
        with col_p2:
            st.markdown(f"**Age / Gender:** `{patient_info.get('age') or 'N/A'}` | `{patient_info.get('gender') or 'N/A'}`")
        with col_p3:
            st.markdown(f"**Created On:** `{patient_info.get('created_at', 'N/A')[:10]}`")
            
        st.write("---")
        
        col_b_left, col_b_right = st.columns([3, 2])
        
        with col_b_left:
            st.subheader("Grounded 30-Second Clinical Briefing")
            st.caption("Retrieves clinical records from ChromaDB + cross-references guidelines via local Llama 3.")
            
            rag_patient_id = resolve_rag_patient_id(patient_info)

            if not rag_patient_id:
                st.warning("No linked patient document found. Add a medical_record_number that matches a patient PDF stem to enable RAG briefing.")
            elif st.button("Generate Briefing", type="primary"):
                with st.spinner("Extracting documents and compiling summary..."):
                    briefing = fetch_patient_briefing(rag_patient_id)
                    st.markdown(f'<div class="briefing-container">{briefing}</div>', unsafe_allow_html=True)
            else:
                st.info("Click 'Generate Briefing' to fetch the grounded RAG summary.")

        with col_b_right:
            st.subheader("Previous Session Logs")
            
            sessions = fetch_patient_sessions(patient_info["id"])
            if not sessions:
                st.write("No recorded consultation logs found.")
            else:
                for idx, s in enumerate(sessions, 1):
                    with st.expander(f"Visit Session on {s.get('created_at')[:16]}", expanded=(idx==1)):
                        st.markdown("**Subjective:**")
                        st.write(s.get("soap_subjective") or "*None*")
                        st.markdown("**Objective:**")
                        st.write(s.get("soap_objective") or "*None*")
                        st.markdown("**Assessment:**")
                        st.write(s.get("soap_assessment") or "*None*")
                        st.markdown("**Plan:**")
                        st.write(s.get("soap_plan") or "*None*")
                        
                        # Show JSON fields
                        for field in ["conditions", "medications", "allergies"]:
                            val = s.get(field)
                            if val:
                                try:
                                    items = json.loads(val)
                                    if items:
                                        st.markdown(f"**{field.title()}:** `{', '.join(items)}`")
                                except:
                                    pass


# ── TAB 3: Hospital Intelligence Dashboard ────────────────────────────────────
with tab_dash:
    st.header("Hospital Intelligence Operations Control")
    st.caption("Aggregated analytics from clinical consult logs and patient metrics.")
    
    # Reload stats button
    if st.button("Refresh Operations Data"):
        st.rerun()
        
    stats = fetch_dashboard_stats()
    
    if not stats:
        st.warning("No dashboard metrics available. Record sessions to populate operational data.")
    else:
        # KPI Cards
        st.write("### Operational KPIs")
        kpi_p, kpi_s, kpi_c, kpi_m = st.columns(4)
        
        with kpi_p:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats.get('total_patients', 0)}</div>
                <div class="metric-label">Total Patients</div>
            </div>
            """, unsafe_allow_html=True)
            
        with kpi_s:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats.get('total_sessions', 0)}</div>
                <div class="metric-label">Consultations</div>
            </div>
            """, unsafe_allow_html=True)
            
        with kpi_c:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(stats.get('top_conditions', []))}</div>
                <div class="metric-label">Unique Conditions</div>
            </div>
            """, unsafe_allow_html=True)
            
        with kpi_m:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(stats.get('top_medications', []))}</div>
                <div class="metric-label">Active Prescriptions</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.write("---")
        
        col_d_left, col_d_right = st.columns([3, 2])
        
        with col_d_left:
            st.subheader("Clinical Diagnoses and Prescription Trends")
            
            # Plot Conditions
            cond_data = stats.get("top_conditions", [])
            med_data = stats.get("top_medications", [])
            
            if cond_data:
                df_cond = pd.DataFrame(cond_data)
                st.write("**Top Diagnosed Conditions Count**")
                st.bar_chart(data=df_cond, x="name", y="count", color="#38bdf8")
            else:
                st.info("No condition trends to display yet.")
                
            if med_data:
                df_med = pd.DataFrame(med_data)
                st.write("**Top Prescribed Medications Count**")
                st.bar_chart(data=df_med, x="name", y="count", color="#6366f1")
            else:
                st.info("No prescription trends to display yet.")

        with col_d_right:
            st.subheader("Ask Hospital Intelligence Assistant")
            st.caption("Ask questions about patient volumes, trends, and clinical alerts.")
            
            query = st.text_input("Enter Question for Local LLM", placeholder="e.g. How many patients do we have in the database?")
            if st.button("Submit Question", type="primary"):
                if not query.strip():
                    st.warning("Please enter a question.")
                else:
                    with st.spinner("Analyzing statistics..."):
                        ans = ask_dashboard_api(query)
                        st.info(ans)
