"""
Central configuration. Every module that needs a secret or setting imports it from here,
so there is exactly one place where .env is read and one place that can fail loudly.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is not set. Add a long random value to your .env file, e.g. generate one with:\n"
        '    python -c "import secrets; print(secrets.token_hex(32))"'
    )
JWT_ALGORITHM = "HS256"

# Browser origin allowed to call the API. Streamlit calls the API from its Python server,
# so CORS does not apply to it; set this when a browser-based frontend is added.
CORS_ALLOWED_ORIGIN = os.environ.get("CORS_ALLOWED_ORIGIN", "*")