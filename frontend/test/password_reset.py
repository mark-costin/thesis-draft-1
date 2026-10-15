"""Pure validation helpers for the forgot-password dialog (no Streamlit imports, so they are unit-testable)."""


def validate_identifier(identifier: str):
    """Return an error message, or None if the username/email field is usable."""
    if not (identifier or "").strip():
        return "Please enter your username or email."
    return None


def validate_reset_form(otp: str, new_password: str, confirm_password: str):
    """Return the first error message, or None if the reset form is valid."""
    code = (otp or "").strip()
    if not (code.isdigit() and len(code) == 6):
        return "Enter the 6-digit code."
    if len(new_password or "") < 8:
        return "Password must be at least 8 characters."
    if new_password != confirm_password:
        return "Passwords do not match."
    return None


def request_succeeded(resp) -> bool:
    """True only when the backend explicitly answered {"status": "success"}.

    _safe_request returns None when the backend is unreachable and an error dict
    for 4xx/5xx, so neither may move the user on to the next step.
    """
    return bool(resp) and resp.get("status") == "success"
