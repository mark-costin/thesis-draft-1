import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(layout="wide")

# ==============================================================================
# STATE INITIALIZATION & MOCK DATA
# ==============================================================================
if "active_doctor" not in st.session_state:
    st.session_state.active_doctor = {
        "name": "Velasco, Maria A.", "suffix": "MD, PhD", 
        "license": "PRC 8839210", "affiliation": "Lucerna Central Clinic",
        "specialty": "Cardiovascular" # Swap to "Type 2 Diabetes", "COPD", or "Mental Health" to test
    }

if "active_consultation_patient" not in st.session_state:
    st.session_state.active_consultation_patient = None

if "ai_results_ready" not in st.session_state:
    st.session_state.ai_results_ready = False

# Mock Queue & Directory
mock_queue = [
    {"q_num": "Q-01", "time_in": "08:15 AM", "id": "P-9921", "name": "Alvarez, Roberto", "urgency": "🔴 Critical", "complaint": "Chest pain, shortness of breath"},
    {"q_num": "Q-02", "time_in": "08:42 AM", "id": "P-8832", "name": "Santos, Elena", "urgency": "🟡 Priority", "complaint": "Palpitations"}
]

# ==============================================================================
# CLINICIAN TELEMETRY HEADER
# ==============================================================================
doc = st.session_state.active_doctor
spec_colors = {"Cardiovascular": "#ef4444", "Type 2 Diabetes": "#f43f5e", "COPD": "#0ea5e9", "Mental Health": "#8b5cf6"}
spec_icons = {"Cardiovascular": "🫀", "Type 2 Diabetes": "🩸", "COPD": "🫁", "Mental Health": "🧠"}

st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; background: white; border: 1px solid #e2e8f0; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
    <div>
        <h3 style="margin: 0; color: #1e293b;">Dr. {doc['name']} <span style="font-size: 1rem; color: #64748b;">{doc['suffix']}</span></h3>
        <div style="font-size: 0.9rem; color: #475569; font-weight: 600; margin-top: 4px;">✔ {doc['license']} • {doc['affiliation']}</div>
    </div>
    <div style="display: flex; gap: 16px; align-items: center;">
        <div style="background: {spec_colors.get(doc['specialty'], '#000')}20; color: {spec_colors.get(doc['specialty'], '#000')}; padding: 8px 16px; border-radius: 20px; font-weight: 700; font-size: 0.9rem;">
            {spec_icons.get(doc['specialty'], '')} {doc['specialty']} Specialist
        </div>
        <div style="background: #f1f5f9; border: 1px solid #cbd5e1; padding: 8px 16px; border-radius: 8px; text-align: center;">
            <div style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Active Queue</div>
            <div style="font-size: 1.4rem; font-weight: 800; color: #0f172a; line-height: 1.1;">{len(mock_queue)}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

tab_queue, tab_cdss = st.tabs(["PATIENTS & QUEUE", "AI DIAGNOSTICS & CDSS"])

# ==============================================================================
# TAB 1: PATIENTS & CLINICAL QUEUE
# ==============================================================================
with tab_queue:
    # 1. Today's Active Triage Queue
    with st.container(border=True):
        st.markdown("**🕒 Today's Active Triage Queue**")
        
        cols = st.columns([1, 1.5, 1.5, 2.5, 2, 4, 2])
        headers = ["Q#", "Time In", "ID", "Patient Name", "Urgency", "Complaint", "Action"]
        for col, header in zip(cols, headers):
            col.markdown(f"**{header}**")
            
        st.divider()
        for idx, p in enumerate(mock_queue):
            cols = st.columns([1, 1.5, 1.5, 2.5, 2, 4, 2], vertical_alignment="center")
            cols[0].write(p["q_num"])
            cols[1].write(p["time_in"])
            cols[2].write(p["id"])
            cols[3].write(f"**{p['name']}**")
            cols[4].write(p["urgency"])
            cols[5].write(p["complaint"])
            
            if cols[6].button("🩺 Start Consultation", key=f"start_{idx}", type="primary"):
                st.session_state.active_consultation_patient = p
                st.session_state.ai_results_ready = False
                st.rerun()

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Specialty-Personalized Master Patient Directory
    with st.container(border=True):
        st.markdown(f"**🗃️ Master Patient Directory ({doc['specialty']} View)**")
        
        f_col1, f_col2 = st.columns([2, 2])
        f_col1.text_input("Search Patient", placeholder="Name, ID, or National Health #", label_visibility="collapsed")
        f_col2.radio("Risk Stratification", ["All", "High Risk Flagged", "Stable", "Awaiting Review"], horizontal=True, label_visibility="collapsed")
        
        # Dynamic Columns based on Specialty
        if doc["specialty"] == "Cardiovascular":
            df_cols = {"ID": ["P-9921"], "Name": ["Alvarez, Roberto"], "Latest BP": ["145/92"], "Resting HR": ["88 bpm"], "Total Chol": ["240 mg/dL"], "Last ECG": ["2026-08-15"]}
        elif doc["specialty"] == "Type 2 Diabetes":
            df_cols = {"ID": ["P-9921"], "Name": ["Alvarez, Roberto"], "Fasting Gluc": ["126 mg/dL"], "HbA1c": ["7.2%"], "BMI": ["28.4"], "Last Lab": ["2026-08-15"]}
        else:
            df_cols = {"ID": ["P-9921"], "Name": ["Alvarez, Roberto"], "Vitals": ["Stable"], "Last Visit": ["2026-08-15"]}
            
        st.dataframe(pd.DataFrame(df_cols), use_container_width=True, hide_index=True)

    # 3. Longitudinal Health Timeline
    with st.expander("📈 Patient Consultation History & Vitals Timeline"):
        st.markdown("**Historical Biomarker Progression (Last 6 Months)**")
        st.line_chart(pd.DataFrame({"Systolic BP": [135, 140, 138, 142, 145]}, index=["Apr", "May", "Jun", "Jul", "Aug"]), height=200)

