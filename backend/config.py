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

# Key that seals clinical encounters (HMAC-SHA256). Keep it separate from JWT_SECRET:
# rotating the login secret must never make old encounter seals unverifiable.
# Back it up — if this key is lost, existing seals can no longer be verified.
ENCOUNTER_SEAL_KEY = os.environ.get("ENCOUNTER_SEAL_KEY")
if not ENCOUNTER_SEAL_KEY:
    raise RuntimeError(
        "ENCOUNTER_SEAL_KEY is not set. Add a long random value to your .env file, e.g. generate one with:\n"
        '    python -c "import secrets; print(secrets.token_hex(32))"'
    )

# Browser origin allowed to call the API. Streamlit calls the API from its Python server,
# so CORS does not apply to it; set this when a browser-based frontend is added.
CORS_ALLOWED_ORIGIN = os.environ.get("CORS_ALLOWED_ORIGIN", "*")


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def run_options(env=None):
    """
    How `python -m backend.rest` starts the server, from FLASK_HOST, FLASK_PORT and FLASK_DEBUG.
    Defaults: this computer only (127.0.0.1), port 5000, debug off. Flask's debugger runs any
    Python typed into the error page, so debug is refused on an address other computers can reach.
    """
    env = os.environ if env is None else env
    host = (env.get("FLASK_HOST") or "127.0.0.1").strip()
    debug = (env.get("FLASK_DEBUG") or "").strip().lower() in {"1", "true", "yes", "on"}
    try:
        port = int(env.get("FLASK_PORT") or 5000)
    except ValueError:
        raise RuntimeError(f"FLASK_PORT must be a number, got {env.get('FLASK_PORT')!r}.") from None
    if debug and host not in LOOPBACK_HOSTS:
        raise RuntimeError(
            f"FLASK_DEBUG is on with FLASK_HOST={host}: the debugger would let other computers run "
            "code on this one. Use debug only with FLASK_HOST=127.0.0.1.")
    return {"host": host, "port": port, "debug": debug}


def database_url(env=None):
    """
    DATABASE_URL from .env, required. There is deliberately no fallback: a missing setting used
    to switch silently to an empty SQLite file, which looks exactly like lost patient data.
    """
    env = os.environ if env is None else env
    url = (env.get("DATABASE_URL") or "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to your .env file, e.g.\n"
            "    DATABASE_URL=postgresql://postgres:<password>@localhost:5432/postgres")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url
