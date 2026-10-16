"""Run each Streamlit page top to bottom against sample backend replies (shapes from the API guide)."""
import copy
import os
import runpy
import sys
import unittest

from frontend.test import fakes

st = fakes.install()

from frontend import docpage_api  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRONTEND = os.path.join(ROOT, "frontend")
VIEWS = os.path.join(FRONTEND, "views")
for p in (ROOT, FRONTEND):
    if p not in sys.path:
        sys.path.insert(0, p)


def ok(body=None, status=200):
    out = dict(body or {})
    out["_http_status"] = status
    return out


def err(code, message, status=400, fields=None):
    return {"status": "error", "code": code, "error": message, "fields": fields or [], "_http_status": status}


TICKET = {"ticket_id": 12, "queue_no": "Q-03", "queue_date": "2026-10-15", "patient_id": 5, "name": "Patient #5",
          "time_in": "02:41 PM", "urgency": "🟢 Routine", "complaint": "Routine follow-up", "vitals": "Not recorded",
          "watch_flag": "None declared", "status": "WAITING", "lifecycle_status": "In Waiting Room"}
FHRS = {"bio_fhrs": 2.0, "pedigree_sum": 1.5, "clustering": 0.5, "environmental_modifier": 0.15,
        "adjusted_fhrs": 2.3, "band": 2, "band_label": "Moderate Risk", "relatives_counted": 2,
        "hazards": [{"code": "SMOKE", "e_j": 0.15}], "skipped_records": []}
CATALOGUE = {"cvd": [{"code": "SMOKE", "label": "Household smoking", "e_j": 0.15, "status": "dictionary"},
                     {"code": "SALT", "label": "High-salt cooking", "e_j": 0.10, "status": "assumption"}],
             "t2d": [], "resp": [], "neuro": []}
INFER = ok({"status": "success", "risk": {"score": 72.0, "probability": 0.72, "tier": "HIGH"}, "is_stub": False,
            "missing_features": ["ldl"], "biomarker_source": "database",
            "shap": {"drivers": [{"display_name": "Systolic BP", "shap_value": 0.41},
                                 {"display_name": "HDL", "shap_value": -0.22}]},
            "fhrs_decomposition": FHRS,
            "fairness": {"source": "training_cv", "passed": False, "disparity_detected": True, "gap": 0.102,
                         "threshold": 0.05, "subgroup_flags": []},
            "calibration": {"method": "sigmoid", "brier_score": 0.071, "ece": 0.019, "confidence": None},
            "audit_id": "AUD-9", "model_version": "cvd-v3"})

