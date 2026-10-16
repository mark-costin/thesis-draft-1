import unittest

from frontend.test import password_reset as pr


class ValidateIdentifier(unittest.TestCase):
    def test_rejects_empty_identifier(self):
        self.assertEqual(pr.validate_identifier(""), "Please enter your username or email.")

    def test_rejects_whitespace_only_identifier(self):
        self.assertEqual(pr.validate_identifier("   "), "Please enter your username or email.")

    def test_accepts_username(self):
        self.assertIsNone(pr.validate_identifier("juan.delacruz"))


class ValidateResetForm(unittest.TestCase):
    GOOD_PW = "newpass123"

    def test_rejects_code_with_letters(self):
        self.assertEqual(pr.validate_reset_form("12a456", self.GOOD_PW, self.GOOD_PW), "Enter the 6-digit code.")

    def test_rejects_short_code(self):
        self.assertEqual(pr.validate_reset_form("12345", self.GOOD_PW, self.GOOD_PW), "Enter the 6-digit code.")

    def test_rejects_empty_code(self):
        self.assertEqual(pr.validate_reset_form("", self.GOOD_PW, self.GOOD_PW), "Enter the 6-digit code.")

    def test_accepts_code_with_surrounding_spaces(self):
        # People paste codes from email with stray spaces
        self.assertIsNone(pr.validate_reset_form(" 123456 ", self.GOOD_PW, self.GOOD_PW))

    def test_rejects_password_under_8_chars(self):
        self.assertEqual(pr.validate_reset_form("123456", "short", "short"), "Password must be at least 8 characters.")

    def test_rejects_mismatched_passwords(self):
        self.assertEqual(pr.validate_reset_form("123456", self.GOOD_PW, "different1"), "Passwords do not match.")

    def test_accepts_valid_form(self):
        self.assertIsNone(pr.validate_reset_form("123456", self.GOOD_PW, self.GOOD_PW))


class RequestSucceeded(unittest.TestCase):
    def test_none_means_backend_unreachable(self):
        # _safe_request returns None on connection error / timeout
        self.assertFalse(pr.request_succeeded(None))

    def test_error_body_is_failure(self):
        # _safe_request returns {"status": "error", ...} for non-JSON 4xx/5xx (e.g. missing endpoint)
        self.assertFalse(pr.request_succeeded({"status": "error", "message": "HTTP 404"}))

    def test_empty_body_is_failure(self):
        self.assertFalse(pr.request_succeeded({}))

    def test_success_body_is_success(self):
        self.assertTrue(pr.request_succeeded({"status": "success"}))


if __name__ == "__main__":
    unittest.main()
