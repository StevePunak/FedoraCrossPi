"""
Authentication: password hashing, persistent creds in /data/auth.json,
in-memory session store with idle timeout, rate-limited login.
"""

import json
import os
import secrets
import time
from pathlib import Path
from threading import Lock

import bcrypt

# Idle session timeout (seconds)
SESSION_IDLE_TIMEOUT = 12 * 60 * 60  # 12h

# Rate limiting: lock out an IP after N failures within a window
RATE_LIMIT_MAX_FAILURES = 5
RATE_LIMIT_WINDOW = 5 * 60      # 5 min window to count failures
RATE_LIMIT_LOCKOUT = 60         # 60s lockout after threshold


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("ascii"))
    except ValueError:
        return False

# session_token -> {"username": str, "last_activity": float}
_sessions: dict[str, dict] = {}
# ip -> [failure_timestamp, ...]
_failures: dict[str, list[float]] = {}
_lock = Lock()


def _auth_file() -> Path:
    return Path(os.environ.get("GATEWAY_DATA_DIR", "/data")) / "auth.json"


def is_dev_bypass() -> bool:
    return os.environ.get("GATEWAY_DEV_NO_AUTH") == "1"


def is_bootstrap() -> bool:
    """True when no admin password has been set yet."""
    return not _auth_file().exists()


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    # bcrypt has a hard 72-byte limit on the input
    if len(password.encode("utf-8")) > 72:
        raise ValueError("password must be 72 bytes or fewer")


def bootstrap_password(username: str, password: str) -> None:
    """Set the initial admin password. Only valid when in bootstrap mode."""
    if not is_bootstrap():
        raise ValueError("password already set")
    if not username or not password:
        raise ValueError("username and password required")
    _validate_password(password)

    data = {
        "username": username,
        "password_hash": _hash_password(password),
    }
    path = _auth_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    os.chmod(path, 0o600)


def change_password(current_password: str, new_password: str) -> None:
    data = _load_creds()
    if not _verify_password(current_password, data["password_hash"]):
        raise ValueError("current password is incorrect")
    _validate_password(new_password)
    data["password_hash"] = _hash_password(new_password)
    _auth_file().write_text(json.dumps(data, indent=2) + "\n")


def _load_creds() -> dict:
    path = _auth_file()
    if not path.exists():
        raise ValueError("no credentials configured")
    return json.loads(path.read_text())


def _check_rate_limit(ip: str) -> float | None:
    """Return seconds until unlock, or None if not locked out."""
    now = time.time()
    with _lock:
        fails = _failures.get(ip, [])
        fails = [t for t in fails if now - t < RATE_LIMIT_WINDOW]
        _failures[ip] = fails

        if len(fails) >= RATE_LIMIT_MAX_FAILURES:
            last = fails[-1]
            remaining = RATE_LIMIT_LOCKOUT - (now - last)
            if remaining > 0:
                return remaining
    return None


def _record_failure(ip: str) -> None:
    now = time.time()
    with _lock:
        _failures.setdefault(ip, []).append(now)


def _clear_failures(ip: str) -> None:
    with _lock:
        _failures.pop(ip, None)


def login(username: str, password: str, client_ip: str) -> str:
    """Validate credentials and return a new session token."""
    locked_for = _check_rate_limit(client_ip)
    if locked_for is not None:
        raise ValueError(f"too many failed attempts; try again in {int(locked_for)}s")

    try:
        data = _load_creds()
    except ValueError:
        raise ValueError("authentication not configured")

    if username != data["username"] or not _verify_password(password, data["password_hash"]):
        _record_failure(client_ip)
        raise ValueError("invalid credentials")

    _clear_failures(client_ip)
    token = secrets.token_urlsafe(32)
    with _lock:
        _sessions[token] = {"username": username, "last_activity": time.time()}
    return token


def logout(token: str) -> None:
    with _lock:
        _sessions.pop(token, None)


def validate_session(token: str | None) -> str | None:
    """Return username if token is valid (and bump last_activity), else None."""
    if not token:
        return None
    now = time.time()
    with _lock:
        session = _sessions.get(token)
        if not session:
            return None
        if now - session["last_activity"] > SESSION_IDLE_TIMEOUT:
            _sessions.pop(token, None)
            return None
        session["last_activity"] = now
        return session["username"]


def get_username() -> str | None:
    """Configured username, or None if in bootstrap mode."""
    if is_bootstrap():
        return None
    return _load_creds().get("username")
