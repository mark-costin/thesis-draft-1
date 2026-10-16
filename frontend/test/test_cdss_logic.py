"""Rules the frontend must follow to stay in sync with the backend (Frontend API Guide, 2026-10-15)."""
import datetime
import unittest

from frontend import cdss_logic as L


def ok(body=None, status=200):
    out = dict(body or {})
    out["_http_status"] = status
    return out


def err(code, message="x", status=400, fields=None, retryable=False):
    return {"status": "error", "code": code, "error": message, "fields": fields or [],
            "retryable": retryable, "_http_status": status}


class ModalityCodes(unittest.TestCase):
    def test_every_ui_label_maps_to_a_backend_disease_code(self):
        self.assertEqual(sorted(L.MODALITY_CODES.values()), ["cvd", "neuro", "resp", "t2d"])

    def test_cvd_label(self):
        self.assertEqual(L.MODALITY_CODES["Cardiovascular Diseases (Hypertension / CVD)"], "cvd")

    def test_no_label_sends_multi_modal(self):
        self.assertNotIn("MULTI_MODAL", L.MODALITY_CODES.values())


class FamilyHistoryPayload(unittest.TestCase):
    def test_sends_tier_and_onset_codes(self):
        p = L.build_family_history_payload("t2d", 1, "early")
        self.assertEqual(p, {"disease_domain": "t2d", "relationship_tier": 1, "onset_classification": "early"})

    def test_never_sends_weights(self):
        p = L.build_family_history_payload("cvd", 2, "severe_early", shared_environment=True,
                                           age_at_diagnosis=40, specific_diagnosis="MI")
        self.assertNotIn("relationship_weight", p)
        self.assertNotIn("onset_weight", p)

    def test_optional_fields_included_only_when_given(self):
        p = L.build_family_history_payload("cvd", 2, "typical", age_at_diagnosis=55, patient_id=7)
        self.assertEqual(p["age_at_diagnosis"], 55)
        self.assertEqual(p["patient_id"], 7)
        self.assertNotIn("specific_diagnosis", p)

    def test_rejects_unknown_disease(self):
        with self.assertRaises(ValueError):
            L.build_family_history_payload("oncology", 1, "early")

    def test_rejects_tier_outside_1_to_3(self):
        with self.assertRaises(ValueError):
            L.build_family_history_payload("cvd", 4, "early")

    def test_rejects_unknown_onset(self):
        with self.assertRaises(ValueError):
            L.build_family_history_payload("cvd", 1, "Very early onset")

    def test_rejects_age_above_120(self):
        with self.assertRaises(ValueError):
            L.build_family_history_payload("cvd", 1, "early", age_at_diagnosis=130)

    def test_patient_labels_map_to_codes(self):
        self.assertEqual(L.PATIENT_TIER_CHOICES["Immediate Family (Parent, Sibling, Child)"], 1)
        self.assertEqual(L.PATIENT_ONSET_CHOICES["Childhood / Teens (Very Early)"], "severe_early")
        self.assertEqual(L.PATIENT_ONSET_CHOICES["60+ (Late)"], "late")


class HazardPicker(unittest.TestCase):
    CATALOGUE = {"cvd": [{"code": "SMOKE", "label": "Household smoking", "e_j": 0.15, "status": "dictionary"},
                         {"code": "SALT", "label": "High-salt cooking", "e_j": 0.1, "status": "assumption"}],
                 "neuro": []}

    def test_choices_come_from_catalogue_for_that_disease(self):
        codes = [c["code"] for c in L.hazard_choices(self.CATALOGUE, "cvd")]
        self.assertEqual(codes, ["SMOKE", "SALT"])

    def test_already_recorded_hazards_are_not_offered(self):
        recorded = [{"id": 3, "disease_domain": "cvd", "hazard_code": "SMOKE"}]
        codes = [c["code"] for c in L.hazard_choices(self.CATALOGUE, "cvd", recorded)]
        self.assertEqual(codes, ["SALT"])

    def test_disease_without_hazards_gives_no_choices(self):
        self.assertEqual(L.hazard_choices(self.CATALOGUE, "neuro"), [])
        self.assertEqual(L.hazard_choices(self.CATALOGUE, "t2d"), [])

    def test_recorded_hazards_filtered_by_disease(self):
        recorded = [{"id": 1, "disease_domain": "cvd", "hazard_code": "SMOKE"},
                    {"id": 2, "disease_domain": "t2d", "hazard_code": "SUGAR"}]
        self.assertEqual([h["id"] for h in L.recorded_hazards(recorded, "t2d")], [2])


