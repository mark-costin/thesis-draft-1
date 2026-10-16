"""The API client must call each backend route exactly as the Frontend API Guide describes."""
import unittest
from unittest import mock

import requests

from frontend.test import fakes

st = fakes.install()

from frontend import docpage_api as api  # noqa: E402

BASE = api.BASE_URL  # http://127.0.0.1:5000/api/v1


def reply(status=200, body=b'{"status": "success"}', headers=None):
    r = requests.Response()
    r.status_code = status
    r._content = body
    r.headers.update(headers or {})
    return r


class Base(unittest.TestCase):
    def setUp(self):
        fakes.install()
        st.reset()
        st.session_state["token"] = "tok"
        st.session_state["authenticated"] = True
        self.patcher = mock.patch("requests.request", return_value=reply())
        self.req = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def call(self, i=-1):
        c = self.req.call_args_list[i]
        method, url = c.args
        return method, url, c.kwargs


class Responses(Base):
    def test_success_reply_carries_http_status(self):
        self.req.return_value = reply(201, b'{"metric_id": 4}')
        out = api.get_doctor_queue()
        self.assertEqual(out["_http_status"], 201)
        self.assertEqual(out["metric_id"], 4)

    def test_list_reply_is_wrapped(self):
        self.req.return_value = reply(200, b'[{"user_id": 1}]')
        self.assertEqual(api.get_directory()["_items"], [{"user_id": 1}])

    def test_non_json_error_gets_a_code(self):
        self.req.return_value = reply(502, b"<html>bad gateway</html>")
        out = api.get_doctor_queue()
        self.assertEqual(out["_http_status"], 502)
        self.assertEqual(out["status"], "error")

    def test_backend_down_returns_none(self):
        self.req.side_effect = requests.exceptions.ConnectionError()
        self.assertIsNone(api.get_doctor_queue())

    def test_replay_header_is_reported(self):
        self.req.return_value = reply(201, b'{"consultation_uid": "C1"}', {"X-Idempotent-Replay": "true"})
        self.assertTrue(api.save_consultation(5, "x", "")["_replay"])


class ExpiredSession(Base):
    def test_401_clears_login_and_reruns(self):
        self.req.return_value = reply(401, b'{"status": "error", "code": "TOKEN_EXPIRED", "error": "x"}')
        with self.assertRaises(fakes.RerunScript):
            api.get_doctor_queue()
        self.assertNotIn("token", st.session_state)
        self.assertFalse(st.session_state["authenticated"])

    def test_wrong_current_password_does_not_log_out(self):
        self.req.return_value = reply(401, b'{"error": "Current password is incorrect"}')
        out = api.change_user_password("bad", "newpass123")
        self.assertEqual(out["_http_status"], 401)
        self.assertEqual(st.session_state["token"], "tok")


class Headers(Base):
    def test_token_sent(self):
        api.get_doctor_queue()
        self.assertEqual(self.call()[2]["headers"]["Authorization"], "Bearer tok")

    def test_get_has_no_content_type(self):
        api.get_doctor_queue()
        self.assertNotIn("Content-Type", self.call()[2]["headers"])

    def test_password_reset_sends_no_token(self):
        api.request_password_reset("ana")
        self.assertNotIn("Authorization", self.call()[2]["headers"])


class IdempotentSaves(Base):
    def key(self, i=-1):
        return self.call(i)[2]["headers"].get("Idempotency-Key")

    def test_retry_after_network_failure_reuses_key(self):
        self.req.side_effect = [requests.exceptions.Timeout(), reply(201, b'{"consultation_uid": "C1"}')]
        api.save_consultation(5, "Repeat labs", "")
        api.save_consultation(5, "Repeat labs", "")
        self.assertIsNotNone(self.key(0))
        self.assertEqual(self.key(0), self.key(1))

    def test_new_key_after_success(self):
        self.req.return_value = reply(201, b'{"consultation_uid": "C1"}')
        api.save_consultation(5, "a", "")
        api.save_consultation(5, "b", "")
        self.assertNotEqual(self.key(0), self.key(1))

    def test_every_record_creating_route_sends_a_key(self):
        self.req.return_value = reply(201, b"{}")
        api.save_consultation(5, "x", "")
        api.commit_encounter(5, {"patient_id": 5})
        api.save_biomarkers("cvd", 5, {"sbp": 140})
        api.provision_doctor({"username": "d"})
        keys = [self.key(i) for i in range(4)]
        self.assertTrue(all(keys))
        self.assertEqual(len(set(keys)), 4)