DEFAULT_REPLIES = {
    "get_doctor_queue": ok({"status": "success", "queue": [TICKET]}),
    "get_doctor_patient": ok({"patient_id": 5, "first_name": "Ana", "last_name": "Cruz",
                              "date_of_birth": "1980-05-02", "biological_sex": "Female"}),
    "get_baseline": {"has_baseline": False, "_http_status": 404},
    "get_patient_family_history": ok({"family_history": [
        {"record_id": 12, "disease_domain": "cvd", "specific_diagnosis": "MI", "relationship_tier": 1,
         "relationship_weight": 0.5, "onset_classification": "early", "onset_weight": 2.0,
         "age_at_diagnosis": 48, "shared_environment": True, "is_verified": False, "recorded_at": "2026-10-15"},
        {"record_id": 13, "disease_domain": "t2d", "specific_diagnosis": None, "relationship_tier": 2,
         "onset_classification": "typical", "age_at_diagnosis": None, "shared_environment": False,
         "is_verified": True, "recorded_at": "2026-10-15"}]}),
    "get_fhrs": ok({"fhrs": FHRS}),
    "get_hazards": ok({"hazards": [{"id": 3, "disease_domain": "cvd", "hazard_code": "SMOKE",
                                    "label": "Household smoking"}], "catalogue": CATALOGUE}),
    "get_latest_biomarkers": ok({"metric_id": 1, "recorded_at": "2026-10-15T10:00:00+08:00",
                                 "values": {"sbp": 142, "dbp": 91}}),
    "get_consultations": ok({"consultations": [{"consultation_uid": "CONS-0", "doctor_id": 2,
                                                "directives": "Repeat labs", "notes": "", "created_at": "2026-10-01"}]}),
    "get_models_status": ok({"cvd": {"loaded": True, "model_version": "cvd-v3", "version_warnings": []},
                             "t2d": {"loaded": True, "model_version": "t2d-v3"},
                             "resp": {"loaded": True}, "neuro": {"loaded": True}}),
    "infer_cdss": INFER,
    "save_biomarkers": ok({"metric_id": 2, "values": {"sbp": 140}}, 201),
    "submit_patient_family_history": ok({"record_id": 14, "is_verified": False}, 201),
    "verify_family_history": ok({}),
    "add_hazard": ok({"id": 4}, 201),
    "delete_hazard": ok({}),
    "set_biological_sex": ok({}),
    "save_consultation": ok({"consultation_uid": "CONS-1", "patient_id": 5, "doctor_id": 2,
                             "queue_ticket_closed": True}, 201),
    "commit_encounter": ok({"encounter_id": "ENC-1", "cryptographic_hash": "abc123", "parent_baseline_hash": None,
                            "committed_at_utc": "2026-10-15T07:00:00Z", "envelope_status": "SEALED"}, 201),
    "verify_encounter": ok({"seal_valid": True, "parent_found": True}),
    "get_latest_patient_encounter": ok({"has_encounter": True, "encounter": {
        "encounter_uid": "ENC-0", "record_type": "BASELINE", "created_at": "2026-10-01", "doctor_name": "Dr. Reyes",
        "care_plan": {"clinical_directive": "Low-salt diet", "medications": ["Amlodipine 5mg"],
                      "risk_classification": "HIGH", "primary_condition": "Cardiovascular"},
        "cdss_payload": {"risk": {"score": 72.0, "tier": "HIGH"}}}}),
    "get_patient_encounters_list": ok({"count": 1, "encounters": [
        {"encounter_uid": "ENC-0", "record_type": "BASELINE", "created_at": "2026-10-01", "doctor_name": "Dr. Reyes",
         "cryptographic_hash": "abc", "summary_directive": "Low-salt diet"}]}),
    "get_active_queue": ok({"queue": []}),
    "submit_patient_checkin": ok({"ticket": dict(TICKET)}, 201),
    "cancel_patient_checkin": ok({}),
    "change_user_password": ok({}),
    "perform_backend_logout": ok({}),
    "get_directory": ok({"_items": [
        {"user_id": 1, "username": "admin", "role": "ADMIN", "is_locked": False, "created_at": "2026-10-01"},
        {"user_id": 7, "username": "drcruz", "role": "DOCTOR", "is_locked": True, "created_at": "2026-10-02"},
        {"user_id": 9, "username": "ana", "role": "PATIENT", "is_locked": False, "created_at": "2026-10-03"}]}),
    "provision_doctor": ok({"user_id": 10, "doctor_id": 4, "status": "PENDING_VERIFICATION"}, 201),
    "verify_doctor": ok({}),
    "unlock_user": ok({}),
    "reload_models": ok({"audit_id": "AUD-R"}),
    "get_health": ok({"status": "ok", "database": "up"}),
}