class Errors(unittest.TestCase):
    def test_2xx_is_ok(self):
        self.assertTrue(L.is_ok(ok({"metric_id": 1}, 201)))

    def test_none_is_not_ok(self):
        self.assertFalse(L.is_ok(None))

    def test_error_reply_is_not_ok(self):
        self.assertFalse(L.is_ok(err("NO_BIOMARKERS", status=404)))

    def test_error_info_reads_code_message_fields(self):
        info = L.error_info(err("VALIDATION_FAILED", "hba1c must be between 4.0 and 15.0 % (got 3.5)",
                                fields=["hba1c"]))
        self.assertEqual(info["code"], "VALIDATION_FAILED")
        self.assertEqual(info["fields"], ["hba1c"])
        self.assertIn("4.0 and 15.0", info["message"])

    def test_older_reply_without_code_is_generic(self):
        info = L.error_info({"error": "Patient not found", "_http_status": 404})
        self.assertEqual(info["code"], "ERROR")
        self.assertEqual(info["message"], "Patient not found")

    def test_no_reply_means_backend_unreachable(self):
        info = L.error_info(None)
        self.assertEqual(info["code"], "NETWORK")

    def test_no_biomarkers_explains_what_to_do(self):
        msg = L.friendly_error(err("NO_BIOMARKERS", "none", status=404))
        self.assertIn("Save", msg)

    def test_out_of_range_keeps_backend_message(self):
        msg = L.friendly_error(err("OUT_OF_RANGE", "sbp must be between 70 and 220 mmHg (got 300)"))
        self.assertIn("70 and 220", msg)

    def test_audit_failure_says_nothing_is_shown(self):
        msg = L.friendly_error(err("AUDIT_LOG_FAILED", "x", status=500))
        self.assertIn("audit", msg.lower())


class IdempotencyKeys(unittest.TestCase):
    def test_same_key_reused_until_released(self):
        state = {}
        k1 = L.idempotency_key(state, "consultation:5")
        k2 = L.idempotency_key(state, "consultation:5")
        self.assertEqual(k1, k2)

    def test_new_key_after_release(self):
        state = {}
        k1 = L.idempotency_key(state, "consultation:5")
        L.release_idempotency_key(state, "consultation:5")
        self.assertNotEqual(k1, L.idempotency_key(state, "consultation:5"))

    def test_scopes_do_not_share_keys(self):
        state = {}
        self.assertNotEqual(L.idempotency_key(state, "a"), L.idempotency_key(state, "b"))


class AuthState(unittest.TestCase):
    def test_clears_everything_but_display_preferences(self):
        state = {"token": "t", "jwt_token": "t", "authenticated": True, "fhrs_data": [1],
                 "user_role": "DOCTOR", "night_light": True, "night_light_warmth": 9}
        L.clear_auth_state(state)
        self.assertEqual(state, {"night_light": True, "night_light_warmth": 9, "authenticated": False})


class Baseline(unittest.TestCase):
    def test_existing_baseline_is_phase_2(self):
        self.assertEqual(L.baseline_phase(ok({"has_baseline": True, "baseline_hash": "h"})), 2)

    def test_404_without_baseline_is_phase_1(self):
        self.assertEqual(L.baseline_phase({"has_baseline": False, "_http_status": 404}), 1)

    def test_unreachable_backend_is_unknown(self):
        self.assertIsNone(L.baseline_phase(None))

    def test_encounter_types_match_backend(self):
        self.assertEqual(L.encounter_type_for(1), "BASELINE")
        self.assertEqual(L.encounter_type_for(2), "FOLLOWUP")


INFER_OK = ok({
    "risk": {"score": 63.0, "probability": 0.63, "tier": "MODERATE"},
    "is_stub": False,
    "missing_features": ["ldl"],
    "biomarker_source": "database",
    "shap": {"drivers": [{"display_name": "HbA1c", "shap_value": 0.4},
                         {"display_name": "HDL", "shap_value": -0.6}]},
    "fhrs_decomposition": {"bio_fhrs": 2.0, "adjusted_fhrs": 2.3, "band": 2, "band_label": "Moderate Risk",
                           "relatives_counted": 2, "skipped_records": []},
    "fairness": {"disparity_detected": True, "gap": 0.102, "threshold": 0.05},
    "calibration": {"method": "sigmoid", "brier_score": 0.071, "ece": 0.019},
    "audit_id": "AUD-1", "model_version": "cvd-v3",
    "biomarker_deltas": {"placeholder": True}, "proposed_reanchor": {"placeholder": True, "eligible": True},
})


