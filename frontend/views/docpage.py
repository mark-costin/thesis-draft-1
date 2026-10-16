import os
import sys
import textwrap
import uuid
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# 1. PATHS, SHARED UI, API CLIENT
# ==============================================================================
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.abspath(os.path.join(_HERE, "..")), os.path.abspath(os.path.join(_HERE, "..", ".."))):
    if _p not in sys.path:
        sys.path.append(_p)

try:
    from styles import basetab_layout_, render_top_navbar, render_fhrs_panel, show_api_error, flash, show_flash
except ImportError:
    from views.styles import basetab_layout_, render_top_navbar, render_fhrs_panel, show_api_error, flash, show_flash

from frontend import cdss_logic as L
from frontend import docpage_api

# ==============================================================================
# 2. PAGE SETUP
# ==============================================================================
st.set_page_config(layout="wide", page_title="HEART | Clinician Workspace")
basetab_layout_()
st.markdown("<style>[data-testid='stToolbar'] {visibility: hidden;}</style>", unsafe_allow_html=True)

if not st.session_state.get("token"):
    st.warning("Session expired. Please log in.")
    st.stop()

# ==============================================================================
# 3. LOGGED-IN DOCTOR (profile comes from /auth/login; nothing invented)
# ==============================================================================
profile = st.session_state.get("user_profile") or {}
_first, _last = (profile.get("first_name") or "").strip(), (profile.get("last_name") or "").strip()
active_doc = {
    "name": f"Dr. {_first} {_last}".strip() if (_first or _last) else st.session_state.get("username", "Clinician"),
    "suffix": profile.get("suffix") or "",
    "prc": profile.get("license_number") or "License not on file",
    "affiliation": profile.get("hospital_affiliation") or "Lucerna Medica",
    "specialty": profile.get("specialization") or "General Practice",
    "icon": "🩺", "badge_fg": "#0f172a", "default_modality": "cvd",
}
_spec = active_doc["specialty"].upper()
if "CARDIO" in _spec:
    active_doc.update({"icon": "🫀", "badge_fg": "#ef4444", "default_modality": "cvd"})
elif "ENDOCRIN" in _spec or "DIABET" in _spec:
    active_doc.update({"icon": "🩸", "badge_fg": "#d97706", "default_modality": "t2d"})
elif "PULMON" in _spec or "RESPIR" in _spec:
    active_doc.update({"icon": "🫁", "badge_fg": "#0284c7", "default_modality": "resp"})
elif "NEURO" in _spec or "PSYCH" in _spec:
    active_doc.update({"icon": "🧠", "badge_fg": "#7c3aed", "default_modality": "neuro"})

for _key, _default in {"active_patient_id": None, "last_inference": None, "last_inference_pid": None,
                       "last_inference_modality": None, "last_commit_receipt": None, "last_commit_pid": None,
                       "audit_trail": []}.items():
    st.session_state.setdefault(_key, _default)


def open_patient(patient_id):
    """Switch the CDSS workspace to another patient and forget the previous patient's result."""
    st.session_state["active_patient_id"] = int(patient_id)
    st.session_state["last_inference"] = None
    st.session_state["last_inference_pid"] = None
    st.session_state["last_inference_modality"] = None


def append_audit(event_type, payload):
    st.session_state["audit_trail"].append({
        "audit_id": f"AUD-{uuid.uuid4().hex[:6].upper()}",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event_type": event_type,
        "payload": payload,
    })


# Today's waiting tickets (GET /doctor/queue -> {"status", "queue": [...]})
queue_resp = docpage_api.get_doctor_queue()
queue = L.queue_tickets(queue_resp)

# ==============================================================================
# 4. WORKSPACE
# ==============================================================================
_, col_main, _ = st.columns([5, 90, 5], gap="small")

