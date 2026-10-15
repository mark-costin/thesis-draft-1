import sys
import types
import unittest
from unittest import mock

import requests

# docpage_api imports streamlit; streamlit is not needed for these HTTP checks,
# so give it a minimal stand-in with session_state and error().
_fake_st = types.ModuleType("streamlit")
_fake_st.session_state = {}
_fake_st.errors_shown = []
_fake_st.error = lambda msg: _fake_st.errors_shown.append(msg)
sys.modules.setdefault("streamlit", _fake_st)

from frontend import docpage_api  # noqa: E402
from frontend.test.password_reset import request_succeeded  # noqa: E402


def _response(status, body=b'{"status": "success"}'):
    r = requests.Response()
    r.status_code = status
    r._content = body
    return r


class RequestPasswordReset(unittest.TestCase):
    def setUp(self):
        _fake_st.session_state.clear()
        _fake_st.session_state["token"] = "leftover-token-from-old-session"

    def test_posts_identifier_to_forgot_password_endpoint(self):
        with mock.patch("requests.request", return_value=_response(200)) as req:
            docpage_api.request_password_reset("juan")
        method, url = req.call_args.args
        self.assertEqual(method, "POST")
        self.assertEqual(url, f"{docpage_api.BASE_URL}/auth/forgot-password")
        self.assertEqual(req.call_args.kwargs["json"], {"identifier": "juan"})

    def test_sends_no_bearer_token(self):
        # User is logged out here; a stale token must not be attached
        with mock.patch("requests.request", return_value=_response(200)) as req:
            docpage_api.request_password_reset("juan")
        self.assertNotIn("Authorization", req.call_args.kwargs["headers"])

    def test_backend_offline_is_not_success(self):
        with mock.patch("requests.request", side_effect=requests.exceptions.ConnectionError()):
            resp = docpage_api.request_password_reset("juan")
        self.assertFalse(request_succeeded(resp))

    def test_missing_endpoint_is_not_success(self):
        # Backend hasn't built /auth/forgot-password yet -> Flask HTML 404
        with mock.patch("requests.request", return_value=_response(404, b"<html>Not Found</html>")):
            resp = docpage_api.request_password_reset("juan")
        self.assertFalse(request_succeeded(resp))


class ResetPassword(unittest.TestCase):
    def setUp(self):
        _fake_st.session_state.clear()

    def test_posts_identifier_code_and_new_password(self):
        with mock.patch("requests.request", return_value=_response(200)) as req:
            docpage_api.reset_password("juan", "123456", "newpass123")
        method, url = req.call_args.args
        self.assertEqual(method, "POST")
        self.assertEqual(url, f"{docpage_api.BASE_URL}/auth/reset-password")
        self.assertEqual(
            req.call_args.kwargs["json"],
            {"identifier": "juan", "otp": "123456", "new_password": "newpass123"},
        )

    def test_wrong_code_returns_backend_error_message(self):
        body = b'{"status": "error", "error": "Invalid or expired code."}'
        with mock.patch("requests.request", return_value=_response(400, body)):
            resp = docpage_api.reset_password("juan", "000000", "newpass123")
        self.assertFalse(request_succeeded(resp))
        self.assertEqual(resp["error"], "Invalid or expired code.")


if __name__ == "__main__":
    unittest.main()