# ==============================================================================
# TAB 2: AI ANALYTICS & CDSS
# ==============================================================================
with tab_cdss:
    patient = st.session_state.active_consultation_patient
    
    if not patient:
        st.warning("⚠️ No patient actively loaded. Please select a patient from the **PATIENTS & QUEUE** tab.")
    else:
        # 1. Patient Snapshot & Family History
        with st.container(border=True):
            st.markdown(f"**Target:** `{patient['id']}` - **{patient['name']}** | Age: 58 | Sex: M | BMI: 28.4 | HR: 88 | BP: 145/92")
            st.divider()
            st.markdown("**Standardized Family History (Hereditary Risks)**")
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            f_col1.error("🫀 CVD: Present (Father)") if doc['specialty'] == "Cardiovascular" else f_col1.info("🫀 CVD: Present (Father)")
            f_col2.info("🩸 Diabetes: Present (Mother)")
            f_col3.success("🫁 Respiratory: Absent")
            f_col4.info("🧠 Neuro/Psych: Present (Sibling)")

        # 2. Disease-Specific Parameter Input Grid
        with st.container(border=True):
            st.markdown(f"**{doc['specialty']} Parameter Input**")
            p_col1, p_col2, p_col3, p_col4 = st.columns(4)
            
            if doc["specialty"] == "Cardiovascular":
                sys_bp = p_col1.number_input("Systolic BP (mmHg)", value=145)
                dia_bp = p_col2.number_input("Diastolic BP (mmHg)", value=92)
                chol = p_col3.number_input("Total Chol (mg/dL)", value=240)
                chest_pain = p_col4.selectbox("Chest Pain Class", ["Typical Angina", "Atypical", "Non-Anginal", "Asymptomatic"])
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("🧠 Run AI Diagnostic Inference", type="primary", use_container_width=True):
                st.session_state.ai_results_ready = True
                st.rerun()

        # 3. AI Analytics & Explainability Panel
        if st.session_state.ai_results_ready:
            st.markdown("---")
            st.markdown("**AI Analytics & Explainability**")
            
            res_col1, res_col2 = st.columns([1, 1.5], gap="large")
            
            with res_col1:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=82, title={'text': "Condition Probability"},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#1e293b"},
                        'steps': [
                            {'range': [0, 33], 'color': "#10b981"},
                            {'range': [33, 66], 'color': "#f59e0b"},
                            {'range': [66, 100], 'color': "#dc2626"}
                        ]
                    }
                ))
                fig.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=10))
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Model Benchmark: Validation Accuracy: 91.8% | ROC-AUC: 0.93")
                
            with res_col2:
                st.markdown("**Feature Importance (Risk Drivers)**")
                st.bar_chart(pd.DataFrame({
                    "Weight (%)": [38, 18, 14]
                }, index=["Systolic BP > 140", "Family History (CVD)", "Age > 55"]), horizontal=True, height=250)

            # 4. Clinical Verification Form
            with st.form("clinical_verification"):
                st.markdown("**🩺 Human-in-the-Loop Clinical Verification**")
                
                v_col1, v_col2 = st.columns(2)
                status = v_col1.selectbox("Diagnostic Status", ["Agree with AI Assessment (Confirmed)", "Modify AI Assessment (Clinical Variance)", "Reject AI Assessment (False Positive)"])
                icd_10 = v_col2.text_input("Official Diagnostic Code (ICD-10)", placeholder="e.g., I10 - Essential Hypertension")
                
                directives = st.text_area("Physician Directives & Treatment Plan", placeholder="Prescriptions, lifestyle interventions, follow-up dates...")
                
                submitted = st.form_submit_button("🔒 Lock & Commit Clinical Diagnosis", type="primary", use_container_width=True)
                if submitted:
                    st.success(f"Diagnosis {icd_10} locked. Audit trail updated.")
                    
            # 5. CDSS Diagnostic Report Generator
            with st.container(border=True):
                st.markdown("**📄 Report Generation Preview**")
                st.info(f"**Patient:** {patient['name']} | **ICD-10:** {icd_10} | **Status:** {status}")
                st.download_button("📥 Export Clinical Report (CSV)", data="Patient,ICD10,Status\nRoberto Alvarez,I10,Confirmed", file_name="clinical_report.csv", use_container_width=True)