with col_main:
    render_top_navbar(
        user_name=f"{active_doc['name']}{', ' + active_doc['suffix'] if active_doc['suffix'] else ''}",
        user_role=f"ATTENDING CLINICIAN | ✔ {active_doc['prc']}",
        user_email=f"Affiliation: {active_doc['affiliation']} • Waiting now: {len(queue)}",
        badge_label=f"{active_doc['icon']} {active_doc['specialty']}",
        badge_color=active_doc["badge_fg"],
    )

    tab_overview, tab_queue, tab_cdss = st.tabs(["Overview Dashboard", "Live Patients & Triage", "AI Diagnostics & CDSS"])

    # --------------------------------------------------------------------------
    # TAB 1: OVERVIEW (live queue size + which disease models the server loaded)
    # --------------------------------------------------------------------------
    with tab_overview:
        st.write("")
        models_resp = docpage_api.get_models_status()
        model_rows = L.models_status_rows(models_resp)
        with st.container(border=True):
            st.markdown("### Clinic status")
            m1, m2 = st.columns(2)
            m1.metric("Patients waiting today", len(queue) if L.is_ok(queue_resp) else "—")
            m2.metric("Disease models loaded", f"{sum(r['loaded'] for r in model_rows)} / 4" if model_rows else "—")
            if not L.is_ok(models_resp):
                show_api_error(models_resp)
            elif model_rows:
                st.dataframe(pd.DataFrame([{
                    "Disease": L.MODALITY_LABELS[r["disease"]],
                    "Loaded": "🟢 Yes" if r["loaded"] else "🔴 No (stub)",
                    "Model version": r["model_version"] or "—",
                    "Notes": r["problem"] or "; ".join(r["warnings"]) or "—",
                } for r in model_rows]), hide_index=True, use_container_width=True)
                if not all(r["loaded"] for r in model_rows):
                    st.warning("A disease without a loaded model returns no prediction until the server loads it.")

    # --------------------------------------------------------------------------
    # TAB 2: TODAY'S QUEUE
    # --------------------------------------------------------------------------
    with tab_queue:
        st.write("")
        st.markdown("### Today's Active Triage Queue")
        st.caption("Waiting tickets in check-in order. A ticket closes when you save a consultation.")
        if not L.is_ok(queue_resp):
            show_api_error(queue_resp)
        elif not queue:
            st.info("The waiting room is currently empty. Patients will appear here upon pre-check-in.")
        else:
            for item in queue:
                with st.container(border=True):
                    qc1, qc2, qc3, qc4 = st.columns([1, 3, 3, 2])
                    qc1.markdown(f"### 🎫 {item.get('queue_no', '--')}")
                    with qc2:
                        st.markdown(f"**{item.get('name', 'Patient')}** (PID #{item.get('patient_id', '--')})")
                        st.caption(f"Arrival: {item.get('time_in', '--')} | Priority: {item.get('urgency', 'Routine')} | "
                                   f"{item.get('lifecycle_status', item.get('status', ''))}")
                    with qc3:
                        st.markdown(f"**Complaint:** {item.get('complaint', '—')}")
                        st.caption(f"Vitals: {item.get('vitals', 'N/A')} | Watch: {item.get('watch_flag', '—')}")
                    with qc4:
                        qid = item.get("patient_id")
                        if st.button("🩺 Call to Consult", key=f"call_q_{qid}", type="primary", use_container_width=True):
                            open_patient(qid)
                            st.session_state["consult_pid_input"] = int(qid)  # widget not drawn yet in this run
                            st.session_state["cdss_notice"] = f"Loaded {item.get('name', 'patient')} into the CDSS tab."
                            st.rerun()

    # --------------------------------------------------------------------------
    # TAB 3: CDSS WORKSPACE
    # --------------------------------------------------------------------------
    def render_results(resp, disease_label):
        s = L.summarize_inference(resp)
        if s["is_stub"]:
            st.warning(f"The {disease_label} model is not loaded on the server (stub), so no prediction is shown. "
                       "Check Overview → Disease models loaded.")
            return
        if not s["show_result"]:
            st.warning("The backend returned no risk score for this run.")
            return

        color = L.tier_color(s["tier"])
        col_gauge, col_chart = st.columns([1, 1.5])
        with col_gauge:
            st.markdown(f"<div class='tier-badge' style='text-align:center;font-weight:700;color:{color};'>"
                        f"{s['tier']} RISK</div>", unsafe_allow_html=True)
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number", value=s["score"],
                number={"suffix": "%", "font": {"size": 42, "color": color}},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": color}},
            ))
            fig_gauge.update_layout(height=240, margin=dict(l=20, r=20, t=20, b=10))
            st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})
            st.caption(f"Inputs built from: {s['source'] or '—'}")
        with col_chart:
            st.markdown("##### What drove this result (TreeSHAP)")
            if s["drivers"]:
                names = [n for n, _ in reversed(s["drivers"])]
                values = [v for _, v in reversed(s["drivers"])]
                fig_bar = go.Figure(go.Bar(
                    x=values, y=names, orientation="h",
                    marker=dict(color=["#ef4444" if v > 0 else "#10b981" for v in values]),
                    text=[f"{v:+.3f}" for v in values], textposition="outside"))
                fig_bar.update_layout(height=260, margin=dict(l=10, r=40, t=10, b=10),
                                      xaxis_title="SHAP value (log-odds): right raises risk, left lowers it")
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
            else:
                st.caption("The backend returned no SHAP drivers for this run.")

        if s["missing_features"]:
            st.warning("Based on incomplete data. Inputs the model did not get: " + ", ".join(s["missing_features"]))

        render_fhrs_panel(s["fhrs"], title="Family-history risk used in this prediction")

        st.markdown("##### Fairness and calibration (from training)")
        fair = s["fairness"]
        if fair.get("disparity_detected"):
            st.warning(f"Subgroup AUROC gap {fair.get('gap')} is above the {fair.get('threshold', 0.05)} fairness "
                       "threshold in training cross-validation. Interpret this result with care.")
        elif fair:
            st.success(f"Subgroup gap {fair.get('gap', '—')} is within the {fair.get('threshold', 0.05)} threshold.")
        cal = s["calibration"]
        if cal:
            st.caption(f"Calibration: {cal.get('method', '—')} · Brier {cal.get('brier_score', '—')} · ECE {cal.get('ece', '—')}")
        if s["trace"]:
            st.caption(" · ".join(f"{k}: {v}" for k, v in s["trace"].items()))
        with st.expander("Raw reply from POST /predictions/infer"):
            st.json(L.strip_meta(resp))

    def biomarker_input(field, code, pid):
        key = f"bm_{code}_{field['column']}_{pid}"
        hint = f" · {field['min']}–{field['max']}" if field["min"] is not None else ""
        label = f"{field['label']}{' (' + field['unit'] + ')' if field['unit'] else ''}{hint}"
        if field["kind"] == "flag":
            choice = st.selectbox(label, ["Not recorded", "No", "Yes"], key=key)
            return {"Not recorded": None, "No": 0, "Yes": 1}[choice]
        if field["kind"] == "int":
            return st.number_input(label, value=None, step=1, key=key)
        return st.number_input(label, value=None, step=float(field["step"]), key=key)

    def render_workspace(pid, info_col):
        prof_resp = docpage_api.get_doctor_patient(pid)
        prof = L.patient_profile(prof_resp)
        if prof is None:
            with info_col:
                show_api_error(prof_resp)
            return
        header = L.patient_header(dict(prof, patient_id=prof.get("patient_id", pid)))

        baseline_resp = docpage_api.get_baseline(pid)
        phase = L.baseline_phase(baseline_resp)

        with info_col:
            st.markdown(f"### Active Consultation: **{header['name']}** (`PID-{pid}`)")
            st.caption(f"Age: {header['age'] if header['age'] is not None else '—'} | Sex: {header['sex']} | "
                       f"Date of birth: {header['dob'] or '—'}")

        if phase is None:
            show_api_error(baseline_resp)
            st.warning("Could not check whether this patient has a baseline. Encounters can't be committed until it loads.")
        else:
            if phase == 1:
                title, desc, bg, border = ("Phase 1 · Baseline intake",
                                           "No sealed baseline yet. This visit's encounter becomes the patient's baseline.",
                                           "#e0f2fe", "#0284c7")
            else:
                title, desc, bg, border = ("Phase 2 · Follow-up",
                                           f"Baseline sealed {baseline_resp.get('established_at_utc', '')}. "
                                           "This visit is saved as a follow-up linked to it.", "#ede9fe", "#7c3aed")
            st.markdown(textwrap.dedent(f"""
                <div style="padding: 15px; border-radius: 8px; background: {bg}; border-left: 5px solid {border}; margin: 10px 0 18px 0;">
                    <h4 style="margin: 0; color: #0f172a;">{title}</h4>
                    <p style="margin: 4px 0 0 0; font-size: 0.9rem; color: #475569;">{desc}</p>
                </div>"""), unsafe_allow_html=True)

        # Biological sex (POST /patient/biological-sex; all four models read it)
        with st.container(border=True):
            sx1, sx2 = st.columns([3, 1], vertical_alignment="bottom")
            current_sex = prof.get("biological_sex")
            sex_options = ["Female", "Male"]
            sex_choice = sx1.selectbox("Biological sex (used by all four models)", sex_options,
                                       index=sex_options.index(current_sex) if current_sex in sex_options else None,
                                       placeholder="Not set", key=f"sex_pick_{pid}")
            if sx2.button("Save sex", key="sex_save_btn", use_container_width=True,
                          disabled=sex_choice is None or sex_choice == current_sex):
                resp = docpage_api.set_biological_sex(pid, sex_choice)
                if L.is_ok(resp):
                    flash("success", f"Biological sex saved as {sex_choice}.")
                    st.rerun()
                show_api_error(resp)

        codes = list(L.MODALITY_LABELS)
        code = st.selectbox("Disease to evaluate*", codes, format_func=L.MODALITY_LABELS.get,
                            index=codes.index(active_doc["default_modality"]), key="cdss_modality")
        disease_label = L.MODALITY_LABELS[code]

        # ---------------- 1 · Family history -----------------------------------
        with st.container(border=True):
            st.markdown("#### 1 · Family history (FHRS inputs)")
            st.caption("Send tier and onset only: the backend applies the FHRS weights. "
                       "Unverified relatives count half until you verify them.")
            fh_resp = docpage_api.get_patient_family_history(pid)
            if not L.is_ok(fh_resp):
                show_api_error(fh_resp)
            else:
                relatives = fh_resp.get("family_history") or []
                if not relatives:
                    st.info("No relatives recorded yet.")
                for rel in relatives:
                    r1, r2, r3, r4 = st.columns([3, 3, 2, 1.4], vertical_alignment="center")
                    r1.markdown(f"**{L.DISEASE_CHOICES.get(rel.get('disease_domain'), rel.get('disease_domain'))}**"
                                f"{' · ' + rel['specific_diagnosis'] if rel.get('specific_diagnosis') else ''}")
                    r2.caption(f"{L.TIER_LABELS.get(rel.get('relationship_tier'), rel.get('relationship_tier'))} · "
                               f"onset {L.ONSET_LABELS.get(rel.get('onset_classification'), rel.get('onset_classification'))}"
                               f"{' · age ' + str(rel['age_at_diagnosis']) if rel.get('age_at_diagnosis') is not None else ''}"
                               f"{' · same household' if rel.get('shared_environment') else ''}")
                    r3.markdown("🟢 Verified" if rel.get("is_verified") else "🟡 Unverified (×0.5)")
                    if not rel.get("is_verified"):
                        if r4.button("Verify", key=f"fh_verify_{rel.get('record_id')}", use_container_width=True):
                            resp = docpage_api.verify_family_history(rel.get("record_id"))
                            if L.is_ok(resp):
                                flash("success", "Relative verified. It now counts fully in the FHRS.")
                                st.rerun()
                            show_api_error(resp)

            with st.form(f"fh_form_{pid}", clear_on_submit=True):
                st.markdown("**Add a relative**")
                f1, f2, f3 = st.columns(3)
                fh_codes = list(L.DISEASE_CHOICES)
                fh_disease = f1.selectbox("Disease", fh_codes, format_func=L.DISEASE_CHOICES.get,
                                          index=fh_codes.index(code), key=f"fh_disease_{pid}")
                fh_tier = f2.selectbox("Relationship", list(L.TIER_CHOICES), key=f"fh_tier_{pid}")
                fh_onset = f3.selectbox("Age of onset", list(L.ONSET_CHOICES), key=f"fh_onset_{pid}")
                g1, g2 = st.columns(2)
                fh_diag = g1.text_input("Specific diagnosis (optional)", key=f"fh_diag_{pid}")
                fh_age = g2.number_input("Age at diagnosis (optional)", min_value=0, max_value=120, value=None, step=1,
                                         key=f"fh_age_{pid}")
                fh_shared = st.checkbox("Lived in the same household", key=f"fh_shared_{pid}")
                fh_verified = st.checkbox("Diagnosis confirmed from records (verified)", key=f"fh_verified_{pid}")
                if st.form_submit_button("Save relative"):
                    try:
                        payload = L.build_family_history_payload(
                            fh_disease, L.TIER_CHOICES[fh_tier], L.ONSET_CHOICES[fh_onset],
                            specific_diagnosis=fh_diag, age_at_diagnosis=fh_age, shared_environment=fh_shared,
                            is_verified=fh_verified, patient_id=pid)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        resp = docpage_api.submit_patient_family_history(payload)
                        if L.is_ok(resp):
                            flash("success", "Relative saved.")
                            st.rerun()
                        show_api_error(resp)

            fhrs_resp = docpage_api.get_fhrs(code, pid)
            if L.is_ok(fhrs_resp):
                render_fhrs_panel(L.fhrs_view(fhrs_resp.get("fhrs")), title=f"FHRS for {disease_label}")
            else:
                show_api_error(fhrs_resp)

        # ---------------- 2 · Household hazards ---------------------------------
        with st.container(border=True):
            st.markdown("#### 2 · Shared household hazards")
            hz_resp = docpage_api.get_hazards(pid)
            if not L.is_ok(hz_resp):
                show_api_error(hz_resp)
            else:
                hazards = hz_resp.get("hazards") or []
                catalogue = hz_resp.get("catalogue") or {}
                cat_labels = {h.get("code"): h for h in catalogue.get(code, [])}
                for hz in L.recorded_hazards(hazards, code):
                    h1, h2 = st.columns([5, 1], vertical_alignment="center")
                    info = cat_labels.get(hz.get("hazard_code"), {})
                    h1.markdown(f"• {hz.get('label') or info.get('label') or hz.get('hazard_code')}"
                                f"{' (+' + str(info['e_j']) + ')' if info.get('e_j') is not None else ''}")
                    if h2.button("Remove", key=f"hz_del_{hz.get('id')}", use_container_width=True):
                        resp = docpage_api.delete_hazard(hz.get("id"))
                        if L.is_ok(resp):
                            flash("success", "Hazard removed.")
                            st.rerun()
                        show_api_error(resp)
                choices = L.hazard_choices(catalogue, code, hazards)
                if not catalogue.get(code):
                    st.caption(f"No household hazards are defined for {disease_label}.")
                elif not choices:
                    st.caption("Every hazard in the catalogue for this disease is already recorded.")
                else:
                    p1, p2 = st.columns([5, 1], vertical_alignment="bottom")
                    pick = p1.selectbox(
                        "Add a hazard from the catalogue", choices, key=f"hz_pick_{code}_{pid}",
                        format_func=lambda h: f"{h.get('label', h.get('code'))} (+{h.get('e_j')})"
                                              f"{' · ' + h['status'] if h.get('status') else ''}")
                    if p2.button("Add hazard", key="hz_add_btn", use_container_width=True):
                        resp = docpage_api.add_hazard(code, pick["code"], patient_id=pid)
                        if L.is_ok(resp):
                            flash("success", "Hazard recorded.")
                            st.rerun()
                        show_api_error(resp)

        # ---------------- 3 · Biomarkers -----------------------------------------
        with st.container(border=True):
            st.markdown(f"#### 3 · Biomarkers — {disease_label}")
            latest = docpage_api.get_latest_biomarkers(code, pid)
            if L.is_ok(latest):
                labels = {f["column"]: f["label"] for f in L.BIOMARKER_FIELDS[code]}
                st.caption(f"Latest stored record #{latest.get('metric_id')} · {latest.get('recorded_at', '')}")
                values = latest.get("values") or {}
                if values:
                    st.dataframe(pd.DataFrame([{"Measurement": labels.get(k, k), "Value": v}
                                               for k, v in values.items() if v is not None]),
                                 hide_index=True, use_container_width=True)
            elif (L.error_info(latest) or {}).get("code") == "NO_BIOMARKERS" or (latest or {}).get("_http_status") == 404:
                st.info("No biomarkers stored for this disease yet.")
            else:
                show_api_error(latest)

            with st.form(f"bm_form_{code}_{pid}"):
                st.caption("Leave a test empty when it was not done. The server checks every value against the "
                           "data-dictionary range and names any value outside it.")
                entered = {}
                fields = L.BIOMARKER_FIELDS[code]
                with st.expander("Used by the model", expanded=True):
                    cols = st.columns(2)
                    for i, field in enumerate([f for f in fields if f["model_input"]]):
                        with cols[i % 2]:
                            entered[field["column"]] = biomarker_input(field, code, pid)
                with st.expander("Other measurements (stored, not used by this model)", expanded=False):
                    cols = st.columns(2)
                    for i, field in enumerate([f for f in fields if not f["model_input"]]):
                        with cols[i % 2]:
                            entered[field["column"]] = biomarker_input(field, code, pid)
                if st.form_submit_button("Save biomarkers"):
                    values = L.clean_biomarker_values(entered)
                    if not values:
                        st.error("Enter at least one value.")
                    else:
                        resp = docpage_api.save_biomarkers(code, pid, values)
                        if L.is_ok(resp):
                            flash("success", f"Biomarkers saved (record #{resp.get('metric_id')}).")
                            st.rerun()
                        show_api_error(resp, disease=code)

        # ---------------- 4 · Run the model ---------------------------------------
        with st.container(border=True):
            st.markdown("#### 4 · Diagnostic Risk Assessment")
            st.caption("The server builds the model input from the stored biomarkers, family history, hazards, "
                       "age and sex, and writes an audit entry for every run.")
            if st.button("🧠 Run the model", key="run_model_btn", type="primary", use_container_width=True):
                resp = docpage_api.infer_cdss(pid, code)
                if L.is_ok(resp):
                    st.session_state["last_inference"] = resp
                    st.session_state["last_inference_pid"] = pid
                    st.session_state["last_inference_modality"] = code
                else:
                    show_api_error(resp)
            inference = st.session_state.get("last_inference")
            if (inference and st.session_state.get("last_inference_pid") == pid
                    and st.session_state.get("last_inference_modality") == code):
                render_results(inference, disease_label)
            else:
                st.info(f"Run the model to see this patient's {disease_label} risk.")

        # ---------------- 5 · Consultation -----------------------------------------
        with st.container(border=True):
            st.markdown("#### 5 · Consultation")
            st.caption("Saving closes the patient's queue ticket.")
            with st.form(f"cons_form_{pid}"):
                cons_dir = st.text_area("Directives*", key=f"cons_dir_{pid}", height=90)
                cons_notes = st.text_area("Notes (optional, up to 5000 characters)", key=f"cons_notes_{pid}",
                                          max_chars=5000, height=70)
                if st.form_submit_button("Save consultation"):
                    try:
                        body = L.build_consultation_payload(pid, cons_dir, cons_notes)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        resp = docpage_api.save_consultation(pid, body["directives"], body["notes"])
                        if L.is_ok(resp):
                            closed = " The queue ticket is closed." if resp.get("queue_ticket_closed") else ""
                            flash("success", f"Consultation {resp.get('consultation_uid')} saved.{closed}")
                            st.rerun()
                        show_api_error(resp)
            cons_resp = docpage_api.get_consultations(pid)
            history = (cons_resp or {}).get("consultations") or [] if L.is_ok(cons_resp) else []
            with st.expander(f"Consultation history ({len(history)})"):
                if not L.is_ok(cons_resp):
                    show_api_error(cons_resp)
                for c in history:
                    st.markdown(f"**{c.get('created_at', '')}** · `{c.get('consultation_uid', '')}`")
                    st.write(c.get("directives"))
                    if c.get("notes"):
                        st.caption(c["notes"])

        # ---------------- 6 · Sign the encounter ------------------------------------
        with st.container(border=True):
            st.markdown("#### 6 · Prescribe Treatment & Sign the Encounter")
            st.caption("The server seals the whole record (care plan included) and links it to the baseline itself.")
            inference = st.session_state.get("last_inference")
            blockers = L.commit_blockers(phase, inference, st.session_state.get("last_inference_pid"), pid)
            for reason in blockers:
                st.info(reason)
            with st.form(f"care_plan_form_{pid}"):
                cp_dir = st.text_area("Clinical directive & orders*", key=f"cp_dir_{pid}", height=100)
                cp_rx = st.text_input("Prescribed medications (comma-separated)", key=f"cp_rx_{pid}")
                cp_life = st.text_area("Lifestyle advice (optional)", key=f"cp_life_{pid}", height=70)
                if phase is not None:
                    st.caption(f"Will be saved as a {L.encounter_type_for(phase)} encounter.")
                if st.form_submit_button("Sign & Finalize Clinical Encounter", type="primary", disabled=bool(blockers)):
                    if not (cp_dir or "").strip():
                        st.error("Write the clinical directive before signing.")
                    else:
                        summary = L.summarize_inference(inference)
                        care_plan = L.build_care_plan(
                            cp_dir, cp_rx, cp_life, tier=summary["tier"],
                            condition=L.MODALITY_LABELS.get(st.session_state.get("last_inference_modality")))
                        resp = docpage_api.commit_encounter(pid, L.build_commit_payload(pid, phase, inference, care_plan))
                        if L.is_ok(resp):
                            receipt = L.strip_meta(resp)
                            st.session_state["last_commit_receipt"] = receipt
                            st.session_state["last_commit_pid"] = pid
                            st.session_state["last_inference"] = None
                            append_audit("ENCOUNTER_COMMITTED", receipt)
                            flash("success", f"Encounter {receipt.get('encounter_id')} sealed.")
                            st.rerun()
                        show_api_error(resp)

            receipt = st.session_state.get("last_commit_receipt")
            if receipt and st.session_state.get("last_commit_pid") == pid:
                st.markdown("##### 🔒 Sealed encounter receipt")
                st.json(receipt)
                if st.button("Check seal", key="seal_check_btn"):
                    check = docpage_api.verify_encounter(receipt.get("encounter_id"))
                    if not L.is_ok(check):
                        show_api_error(check)
                    elif check.get("seal_valid"):
                        st.success("Seal valid: the stored record matches what was signed.")
                    else:
                        st.error("Seal check failed: the stored record was changed after signing.")

    with tab_cdss:
        st.write("")
        notice = st.session_state.pop("cdss_notice", None)
        if notice:
            st.success(notice)
        show_flash()
        with st.container(border=True):
            col_info, col_pick = st.columns([3, 1])
            with col_pick:
                st.session_state.setdefault("consult_pid_input", int(st.session_state["active_patient_id"] or 1))
                typed_pid = st.number_input("Patient ID #", min_value=1, step=1, key="consult_pid_input")
                if st.button("Open patient", key="open_pid_btn", use_container_width=True):
                    open_patient(typed_pid)
                    st.rerun()
        active_pid = st.session_state.get("active_patient_id")
        if active_pid is None:
            with col_info:
                st.info("Call a patient from the queue, or type a patient ID and press Open patient.")
        else:
            render_workspace(int(active_pid), col_info)

# ==============================================================================
# 5. SIDEBAR (this session's sealed encounters)
# ==============================================================================
with st.sidebar:
    st.markdown("### 🩺 Clinical Context")
    st.markdown(f"**Doctor:** {active_doc['name']}")
    st.markdown("---")
    if st.session_state["audit_trail"]:
        st.markdown("### 📋 Encounters sealed this session")
        for audit in reversed(st.session_state["audit_trail"][-5:]):
            st.markdown(f"**{audit['payload'].get('encounter_id', audit['audit_id'])}** - {audit['timestamp_utc']}")
            seal = audit["payload"].get("cryptographic_hash")
            if seal:
                st.caption(f"Seal: {str(seal)[:10]}...")