class Routes(Base):
    def check(self, method, path, params=None, body=None):
        m, url, kw = self.call()
        self.assertEqual((m, url), (method, BASE + path))
        if params is not None:
            self.assertEqual(kw.get("params"), params)
        if body is not None:
            self.assertEqual(kw.get("json"), body)

    def test_doctor_queue(self):
        api.get_doctor_queue()
        self.check("GET", "/doctor/queue")

    def test_doctor_patient(self):
        api.get_doctor_patient(5)
        self.check("GET", "/doctor/patient/5")

    def test_baseline(self):
        api.get_baseline(5)
        self.check("GET", "/doctor/patient/5/baseline")

    def test_baseline_404_comes_back_as_reply(self):
        self.req.return_value = reply(404, b'{"has_baseline": false}')
        self.assertEqual(api.get_baseline(5), {"has_baseline": False, "_http_status": 404})

    def test_infer_sends_only_patient_and_disease(self):
        api.infer_cdss(5, "cvd")
        self.check("POST", "/predictions/infer", body={"patient_id": 5, "modality": "cvd"})

    def test_save_biomarkers(self):
        api.save_biomarkers("t2d", 5, {"hba1c": 7.1})
        self.check("POST", "/biomarkers/t2d", body={"patient_id": 5, "values": {"hba1c": 7.1}})

    def test_latest_biomarkers_for_staff(self):
        api.get_latest_biomarkers("cvd", 5)
        self.check("GET", "/biomarkers/cvd/latest", params={"patient_id": 5})

    def test_latest_biomarkers_for_patient_sends_no_id(self):
        api.get_latest_biomarkers("cvd")
        self.check("GET", "/biomarkers/cvd/latest", params={})

    def test_family_history_get(self):
        api.get_patient_family_history(5)
        self.check("GET", "/patient/family-history", params={"patient_id": 5})

    def test_family_history_post(self):
        api.submit_patient_family_history({"disease_domain": "cvd", "relationship_tier": 1,
                                           "onset_classification": "early"})
        self.check("POST", "/patient/family-history",
                   body={"disease_domain": "cvd", "relationship_tier": 1, "onset_classification": "early"})

    def test_family_history_verify(self):
        api.verify_family_history(12)
        self.check("POST", "/patient/family-history/12/verify")

    def test_hazards(self):
        api.get_hazards(5)
        self.check("GET", "/patient/hazards", params={"patient_id": 5})
        api.add_hazard("cvd", "SMOKE", patient_id=5)
        self.check("POST", "/patient/hazards", body={"disease_domain": "cvd", "hazard_code": "SMOKE", "patient_id": 5})
        api.delete_hazard(3)
        self.check("DELETE", "/patient/hazards/3")

    def test_patient_adds_own_hazard_without_id(self):
        api.add_hazard("cvd", "SMOKE")
        self.check("POST", "/patient/hazards", body={"disease_domain": "cvd", "hazard_code": "SMOKE"})

    def test_biological_sex(self):
        api.set_biological_sex(5, "Female")
        self.check("POST", "/patient/biological-sex", body={"patient_id": 5, "biological_sex": "Female"})

    def test_fhrs(self):
        api.get_fhrs("t2d", 5)
        self.check("GET", "/patient/fhrs", params={"disease": "t2d", "patient_id": 5})

    def test_encounters(self):
        api.get_latest_patient_encounter(5)
        self.check("GET", "/patient/latest-encounter", params={"patient_id": 5})
        api.get_patient_encounters_list()
        self.check("GET", "/patient/encounters", params={})

    def test_queue_cancel_url_has_single_api_prefix(self):
        api.cancel_patient_checkin(5)
        self.check("DELETE", "/patient/queue/5")

    def test_checkin(self):
        api.submit_patient_checkin({"name": "A", "complaint": "c", "vitals": "v"})
        self.check("POST", "/patient/queue/checkin", body={"name": "A", "complaint": "c", "vitals": "v"})

    def test_consultation(self):
        api.save_consultation(5, "Repeat labs", "note")
        self.check("POST", "/doctor/consultation", body={"patient_id": 5, "directives": "Repeat labs", "notes": "note"})

    def test_consultation_history(self):
        api.get_consultations(5)
        self.check("GET", "/doctor/patient/5/consultations")

    def test_commit(self):
        api.commit_encounter(5, {"patient_id": 5, "encounter_type": "BASELINE"})
        self.check("POST", "/doctor/commit-encounter", body={"patient_id": 5, "encounter_type": "BASELINE"})

    def test_verify_encounter(self):
        api.verify_encounter("ENC-1")
        self.check("GET", "/doctor/encounter/ENC-1/verify")

    def test_models(self):
        api.get_models_status()
        self.check("GET", "/predictions/models/status")
        api.reload_models()
        self.check("POST", "/predictions/models/reload")

    def test_admin(self):
        api.get_directory()
        self.check("GET", "/admin/directory")
        api.provision_doctor({"username": "d"})
        self.check("POST", "/admin/provision", body={"username": "d"})
        api.verify_doctor(3)
        self.check("POST", "/admin/doctors/3/verify")
        api.unlock_user(9)
        self.check("POST", "/admin/users/9/unlock")

    def test_health_is_outside_v1(self):
        api.get_health()
        m, url, _ = self.call()
        self.assertEqual((m, url), ("GET", api.API_BASE + "/api/health/db"))

    def test_logout(self):
        api.perform_backend_logout()
        self.check("POST", "/auth/logout")


if __name__ == "__main__":
    unittest.main()