class InferenceSummary(unittest.TestCase):
    def test_reads_score_and_tier(self):
        s = L.summarize_inference(INFER_OK)
        self.assertEqual((s["score"], s["tier"], s["show_result"]), (63.0, "MODERATE", True))

    def test_stub_never_shows_a_score(self):
        s = L.summarize_inference(ok({"is_stub": True, "risk": {"score": None, "tier": "UNAVAILABLE"}}))
        self.assertFalse(s["show_result"])
        self.assertIsNone(s["score"])

    def test_missing_score_is_not_replaced_by_50(self):
        s = L.summarize_inference(ok({"risk": {"tier": "MODERATE"}}))
        self.assertFalse(s["show_result"])

    def test_drivers_keep_sign_and_sort_by_size(self):
        s = L.summarize_inference(INFER_OK)
        self.assertEqual(s["drivers"], [("HDL", -0.6), ("HbA1c", 0.4)])

    def test_reads_old_alias_names(self):
        s = L.summarize_inference(ok({"risk_assessment": {"score": 20.0, "tier": "LOW"},
                                      "shap_explanations": {"top_risk_drivers": [{"display_name": "Age", "shap_value": 0.1}]},
                                      "fairness_audit": {"disparity_detected": False}}))
        self.assertEqual((s["score"], s["tier"]), (20.0, "LOW"))
        self.assertEqual(s["drivers"], [("Age", 0.1)])

    def test_passes_through_fhrs_fairness_and_missing(self):
        s = L.summarize_inference(INFER_OK)
        self.assertEqual(s["fhrs"]["band_label"], "Moderate Risk")
        self.assertTrue(s["fairness"]["disparity_detected"])
        self.assertEqual(s["missing_features"], ["ldl"])

    def test_placeholders_are_not_exposed(self):
        s = L.summarize_inference(INFER_OK)
        self.assertNotIn("biomarker_deltas", s)
        self.assertNotIn("proposed_reanchor", s)

    def test_fhrs_view_falls_back_to_base_score(self):
        v = L.fhrs_view({"base_score": 1.5, "adjusted_fhrs": 1.5, "band": 1, "band_label": "Mild Risk"})
        self.assertEqual(v["bio_fhrs"], 1.5)


class Biomarkers(unittest.TestCase):
    def test_every_disease_has_fields_named_like_the_db_columns(self):
        self.assertIn("sbp", [f["column"] for f in L.BIOMARKER_FIELDS["cvd"]])
        self.assertIn("fpg", [f["column"] for f in L.BIOMARKER_FIELDS["t2d"]])
        self.assertIn("fev1_fvc_ratio", [f["column"] for f in L.BIOMARKER_FIELDS["resp"]])
        self.assertIn("daily_sleep", [f["column"] for f in L.BIOMARKER_FIELDS["neuro"]])

    def test_model_inputs_are_marked(self):
        cvd_inputs = {f["column"] for f in L.BIOMARKER_FIELDS["cvd"] if f["model_input"]}
        self.assertEqual(cvd_inputs, {"sbp", "dbp", "resting_hr", "total_cholesterol", "hdl", "ldl",
                                      "triglycerides", "egfr"})

    def test_untested_values_are_left_out_not_zeroed(self):
        self.assertEqual(L.clean_biomarker_values({"sbp": 142.0, "ldl": None, "hdl": ""}), {"sbp": 142.0})

    def test_zero_entered_on_purpose_is_kept(self):
        self.assertEqual(L.clean_biomarker_values({"mmrc_score": 0}), {"mmrc_score": 0})


class PatientHeader(unittest.TestCase):
    def test_age_and_sex_come_from_the_profile(self):
        h = L.patient_header({"patient_id": 5, "first_name": "Ana", "last_name": "Cruz",
                              "date_of_birth": "1980-10-16", "biological_sex": "Female"},
                             today=datetime.date(2026, 10, 15))
        self.assertEqual((h["name"], h["age"], h["sex"]), ("Cruz, Ana", 45, "Female"))

    def test_unknown_sex_is_not_invented(self):
        h = L.patient_header({"patient_id": 5}, today=datetime.date(2026, 10, 15))
        self.assertEqual(h["sex"], "Not set")
        self.assertIsNone(h["age"])


class CarePlanAndCommit(unittest.TestCase):
    def test_care_plan_round_trips_to_patient_view(self):
        cp = L.build_care_plan("Low-salt diet", "Amlodipine 5mg, Metformin", "Walk daily",
                               tier="HIGH", condition="Cardiovascular Diseases (Hypertension / CVD)")
        view = L.read_care_plan(cp)
        self.assertEqual(view["directive"], "Low-salt diet")
        self.assertEqual(view["medications"], ["Amlodipine 5mg", "Metformin"])
        self.assertEqual(view["risk_classification"], "HIGH")

    def test_reads_older_care_plan_names(self):
        view = L.read_care_plan({"clinical_order": "Rest", "prescriptions": "A, B"})
        self.assertEqual((view["directive"], view["medications"]), ("Rest", ["A", "B"]))

    def test_commit_payload_uses_backend_encounter_type_and_strips_meta(self):
        p = L.build_commit_payload(5, 2, INFER_OK, {"clinical_directive": "x"})
        self.assertEqual(p["encounter_type"], "FOLLOWUP")
        self.assertNotIn("_http_status", p["cdss_payload_snapshot"])
        self.assertEqual(p["patient_id"], 5)

    def test_commit_blocked_without_inference_for_this_patient(self):
        self.assertTrue(L.commit_blockers(1, None, None, 5))
        self.assertTrue(L.commit_blockers(1, INFER_OK, 9, 5))

    def test_commit_blocked_on_stub_result(self):
        stub = ok({"is_stub": True, "risk": {"score": None, "tier": "UNAVAILABLE"}})
        self.assertTrue(L.commit_blockers(1, stub, 5, 5))

    def test_commit_blocked_when_phase_unknown(self):
        self.assertTrue(L.commit_blockers(None, INFER_OK, 5, 5))

    def test_commit_allowed_with_real_result(self):
        self.assertEqual(L.commit_blockers(2, INFER_OK, 5, 5), [])