class FakeBackend:
    """Replaces every docpage_api function with a recorder that returns a canned reply."""

    def __init__(self, **overrides):
        self.replies = copy.deepcopy(DEFAULT_REPLIES)
        self.replies.update(overrides)
        self.calls = []
        self._saved = {}

    def __enter__(self):
        for name in self.replies:
            self._saved[name] = getattr(docpage_api, name, None)
            setattr(docpage_api, name, self._make(name))
        return self

    def __exit__(self, *exc):
        for name, fn in self._saved.items():
            if fn is None:
                delattr(docpage_api, name)
            else:
                setattr(docpage_api, name, fn)

    def _make(self, name):
        def fn(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return copy.deepcopy(self.replies[name])
        return fn

    def called(self, name):
        return [(a, k) for n, a, k in self.calls if n == name]

    def writes(self):
        read_prefixes = ("get_",)
        return [n for n, _, _ in self.calls if not n.startswith(read_prefixes)]


def run_page(name):
    """Run views/<name>.py once. Returns 'done', 'rerun' or 'stop'."""
    st.new_run()
    try:
        runpy.run_path(os.path.join(VIEWS, name), run_name="__page__")
        return "done"
    except fakes.RerunScript:
        return "rerun"
    except fakes.StopScript:
        return "stop"


def login_as(role, profile):
    st.reset()
    st.session_state.update({"authenticated": True, "token": "tok", "jwt_token": "tok", "user_role": role,
                             "user_id": profile.get("user_id", 1), "username": "user", "user_profile": profile})


DOCTOR = {"user_id": 2, "doctor_id": 2, "first_name": "Luis", "last_name": "Reyes", "specialization": "Cardiology",
          "license_number": "PRC 1234567", "hospital_affiliation": "Lucerna Medica", "email": "luis@gmail.com"}
PATIENT = {"user_id": 30, "patient_id": 5, "first_name": "Ana", "last_name": "Cruz", "date_of_birth": "1980-05-02",
           "email": "ana@gmail.com", "contact_number": "0917-123-4567"}
ADMIN = {"user_id": 1, "first_name": "Sys", "last_name": "Admin", "email": "admin@clinic.ph"}


# ==============================================================================
# DOCTOR PAGE
# ==============================================================================
class DoctorPage(unittest.TestCase):
    def open_patient(self):
        login_as("DOCTOR", DOCTOR)
        st.session_state["active_patient_id"] = 5

    def test_no_token_stops_before_any_call(self):
        st.reset()
        with FakeBackend() as be:
            self.assertEqual(run_page("docpage.py"), "stop")
        self.assertEqual(be.calls, [])

    def test_queue_reads_queue_key_and_calls_patient(self):
        login_as("DOCTOR", DOCTOR)
        st.clicks = {"call_q_5"}
        with FakeBackend():
            self.assertEqual(run_page("docpage.py"), "rerun")
        self.assertEqual(st.session_state["active_patient_id"], 5)

    def test_open_patient_renders_without_writing_anything(self):
        self.open_patient()
        with FakeBackend() as be:
            self.assertEqual(run_page("docpage.py"), "done")
        self.assertEqual(be.writes(), [])
        self.assertTrue(any("Cruz, Ana" in t for t in st.drawn()))
        self.assertEqual(be.called("get_doctor_patient")[0][0], (5,))

    def test_unknown_patient_shows_not_found(self):
        self.open_patient()
        with FakeBackend(get_doctor_patient={"error": "Patient not found", "_http_status": 404}) as be:
            run_page("docpage.py")
        self.assertTrue(any("not found" in t.lower() for t in st.drawn("error")))
        self.assertEqual(be.called("get_baseline"), [])

    def test_run_model_uses_stored_data_and_shows_real_result(self):
        self.open_patient()
        st.clicks = {"run_model_btn"}
        with FakeBackend() as be:
            run_page("docpage.py")
        self.assertEqual(be.called("infer_cdss")[0][0], (5, "cvd"))
        self.assertEqual(st.session_state["last_inference_pid"], 5)
        st.clicks = set()
        with FakeBackend():
            run_page("docpage.py")
        drawn = " ".join(st.drawn())
        self.assertIn("Moderate Risk", drawn)          # FHRS band from the API
        self.assertIn("ldl", drawn)                    # missing feature listed
        self.assertTrue(any("0.102" in t for t in st.drawn("warning")))  # disparity shown

    def test_stub_shows_warning_not_a_score(self):
        self.open_patient()
        stub = ok({"is_stub": True, "risk": {"score": None, "probability": None, "tier": "UNAVAILABLE"}})
        st.clicks = {"run_model_btn"}
        with FakeBackend(infer_cdss=stub):
            run_page("docpage.py")
            st.clicks = set()
            run_page("docpage.py")
        self.assertTrue(any("not loaded" in t.lower() for t in st.drawn("warning")))
        self.assertFalse(any("RISK" in t for t in st.drawn("markdown") if "tier-badge" in t))

    def test_no_biomarkers_error_is_explained(self):
        self.open_patient()
        st.clicks = {"run_model_btn"}
        with FakeBackend(infer_cdss=err("NO_BIOMARKERS", "none", 404)):
            run_page("docpage.py")
        self.assertTrue(any("Save a set of values" in t for t in st.drawn("error")))

    def test_verify_relative(self):
        self.open_patient()
        st.clicks = {"fh_verify_12"}
        with FakeBackend() as be:
            self.assertEqual(run_page("docpage.py"), "rerun")
        self.assertEqual(be.called("verify_family_history")[0][0], (12,))

    def test_add_relative_sends_codes_not_weights(self):
        self.open_patient()
        st.clicks = {"Save relative"}
        st.inputs = {"fh_disease_5": "t2d", "fh_tier_5": "Tier 2 · second-degree (grandparent, aunt/uncle, half-sibling)",
                     "fh_onset_5": "Early", "fh_age_5": 52}
        with FakeBackend() as be:
            run_page("docpage.py")
        payload = be.called("submit_patient_family_history")[0][0][0]
        self.assertEqual((payload["disease_domain"], payload["relationship_tier"], payload["onset_classification"]),
                         ("t2d", 2, "early"))
        self.assertEqual(payload["patient_id"], 5)
        self.assertNotIn("relationship_weight", payload)

    def test_hazard_picker_offers_only_unrecorded_catalogue_items(self):
        self.open_patient()
        st.clicks = {"hz_add_btn"}
        with FakeBackend() as be:
            run_page("docpage.py")
        self.assertEqual(be.called("add_hazard")[0], (("cvd", "SALT"), {"patient_id": 5}))

    def test_remove_hazard(self):
        self.open_patient()
        st.clicks = {"hz_del_3"}
        with FakeBackend() as be:
            run_page("docpage.py")
        self.assertEqual(be.called("delete_hazard")[0][0], (3,))

    def test_set_biological_sex(self):
        self.open_patient()
        st.clicks = {"sex_save_btn"}
        st.inputs = {"sex_pick_5": "Male"}
        with FakeBackend() as be:
            run_page("docpage.py")
        self.assertEqual(be.called("set_biological_sex")[0][0], (5, "Male"))

    def test_save_biomarkers_sends_only_entered_values(self):
        self.open_patient()
        st.clicks = {"Save biomarkers"}
        st.inputs = {"bm_cvd_sbp_5": 141.0, "bm_cvd_ldl_5": 160.0}
        with FakeBackend() as be:
            run_page("docpage.py")
        self.assertEqual(be.called("save_biomarkers")[0][0], ("cvd", 5, {"sbp": 141.0, "ldl": 160.0}))

    def test_out_of_range_names_the_field(self):
        self.open_patient()
        st.clicks = {"Save biomarkers"}
        st.inputs = {"bm_cvd_sbp_5": 400.0}
        bad = err("VALIDATION_FAILED", "sbp must be between 70 and 220 mmHg (got 400)", fields=["sbp"])
        with FakeBackend(save_biomarkers=bad):
            run_page("docpage.py")
        errors = " ".join(st.drawn("error"))
        self.assertIn("70 and 220", errors)
        self.assertIn("Systolic blood pressure", errors)

    def test_consultation_save(self):
        self.open_patient()
        st.clicks = {"Save consultation"}
        st.inputs = {"cons_dir_5": "Repeat lipid panel in 3 months", "cons_notes_5": "Stable"}
        with FakeBackend() as be:
            self.assertEqual(run_page("docpage.py"), "rerun")
        self.assertEqual(be.called("save_consultation")[0][0], (5, "Repeat lipid panel in 3 months", "Stable"))

    def test_commit_blocked_before_inference(self):
        self.open_patient()
        st.clicks = {"Sign & Finalize Clinical Encounter"}
        st.inputs = {"cp_dir_5": "Low-salt diet", "cp_rx_5": "Amlodipine"}
        with FakeBackend() as be:
            run_page("docpage.py")
        self.assertEqual(be.called("commit_encounter"), [])

    def test_commit_after_inference_is_a_baseline_for_new_patient(self):
        self.open_patient()
        st.session_state.update({"last_inference": copy.deepcopy(INFER), "last_inference_pid": 5,
                                 "last_inference_modality": "cvd"})
        st.clicks = {"Sign & Finalize Clinical Encounter"}
        st.inputs = {"cp_dir_5": "Low-salt diet", "cp_rx_5": "Amlodipine 5mg, Atorvastatin"}
        with FakeBackend() as be:
            self.assertEqual(run_page("docpage.py"), "rerun")
        pid, body = be.called("commit_encounter")[0][0]
        self.assertEqual((pid, body["encounter_type"]), (5, "BASELINE"))
        self.assertEqual(body["care_plan"]["medications"], ["Amlodipine 5mg", "Atorvastatin"])
        self.assertNotIn("_http_status", body["cdss_payload_snapshot"])
        self.assertEqual(st.session_state["last_commit_receipt"]["encounter_id"], "ENC-1")

    def test_followup_when_baseline_exists(self):
        self.open_patient()
        st.session_state.update({"last_inference": copy.deepcopy(INFER), "last_inference_pid": 5,
                                 "last_inference_modality": "cvd"})
        st.clicks = {"Sign & Finalize Clinical Encounter"}
        st.inputs = {"cp_dir_5": "Continue", "cp_rx_5": "Amlodipine"}
        baseline = ok({"has_baseline": True, "encounter_id": "ENC-0", "baseline_hash": "h0",
                       "established_at_utc": "2026-10-01T00:00:00Z"})
        with FakeBackend(get_baseline=baseline) as be:
            run_page("docpage.py")
        self.assertEqual(be.called("commit_encounter")[0][0][1]["encounter_type"], "FOLLOWUP")

    def test_no_mock_doctor_profile(self):
        login_as("DOCTOR", {})
        with FakeBackend():
            run_page("docpage.py")
        self.assertFalse(any("Jenkins" in t for t in st.drawn()))


# ==============================================================================
# PATIENT PAGE
# ==============================================================================
class PatientPage(unittest.TestCase):
    def test_renders_care_plan_from_latest_encounter(self):
        login_as("PATIENT", PATIENT)
        with FakeBackend() as be:
            self.assertEqual(run_page("patientpage.py"), "done")
        self.assertEqual(be.writes(), [])
        self.assertTrue(any("Low-salt diet" in t for t in st.drawn()))
        self.assertTrue(any("Amlodipine 5mg" in t for t in st.drawn()))

    def test_family_history_sends_codes_not_weights(self):
        login_as("PATIENT", PATIENT)
        st.clicks = {"📥 Save Family Health Record"}
        st.inputs = {"pf_disease": "Type 2 Diabetes Mellitus", "pf_tier": "Extended Family (Grandparent, Aunt, Uncle)",
                     "pf_onset": "60+ (Late)"}
        with FakeBackend() as be:
            run_page("patientpage.py")
        payload = be.called("submit_patient_family_history")[0][0][0]
        self.assertEqual(payload, {"disease_domain": "t2d", "relationship_tier": 2, "onset_classification": "late",
                                   "shared_environment": False})

    def test_family_history_failure_is_not_reported_as_success(self):
        login_as("PATIENT", PATIENT)
        st.clicks = {"📥 Save Family Health Record"}
        with FakeBackend(submit_patient_family_history=None):
            run_page("patientpage.py")
        self.assertEqual(st.drawn("success"), [])
        self.assertTrue(st.drawn("error"))

    def test_checkin_failure_does_not_mark_checked_in(self):
        login_as("PATIENT", PATIENT)
        st.clicks = {"📥 Get Queue Ticket (Check-In)"}
        with FakeBackend(submit_patient_checkin=None):
            run_page("patientpage.py")
        self.assertTrue(st.drawn("error"))
        self.assertFalse(any("ticket is active" in t for t in st.drawn("success")))

    def test_checkin_success(self):
        login_as("PATIENT", PATIENT)
        st.clicks = {"📥 Get Queue Ticket (Check-In)"}
        with FakeBackend() as be:
            self.assertEqual(run_page("patientpage.py"), "rerun")
        self.assertEqual(len(be.called("submit_patient_checkin")), 1)

    def test_waiting_ticket_from_backend_and_undo_uses_patient_id(self):
        login_as("PATIENT", PATIENT)
        st.clicks = {"↩ Undo Check-In"}
        with FakeBackend(get_active_queue=ok({"queue": [TICKET]})) as be:
            run_page("patientpage.py")
        self.assertEqual(be.called("cancel_patient_checkin")[0][0], (5,))

    def test_patient_can_add_hazard_from_catalogue(self):
        login_as("PATIENT", PATIENT)
        st.clicks = {"pt_hz_add"}
        with FakeBackend() as be:
            run_page("patientpage.py")
        self.assertEqual(be.called("add_hazard")[0][0], ("cvd", "SALT"))

    def test_profile_update_does_not_pretend_to_save(self):
        login_as("PATIENT", PATIENT)
        st.clicks = {"Update Information"}
        with FakeBackend():
            run_page("patientpage.py")
        self.assertFalse(any("successfully updated" in t for t in st.drawn("success")))


# ==============================================================================
# ADMIN PAGE AND SHARED UI
# ==============================================================================
class AdminPage(unittest.TestCase):
    def test_renders_real_directory_and_no_mock_numbers(self):
        login_as("ADMIN", ADMIN)
        with FakeBackend() as be:
            self.assertEqual(run_page("adminpage.py"), "done")
        self.assertEqual(be.writes(), [])
        drawn = " ".join(st.drawn())
        self.assertIn("drcruz", drawn)
        self.assertNotIn("888", drawn)
        self.assertNotIn("1XXX.XX", drawn)

    def test_unlock_locked_account(self):
        login_as("ADMIN", ADMIN)
        st.clicks = {"unlock_7"}
        with FakeBackend() as be:
            run_page("adminpage.py")
        self.assertEqual(be.called("unlock_user")[0][0], (7,))

    def test_provision_doctor(self):
        login_as("ADMIN", ADMIN)
        st.clicks = {"Submit Provisioning"}
        st.inputs = {"doc_username": "drcruz2", "doc_password": "temp-pass-123", "doc_first_name": "Ana",
                     "doc_last_name": "Cruz", "doc_address": "Manila", "doc_prc": "1234567",
                     "doc_email": "ana@gmail.com", "doc_contact": "0917-123-4567", "em_name": "Ben Cruz",
                     "em_contact": "0917-765-4321"}
        with FakeBackend() as be:
            run_page("adminpage.py")
        body = be.called("provision_doctor")[0][0][0]
        self.assertEqual((body["username"], body["license_number"]), ("drcruz2", "PRC 1234567"))
        self.assertIn("emergency_relation", body)

    def test_verify_doctor_by_id(self):
        login_as("ADMIN", ADMIN)
        st.clicks = {"verify_doc_btn"}
        st.inputs = {"verify_doc_id": 4}
        with FakeBackend() as be:
            run_page("adminpage.py")
        self.assertEqual(be.called("verify_doctor")[0][0], (4,))


class Logout(unittest.TestCase):
    def test_logout_clears_token_and_patient_data(self):
        login_as("PATIENT", PATIENT)
        st.session_state["night_light"] = True
        st.session_state["fhrs_data"] = [1]
        st.clicks = {"nav_btn_logout"}
        with FakeBackend() as be:
            run_page("patientpage.py")
        self.assertEqual(len(be.called("perform_backend_logout")), 1)
        self.assertNotIn("token", st.session_state)
        self.assertNotIn("fhrs_data", st.session_state)
        self.assertTrue(st.session_state["night_light"])


if __name__ == "__main__":
    unittest.main()