class Consultation(unittest.TestCase):
    def test_payload(self):
        self.assertEqual(L.build_consultation_payload(5, "Repeat labs", "ok"),
                         {"patient_id": 5, "directives": "Repeat labs", "notes": "ok"})

    def test_directives_required(self):
        with self.assertRaises(ValueError):
            L.build_consultation_payload(5, "  ", "")

    def test_notes_limited_to_5000(self):
        with self.assertRaises(ValueError):
            L.build_consultation_payload(5, "x", "n" * 5001)


class QueueAndDirectory(unittest.TestCase):
    def test_doctor_queue_reads_queue_key(self):
        self.assertEqual(L.queue_tickets(ok({"status": "success", "queue": [{"ticket_id": 1}]})), [{"ticket_id": 1}])

    def test_queue_error_gives_empty_list(self):
        self.assertEqual(L.queue_tickets(None), [])

    def test_own_waiting_ticket(self):
        resp = ok({"queue": [{"ticket_id": 1, "status": "CANCELLED"}, {"ticket_id": 2, "status": "WAITING"}]})
        self.assertEqual(L.own_waiting_ticket(resp)["ticket_id"], 2)

    def test_directory_accepts_bare_list_or_wrapped(self):
        rows = [{"user_id": 1, "role": "ADMIN"}]
        self.assertEqual(L.directory_rows(ok({"_items": rows})), rows)
        self.assertEqual(L.directory_rows(ok({"users": rows})), rows)


class Provision(unittest.TestCase):
    FORM = {"username": "drcruz", "password": "secret123", "first_name": "Ana", "last_name": "Cruz",
            "address": "Manila", "specialization": "Cardiology", "license_number": "1234567",
            "contact_number": "0917-123-4567", "email": "ana@gmail.com",
            "emergency_contact_name": "Ben Cruz", "emergency_contact_number": "0917-765-4321",
            "emergency_relation": "Spouse", "middle_name": "", "hospital_affiliation": ""}

    def test_complete_form_has_no_missing_fields(self):
        payload, missing = L.build_provision_payload(self.FORM)
        self.assertEqual(missing, [])
        self.assertNotIn("middle_name", payload)   # empty optional fields left out

    def test_missing_required_fields_are_listed(self):
        form = dict(self.FORM, username="", password="")
        _, missing = L.build_provision_payload(form)
        self.assertEqual(missing, ["username", "password"])


class PageHelpers(unittest.TestCase):
    def test_profile_row_without_meta(self):
        self.assertEqual(L.patient_profile(ok({"patient_id": 5, "first_name": "A"})),
                         {"patient_id": 5, "first_name": "A"})

    def test_profile_wrapped_in_patient_key(self):
        self.assertEqual(L.patient_profile(ok({"patient": {"patient_id": 5}})), {"patient_id": 5})

    def test_profile_error_is_none(self):
        self.assertIsNone(L.patient_profile({"error": "Patient not found", "_http_status": 404}))

    def test_models_status_flat_or_nested(self):
        flat = ok({"status": "success", "t2d": {"loaded": False, "problem": "missing file"},
                   "cvd": {"loaded": True, "model_version": "cvd-v3", "version_warnings": ["xgboost 2.1 vs 2.0"]}})
        rows = L.models_status_rows(flat)
        self.assertEqual([r["disease"] for r in rows], ["cvd", "t2d"])
        self.assertEqual(rows[0]["warnings"], ["xgboost 2.1 vs 2.0"])
        self.assertFalse(rows[1]["loaded"])
        nested = ok({"models": {"neuro": {"loaded": True}}})
        self.assertEqual([r["disease"] for r in L.models_status_rows(nested)], ["neuro"])

    def test_bad_fields_named_by_their_form_label(self):
        self.assertEqual(L.field_labels("t2d", ["hba1c", "mystery"]), ["HbA1c", "mystery"])


if __name__ == "__main__":
    unittest.main()
